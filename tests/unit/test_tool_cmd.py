"""Unit tests for agentrun_cli.commands.tool_cmd — helpers and CLI commands."""

import json
import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import click
import pytest
from click.testing import CliRunner

from agentrun_cli.commands.tool_cmd import (
    _ctx_cfg,
    _load_json_option,
    _serialize_tool,
    _serialize_tool_detail,
    _serialize_tool_info,
    tool_group,
)


# ---------------------------------------------------------------------------
# Helper: _ctx_cfg
# ---------------------------------------------------------------------------

class TestCtxCfg:

    def test_returns_profile_and_region(self):
        ctx = SimpleNamespace(obj={"profile": "prod", "region": "cn-shanghai"})
        assert _ctx_cfg(ctx) == ("prod", "cn-shanghai")

    def test_none_obj(self):
        ctx = SimpleNamespace(obj=None)
        assert _ctx_cfg(ctx) == (None, None)

    def test_empty_obj(self):
        ctx = SimpleNamespace(obj={})
        assert _ctx_cfg(ctx) == (None, None)


# ---------------------------------------------------------------------------
# Helper: _serialize_tool
# ---------------------------------------------------------------------------

class TestSerializeTool:

    def test_all_fields(self):
        t = SimpleNamespace(
            tool_id="t-1",
            tool_name="mcp-weather",
            tool_type="MCP",
            create_method="MCP_REMOTE",
            status="ACTIVE",
            description="Weather tool",
            created_at="2025-01-01",
            updated_at="2025-01-02",
        )
        result = _serialize_tool(t)
        assert result == {
            "tool_id": "t-1",
            "tool_name": "mcp-weather",
            "tool_type": "MCP",
            "create_method": "MCP_REMOTE",
            "status": "ACTIVE",
            "description": "Weather tool",
            "created_at": "2025-01-01",
            "updated_at": "2025-01-02",
        }

    def test_none_fields_excluded(self):
        t = SimpleNamespace(
            tool_id=None, tool_name="t", tool_type=None,
            create_method=None, status=None, description=None,
            created_at=None, updated_at=None,
        )
        result = _serialize_tool(t)
        assert result == {"tool_name": "t"}

    def test_fallback_name(self):
        t = SimpleNamespace(name="fallback")
        result = _serialize_tool(t)
        assert result["tool_name"] == "fallback"


# ---------------------------------------------------------------------------
# Helper: _serialize_tool_detail
# ---------------------------------------------------------------------------

class TestSerializeToolDetail:

    def test_includes_extras(self):
        t = SimpleNamespace(
            tool_id="t-1", tool_name="mcp-x", tool_type="MCP",
            create_method=None, status="ACTIVE",
            description=None, created_at=None, updated_at=None,
            protocol_spec='{"mcpServers":{}}',
            memory=512, timeout=30,
            credential_name="cred-1",
            environment_variables={"KEY": "VAL"},
            data_endpoint="https://example.com",
            mcp_config=None,
        )
        result = _serialize_tool_detail(t)
        assert result["protocol_spec"] == '{"mcpServers":{}}'
        assert result["memory"] == 512
        assert result["timeout"] == 30
        assert result["credential_name"] == "cred-1"
        assert result["environment_variables"] == {"KEY": "VAL"}
        assert result["data_endpoint"] == "https://example.com"

    def test_mcp_config_dict(self):
        t = SimpleNamespace(
            tool_id=None, tool_name="t", tool_type=None,
            create_method=None, status=None, description=None,
            created_at=None, updated_at=None,
            mcp_config={"proxy": True},
        )
        result = _serialize_tool_detail(t)
        assert result["mcp_config"] == {"proxy": True}

    def test_mcp_config_to_map(self):
        mc = MagicMock()
        mc.to_map.return_value = {"mapped": True}
        del mc.model_dump
        t = SimpleNamespace(
            tool_id=None, tool_name="t", tool_type=None,
            create_method=None, status=None, description=None,
            created_at=None, updated_at=None,
            mcp_config=mc,
        )
        result = _serialize_tool_detail(t)
        assert result["mcp_config"] == {"mapped": True}

    def test_mcp_config_model_dump(self):
        mc = MagicMock()
        mc.model_dump.return_value = {"dumped": True}
        del mc.to_map
        t = SimpleNamespace(
            tool_id=None, tool_name="t", tool_type=None,
            create_method=None, status=None, description=None,
            created_at=None, updated_at=None,
            mcp_config=mc,
        )
        result = _serialize_tool_detail(t)
        assert result["mcp_config"] == {"dumped": True}

    def test_mcp_config_str_fallback(self):
        t = SimpleNamespace(
            tool_id=None, tool_name="t", tool_type=None,
            create_method=None, status=None, description=None,
            created_at=None, updated_at=None,
            mcp_config="raw-string",
        )
        result = _serialize_tool_detail(t)
        assert result["mcp_config"] == "raw-string"

    def test_no_extras(self):
        """When no extra fields exist, result should equal base _serialize_tool."""
        t = SimpleNamespace(
            tool_id="t-1", tool_name="t", tool_type="MCP",
            create_method=None, status=None, description=None,
            created_at=None, updated_at=None,
        )
        result = _serialize_tool_detail(t)
        assert result == {"tool_id": "t-1", "tool_name": "t", "tool_type": "MCP"}


# ---------------------------------------------------------------------------
# Helper: _load_json_option
# ---------------------------------------------------------------------------

class TestLoadJsonOption:

    def test_none(self):
        assert _load_json_option(None) is None

    def test_inline_json(self):
        assert _load_json_option('{"a": 1}') == {"a": 1}

    def test_file_path(self, tmp_path):
        f = tmp_path / "tool.json"
        f.write_text('{"from": "file"}')
        assert _load_json_option(str(f)) == {"from": "file"}

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _load_json_option("{bad}")


# ---------------------------------------------------------------------------
# Helper: _serialize_tool_info
# ---------------------------------------------------------------------------

class TestSerializeToolInfo:

    def test_basic(self):
        ti = SimpleNamespace(name="get_weather", description="Get weather", parameters=None)
        result = _serialize_tool_info(ti)
        assert result == {"name": "get_weather", "description": "Get weather"}

    def test_with_json_schema_parameters(self):
        params = MagicMock()
        params.to_json_schema.return_value = {"type": "object", "properties": {}}
        ti = SimpleNamespace(name="fn", description="desc", parameters=params)
        result = _serialize_tool_info(ti)
        assert result["parameters"] == {"type": "object", "properties": {}}

    def test_with_non_schema_parameters(self):
        params = "some-string-params"
        ti = SimpleNamespace(name="fn", description="desc", parameters=params)
        result = _serialize_tool_info(ti)
        assert result["parameters"] == "some-string-params"


# ---------------------------------------------------------------------------
# CLI: tool create
# ---------------------------------------------------------------------------

class TestToolCreateCommand:

    @patch("agentrun_cli.commands.tool_cmd.get_agentrun_client")
    def test_create_mcp_remote(self, mock_client_fn):
        client = MagicMock()
        mock_client_fn.return_value = (client, {}, MagicMock())

        data = SimpleNamespace(
            tool_id="t-1", tool_name="mcp-w", tool_type="MCP",
            create_method="MCP_REMOTE", status="CREATED",
            description=None, created_at=None, updated_at=None,
        )
        client.create_tool_with_options.return_value = SimpleNamespace(
            body=SimpleNamespace(data=data)
        )

        runner = CliRunner()
        result = runner.invoke(tool_group, [
            "create", "--name", "mcp-w", "--tool-type", "MCP",
            "--create-method", "MCP_REMOTE",
            "--protocol-spec", '{"mcpServers":{"w":{"url":"https://example.com/sse"}}}',
        ])
        assert result.exit_code == 0
        assert "mcp-w" in result.output

    @patch("agentrun_cli.commands.tool_cmd.get_agentrun_client")
    def test_create_with_image_and_env(self, mock_client_fn):
        client = MagicMock()
        mock_client_fn.return_value = (client, {}, MagicMock())

        data = SimpleNamespace(
            tool_id="t-2", tool_name="code-tool", tool_type="FUNCTIONCALL",
            create_method="CODE_PACKAGE", status="CREATED",
            description=None, created_at=None, updated_at=None,
        )
        client.create_tool_with_options.return_value = SimpleNamespace(
            body=SimpleNamespace(data=data)
        )

        runner = CliRunner()
        result = runner.invoke(tool_group, [
            "create", "--name", "code-tool", "--tool-type", "FUNCTIONCALL",
            "--create-method", "CODE_PACKAGE",
            "--image", "myimage:latest", "--port", "8080", "--command", "python main.py",
            "--timeout", "60", "--memory", "512", "--cpu", "1.0",
            "--credential", "cred-1",
            "--env", "KEY1=val1", "--env", "KEY2=val2",
            "--description", "A code tool",
        ])
        assert result.exit_code == 0

    @patch("agentrun_cli.commands.tool_cmd.get_agentrun_client")
    def test_create_with_mcp_config(self, mock_client_fn):
        client = MagicMock()
        mock_client_fn.return_value = (client, {}, MagicMock())

        data = SimpleNamespace(
            tool_id="t-3", tool_name="mcp-proxy", tool_type="MCP",
            create_method="MCP_REMOTE", status="CREATED",
            description=None, created_at=None, updated_at=None,
        )
        client.create_tool_with_options.return_value = SimpleNamespace(
            body=SimpleNamespace(data=data)
        )

        runner = CliRunner()
        result = runner.invoke(tool_group, [
            "create", "--name", "mcp-proxy", "--tool-type", "MCP",
            "--create-method", "MCP_REMOTE",
            "--proxy-enabled",
            "--session-affinity", "MCP_SSE",
        ])
        assert result.exit_code == 0

    @patch("agentrun_cli.commands.tool_cmd.get_agentrun_client")
    def test_create_from_file(self, mock_client_fn):
        client = MagicMock()
        mock_client_fn.return_value = (client, {}, MagicMock())

        data = SimpleNamespace(
            tool_id="t-4", tool_name="from-file", tool_type="MCP",
            create_method="MCP_REMOTE", status="CREATED",
            description=None, created_at=None, updated_at=None,
        )
        client.create_tool_with_options.return_value = SimpleNamespace(
            body=SimpleNamespace(data=data)
        )

        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("tool.json", "w") as f:
                json.dump({"tool_name": "from-file", "tool_type": "MCP", "create_method": "MCP_REMOTE"}, f)
            result = runner.invoke(tool_group, [
                "create", "--name", "from-file", "--tool-type", "MCP",
                "--create-method", "MCP_REMOTE", "--from-file", "tool.json",
            ])
        assert result.exit_code == 0

    @patch("agentrun_cli.commands.tool_cmd.get_agentrun_client")
    def test_create_null_data_response(self, mock_client_fn):
        client = MagicMock()
        mock_client_fn.return_value = (client, {}, MagicMock())
        client.create_tool_with_options.return_value = SimpleNamespace(
            body=SimpleNamespace(data=None)
        )

        runner = CliRunner()
        result = runner.invoke(tool_group, [
            "create", "--name", "t", "--tool-type", "MCP", "--create-method", "MCP_REMOTE",
        ])
        assert result.exit_code == 0
        assert "t" in result.output

    @patch("agentrun_cli.commands.tool_cmd.get_agentrun_client")
    def test_create_protocol_spec_from_file(self, mock_client_fn):
        client = MagicMock()
        mock_client_fn.return_value = (client, {}, MagicMock())

        data = SimpleNamespace(
            tool_id="t-5", tool_name="spec-file", tool_type="MCP",
            create_method="MCP_REMOTE", status="CREATED",
            description=None, created_at=None, updated_at=None,
        )
        client.create_tool_with_options.return_value = SimpleNamespace(
            body=SimpleNamespace(data=data)
        )

        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("spec.json", "w") as f:
                json.dump({"mcpServers": {}}, f)
            result = runner.invoke(tool_group, [
                "create", "--name", "spec-file", "--tool-type", "MCP",
                "--create-method", "MCP_REMOTE",
                "--protocol-spec", "spec.json",
            ])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# CLI: tool get
# ---------------------------------------------------------------------------

class TestToolGetCommand:

    @patch("agentrun_cli.commands.tool_cmd.build_sdk_config")
    def test_get(self, mock_cfg):
        mock_cfg.return_value = MagicMock()
        tool_obj = SimpleNamespace(
            tool_id="t-1", tool_name="mcp-w", tool_type="MCP",
            create_method="MCP_REMOTE", status="ACTIVE",
            description="Weather", created_at=None, updated_at=None,
        )
        with patch("agentrun.tool.Tool.get_by_name", return_value=tool_obj):
            runner = CliRunner()
            result = runner.invoke(tool_group, ["get", "--name", "mcp-w"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# CLI: tool list
# ---------------------------------------------------------------------------

class TestToolListCommand:

    @patch("agentrun_cli.commands.tool_cmd.get_agentrun_client")
    def test_list_empty(self, mock_client_fn):
        client = MagicMock()
        mock_client_fn.return_value = (client, {}, MagicMock())
        items_container = SimpleNamespace(items=[])
        body = SimpleNamespace(data=items_container)
        client.list_tools_with_options.return_value = SimpleNamespace(body=body)

        runner = CliRunner()
        result = runner.invoke(tool_group, ["list"])
        assert result.exit_code == 0

    @patch("agentrun_cli.commands.tool_cmd.get_agentrun_client")
    def test_list_with_type_filter(self, mock_client_fn):
        client = MagicMock()
        mock_client_fn.return_value = (client, {}, MagicMock())
        t1 = SimpleNamespace(
            tool_id="t1", tool_name="mcp-a", tool_type="MCP",
            create_method="MCP_REMOTE", status="ACTIVE",
            description=None, created_at=None, updated_at=None,
        )
        items_container = SimpleNamespace(items=[t1])
        body = SimpleNamespace(data=items_container)
        client.list_tools_with_options.return_value = SimpleNamespace(body=body)

        runner = CliRunner()
        result = runner.invoke(tool_group, ["list", "--tool-type", "MCP"])
        assert result.exit_code == 0
        assert "mcp-a" in result.output

    @patch("agentrun_cli.commands.tool_cmd.get_agentrun_client")
    def test_list_with_pagination(self, mock_client_fn):
        client = MagicMock()
        mock_client_fn.return_value = (client, {}, MagicMock())
        items_container = SimpleNamespace(items=[])
        body = SimpleNamespace(data=items_container)
        client.list_tools_with_options.return_value = SimpleNamespace(body=body)

        runner = CliRunner()
        result = runner.invoke(tool_group, ["list", "--page-number", "1", "--page-size", "10"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# CLI: tool update
# ---------------------------------------------------------------------------

class TestToolUpdateCommand:

    @patch("agentrun_cli.commands.tool_cmd.get_agentrun_client")
    def test_update_description(self, mock_client_fn):
        client = MagicMock()
        mock_client_fn.return_value = (client, {}, MagicMock())
        data = SimpleNamespace(
            tool_id="t-1", tool_name="mcp-w", tool_type="MCP",
            create_method="MCP_REMOTE", status="ACTIVE",
            description="Updated", created_at=None, updated_at=None,
        )
        client.update_tool_with_options.return_value = SimpleNamespace(
            body=SimpleNamespace(data=data)
        )

        runner = CliRunner()
        result = runner.invoke(tool_group, ["update", "--name", "mcp-w", "--description", "Updated"])
        assert result.exit_code == 0
        client.update_tool_with_options.assert_called_once()

    @patch("agentrun_cli.commands.tool_cmd.get_agentrun_client")
    def test_update_with_protocol_spec(self, mock_client_fn):
        client = MagicMock()
        mock_client_fn.return_value = (client, {}, MagicMock())
        data = SimpleNamespace(
            tool_id="t-1", tool_name="mcp-w", tool_type="MCP",
            create_method=None, status="ACTIVE",
            description=None, created_at=None, updated_at=None,
        )
        client.update_tool_with_options.return_value = SimpleNamespace(
            body=SimpleNamespace(data=data)
        )

        runner = CliRunner()
        result = runner.invoke(tool_group, [
            "update", "--name", "mcp-w",
            "--protocol-spec", '{"mcpServers":{}}',
        ])
        assert result.exit_code == 0

    @patch("agentrun_cli.commands.tool_cmd.get_agentrun_client")
    def test_update_with_mcp_config(self, mock_client_fn):
        client = MagicMock()
        mock_client_fn.return_value = (client, {}, MagicMock())
        data = SimpleNamespace(
            tool_id="t-1", tool_name="mcp-w", tool_type="MCP",
            create_method=None, status="ACTIVE",
            description=None, created_at=None, updated_at=None,
        )
        client.update_tool_with_options.return_value = SimpleNamespace(
            body=SimpleNamespace(data=data)
        )

        runner = CliRunner()
        result = runner.invoke(tool_group, [
            "update", "--name", "mcp-w",
            "--proxy-enabled", "--session-affinity", "MCP_SSE",
        ])
        assert result.exit_code == 0

    @patch("agentrun_cli.commands.tool_cmd.get_agentrun_client")
    def test_update_with_resource_opts(self, mock_client_fn):
        client = MagicMock()
        mock_client_fn.return_value = (client, {}, MagicMock())
        data = SimpleNamespace(
            tool_id="t-1", tool_name="t", tool_type="MCP",
            create_method=None, status="ACTIVE",
            description=None, created_at=None, updated_at=None,
        )
        client.update_tool_with_options.return_value = SimpleNamespace(
            body=SimpleNamespace(data=data)
        )

        runner = CliRunner()
        result = runner.invoke(tool_group, [
            "update", "--name", "t",
            "--timeout", "120", "--memory", "1024", "--cpu", "2.0",
            "--credential", "cred-2",
        ])
        assert result.exit_code == 0

    @patch("agentrun_cli.commands.tool_cmd.get_agentrun_client")
    def test_update_from_file(self, mock_client_fn):
        client = MagicMock()
        mock_client_fn.return_value = (client, {}, MagicMock())
        data = SimpleNamespace(
            tool_id="t-1", tool_name="t", tool_type="MCP",
            create_method=None, status="ACTIVE",
            description=None, created_at=None, updated_at=None,
        )
        client.update_tool_with_options.return_value = SimpleNamespace(
            body=SimpleNamespace(data=data)
        )

        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("upd.json", "w") as f:
                json.dump({"description": "from file"}, f)
            result = runner.invoke(tool_group, [
                "update", "--name", "t", "--from-file", "upd.json",
            ])
        assert result.exit_code == 0

    @patch("agentrun_cli.commands.tool_cmd.get_agentrun_client")
    def test_update_null_data_response(self, mock_client_fn):
        client = MagicMock()
        mock_client_fn.return_value = (client, {}, MagicMock())
        client.update_tool_with_options.return_value = SimpleNamespace(
            body=SimpleNamespace(data=None)
        )

        runner = CliRunner()
        result = runner.invoke(tool_group, ["update", "--name", "t", "--description", "x"])
        assert result.exit_code == 0
        assert "t" in result.output


# ---------------------------------------------------------------------------
# CLI: tool delete
# ---------------------------------------------------------------------------

class TestToolDeleteCommand:

    @patch("agentrun_cli.commands.tool_cmd.get_agentrun_client")
    def test_delete(self, mock_client_fn):
        client = MagicMock()
        mock_client_fn.return_value = (client, {}, MagicMock())

        runner = CliRunner()
        result = runner.invoke(tool_group, ["delete", "--name", "mcp-test"])
        assert result.exit_code == 0
        client.delete_tool_with_options.assert_called_once()
        assert "mcp-test" in result.output


# ---------------------------------------------------------------------------
# CLI: tool list-tools
# ---------------------------------------------------------------------------

class TestToolListToolsCommand:

    @patch("agentrun_cli.commands.tool_cmd.build_sdk_config")
    def test_list_tools(self, mock_cfg):
        mock_cfg.return_value = MagicMock()
        tool_obj = MagicMock()
        tool_obj.tool_type = "MCP"
        ti1 = SimpleNamespace(name="get_weather", description="Get weather", parameters=None)
        ti2 = SimpleNamespace(name="set_alarm", description="Set alarm", parameters=None)
        tool_obj.list_tools.return_value = [ti1, ti2]

        with patch("agentrun.tool.Tool.get_by_name", return_value=tool_obj):
            runner = CliRunner()
            result = runner.invoke(tool_group, ["list-tools", "--name", "mcp-w"])
        assert result.exit_code == 0
        assert "get_weather" in result.output
        assert "set_alarm" in result.output


# ---------------------------------------------------------------------------
# CLI: tool invoke
# ---------------------------------------------------------------------------

class TestToolInvokeCommand:

    def test_mutually_exclusive_arguments(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("args.json", "w") as f:
                json.dump({"city": "杭州"}, f)
            result = runner.invoke(tool_group, [
                "invoke", "--name", "t", "--sub-tool", "fn",
                "--arguments", '{"a":1}', "--arguments-file", "args.json",
            ])
        assert result.exit_code != 0

    @patch("agentrun_cli.commands.tool_cmd.build_sdk_config")
    def test_invoke_with_arguments(self, mock_cfg):
        mock_cfg.return_value = MagicMock()
        tool_obj = MagicMock()
        tool_obj.call_tool.return_value = {"temperature": "25°C"}

        with patch("agentrun.tool.Tool.get_by_name", return_value=tool_obj):
            runner = CliRunner()
            result = runner.invoke(tool_group, [
                "invoke", "--name", "mcp-w", "--sub-tool", "get_weather",
                "--arguments", '{"city": "杭州"}',
            ])
        assert result.exit_code == 0
        assert "25" in result.output
        tool_obj.call_tool.assert_called_once_with(
            "get_weather", arguments={"city": "杭州"}, config=mock_cfg.return_value,
        )

    @patch("agentrun_cli.commands.tool_cmd.build_sdk_config")
    def test_invoke_with_arguments_file(self, mock_cfg):
        mock_cfg.return_value = MagicMock()
        tool_obj = MagicMock()
        tool_obj.call_tool.return_value = {"result": "ok"}

        with patch("agentrun.tool.Tool.get_by_name", return_value=tool_obj):
            runner = CliRunner()
            with runner.isolated_filesystem():
                with open("args.json", "w") as f:
                    json.dump({"city": "北京"}, f)
                result = runner.invoke(tool_group, [
                    "invoke", "--name", "mcp-w", "--sub-tool", "get_weather",
                    "--arguments-file", "args.json",
                ])
        assert result.exit_code == 0
        tool_obj.call_tool.assert_called_once()

    @patch("agentrun_cli.commands.tool_cmd.build_sdk_config")
    def test_invoke_no_arguments(self, mock_cfg):
        mock_cfg.return_value = MagicMock()
        tool_obj = MagicMock()
        tool_obj.call_tool.return_value = {"status": "ok"}

        with patch("agentrun.tool.Tool.get_by_name", return_value=tool_obj):
            runner = CliRunner()
            result = runner.invoke(tool_group, [
                "invoke", "--name", "mcp-w", "--sub-tool", "ping",
            ])
        assert result.exit_code == 0
        tool_obj.call_tool.assert_called_once_with(
            "ping", arguments=None, config=mock_cfg.return_value,
        )