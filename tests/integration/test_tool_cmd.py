"""Integration tests for tool CLI commands (via top-level ``ar tool``)."""

import json
import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from agentrun_cli.main import cli


# ---------------------------------------------------------------------------
# SDK mock helpers
# ---------------------------------------------------------------------------

def _mock_agentrun_models():
    mod = MagicMock()
    mod.CreateToolInputV2 = MagicMock(side_effect=lambda **kw: SimpleNamespace(**kw))
    mod.CreateToolRequest = MagicMock(side_effect=lambda **kw: SimpleNamespace(**kw))
    mod.UpdateToolInputV2 = MagicMock(side_effect=lambda **kw: SimpleNamespace(**kw))
    mod.UpdateToolRequest = MagicMock(side_effect=lambda **kw: SimpleNamespace(**kw))
    mod.ListToolsRequest = MagicMock(side_effect=lambda **kw: SimpleNamespace(**kw))
    mod.ContainerConfiguration = MagicMock(side_effect=lambda **kw: SimpleNamespace(**kw))
    mod.McpConfig = MagicMock(side_effect=lambda **kw: SimpleNamespace(**kw))
    return mod


def _make_tool_obj(**overrides):
    defaults = {
        "tool_id": "t-xxx",
        "tool_name": "test-tool",
        "tool_type": "MCP",
        "create_method": "MCP_REMOTE",
        "status": "ACTIVE",
        "description": "Test tool",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-02T00:00:00Z",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _patch_inner_client(client):
    return patch(
        "agentrun_cli.commands.tool_cmd.get_agentrun_client",
        return_value=(client, {}, MagicMock()),
    )


def _patch_sdk_config():
    return patch(
        "agentrun_cli.commands.tool_cmd.build_sdk_config",
        return_value=MagicMock(),
    )


# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------

class TestToolHelp:

    def test_tool_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["tool", "--help"])
        assert result.exit_code == 0
        assert "create" in result.output
        assert "list" in result.output
        assert "get" in result.output
        assert "update" in result.output
        assert "delete" in result.output
        assert "list-tools" in result.output
        assert "invoke" in result.output


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

class TestToolCreate:

    def test_create_mcp_remote(self):
        mock_mod = _mock_agentrun_models()
        client = MagicMock()
        data = _make_tool_obj(tool_name="mcp-weather", status="CREATED")
        client.create_tool_with_options.return_value = SimpleNamespace(
            body=SimpleNamespace(data=data)
        )

        with _patch_inner_client(client), \
             patch.dict("sys.modules", {"alibabacloud_agentrun20250910": MagicMock(),
                                        "alibabacloud_agentrun20250910.models": mock_mod}):
            runner = CliRunner()
            result = runner.invoke(cli, [
                "tool", "create",
                "--name", "mcp-weather",
                "--tool-type", "MCP",
                "--create-method", "MCP_REMOTE",
                "--protocol-spec", '{"mcpServers":{"w":{"url":"https://example.com/sse"}}}',
            ])
        assert result.exit_code == 0, result.output
        out = json.loads(result.output)
        assert out["tool_name"] == "mcp-weather"

    def test_create_with_container(self):
        mock_mod = _mock_agentrun_models()
        client = MagicMock()
        data = _make_tool_obj(tool_name="code-tool", tool_type="FUNCTIONCALL",
                              create_method="CODE_PACKAGE", status="CREATED")
        client.create_tool_with_options.return_value = SimpleNamespace(
            body=SimpleNamespace(data=data)
        )

        with _patch_inner_client(client), \
             patch.dict("sys.modules", {"alibabacloud_agentrun20250910": MagicMock(),
                                        "alibabacloud_agentrun20250910.models": mock_mod}):
            runner = CliRunner()
            result = runner.invoke(cli, [
                "tool", "create",
                "--name", "code-tool",
                "--tool-type", "FUNCTIONCALL",
                "--create-method", "CODE_PACKAGE",
                "--image", "myimage:latest",
                "--port", "8080",
                "--command", "python main.py",
                "--memory", "512",
                "--cpu", "1.0",
                "--env", "KEY=val",
            ])
        assert result.exit_code == 0, result.output

    def test_create_from_file(self):
        mock_mod = _mock_agentrun_models()
        client = MagicMock()
        data = _make_tool_obj(tool_name="from-file", status="CREATED")
        client.create_tool_with_options.return_value = SimpleNamespace(
            body=SimpleNamespace(data=data)
        )

        with _patch_inner_client(client), \
             patch.dict("sys.modules", {"alibabacloud_agentrun20250910": MagicMock(),
                                        "alibabacloud_agentrun20250910.models": mock_mod}):
            runner = CliRunner()
            with runner.isolated_filesystem():
                with open("tool.json", "w") as f:
                    json.dump({"tool_name": "from-file", "tool_type": "MCP"}, f)
                result = runner.invoke(cli, [
                    "tool", "create",
                    "--name", "from-file",
                    "--tool-type", "MCP",
                    "--create-method", "MCP_REMOTE",
                    "--from-file", "tool.json",
                ])
        assert result.exit_code == 0, result.output


class TestToolGet:

    def test_get_tool(self):
        tool_obj = _make_tool_obj(tool_name="mcp-weather")
        with _patch_sdk_config(), \
             patch("agentrun.tool.Tool.get_by_name", return_value=tool_obj):
            runner = CliRunner()
            result = runner.invoke(cli, ["tool", "get", "--name", "mcp-weather"])
        assert result.exit_code == 0, result.output
        out = json.loads(result.output)
        assert out["tool_name"] == "mcp-weather"


class TestToolList:

    def test_list_all(self):
        mock_mod = _mock_agentrun_models()
        client = MagicMock()
        t1 = _make_tool_obj(tool_name="t1")
        t2 = _make_tool_obj(tool_name="t2", tool_type="FUNCTIONCALL")
        items_container = SimpleNamespace(items=[t1, t2])
        body = SimpleNamespace(data=items_container)
        client.list_tools_with_options.return_value = SimpleNamespace(body=body)

        with _patch_inner_client(client), \
             patch.dict("sys.modules", {"alibabacloud_agentrun20250910": MagicMock(),
                                        "alibabacloud_agentrun20250910.models": mock_mod}):
            runner = CliRunner()
            result = runner.invoke(cli, ["tool", "list"])
        assert result.exit_code == 0, result.output
        out = json.loads(result.output)
        assert len(out) == 2

    def test_list_filtered(self):
        mock_mod = _mock_agentrun_models()
        client = MagicMock()
        items_container = SimpleNamespace(items=[_make_tool_obj(tool_type="MCP")])
        body = SimpleNamespace(data=items_container)
        client.list_tools_with_options.return_value = SimpleNamespace(body=body)

        with _patch_inner_client(client), \
             patch.dict("sys.modules", {"alibabacloud_agentrun20250910": MagicMock(),
                                        "alibabacloud_agentrun20250910.models": mock_mod}):
            runner = CliRunner()
            result = runner.invoke(cli, ["tool", "list", "--tool-type", "MCP"])
        assert result.exit_code == 0, result.output


class TestToolUpdate:

    def test_update_description(self):
        mock_mod = _mock_agentrun_models()
        client = MagicMock()
        data = _make_tool_obj(tool_name="mcp-w", description="Updated")
        client.update_tool_with_options.return_value = SimpleNamespace(
            body=SimpleNamespace(data=data)
        )

        with _patch_inner_client(client), \
             patch.dict("sys.modules", {"alibabacloud_agentrun20250910": MagicMock(),
                                        "alibabacloud_agentrun20250910.models": mock_mod}):
            runner = CliRunner()
            result = runner.invoke(cli, [
                "tool", "update", "--name", "mcp-w", "--description", "Updated",
            ])
        assert result.exit_code == 0, result.output
        client.update_tool_with_options.assert_called_once()

    def test_update_from_file(self):
        mock_mod = _mock_agentrun_models()
        client = MagicMock()
        data = _make_tool_obj(tool_name="mcp-w")
        client.update_tool_with_options.return_value = SimpleNamespace(
            body=SimpleNamespace(data=data)
        )

        with _patch_inner_client(client), \
             patch.dict("sys.modules", {"alibabacloud_agentrun20250910": MagicMock(),
                                        "alibabacloud_agentrun20250910.models": mock_mod}):
            runner = CliRunner()
            with runner.isolated_filesystem():
                with open("upd.json", "w") as f:
                    json.dump({"description": "from file"}, f)
                result = runner.invoke(cli, [
                    "tool", "update", "--name", "mcp-w", "--from-file", "upd.json",
                ])
        assert result.exit_code == 0, result.output

    def test_update_with_mcp_config_and_resources(self):
        mock_mod = _mock_agentrun_models()
        client = MagicMock()
        data = _make_tool_obj(tool_name="mcp-w")
        client.update_tool_with_options.return_value = SimpleNamespace(
            body=SimpleNamespace(data=data)
        )

        with _patch_inner_client(client), \
             patch.dict("sys.modules", {"alibabacloud_agentrun20250910": MagicMock(),
                                        "alibabacloud_agentrun20250910.models": mock_mod}):
            runner = CliRunner()
            result = runner.invoke(cli, [
                "tool", "update", "--name", "mcp-w",
                "--proxy-enabled", "--session-affinity", "MCP_SSE",
                "--timeout", "120", "--memory", "1024", "--cpu", "2.0",
                "--credential", "cred-2",
                "--protocol-spec", '{"mcpServers":{}}',
            ])
        assert result.exit_code == 0, result.output


class TestToolDelete:

    def test_delete_tool(self):
        client = MagicMock()
        with _patch_inner_client(client):
            runner = CliRunner()
            result = runner.invoke(cli, ["tool", "delete", "--name", "old-tool"])
        assert result.exit_code == 0, result.output
        out = json.loads(result.output)
        assert out["deleted"] == "old-tool"


# ---------------------------------------------------------------------------
# Data-plane
# ---------------------------------------------------------------------------

class TestToolListTools:

    def test_list_sub_tools(self):
        tool_obj = MagicMock()
        tool_obj.tool_type = "MCP"
        ti1 = SimpleNamespace(name="get_weather", description="Get weather", parameters=None)
        ti2 = SimpleNamespace(name="set_alarm", description="Set alarm", parameters=None)
        tool_obj.list_tools.return_value = [ti1, ti2]

        with _patch_sdk_config(), \
             patch("agentrun.tool.Tool.get_by_name", return_value=tool_obj):
            runner = CliRunner()
            result = runner.invoke(cli, ["tool", "list-tools", "--name", "mcp-w"])
        assert result.exit_code == 0, result.output
        out = json.loads(result.output)
        assert len(out["sub_tools"]) == 2
        assert out["sub_tools"][0]["name"] == "get_weather"


class TestToolInvoke:

    def test_invoke_with_inline_args(self):
        tool_obj = MagicMock()
        tool_obj.call_tool.return_value = {"temperature": "25°C"}

        with _patch_sdk_config(), \
             patch("agentrun.tool.Tool.get_by_name", return_value=tool_obj):
            runner = CliRunner()
            result = runner.invoke(cli, [
                "tool", "invoke",
                "--name", "mcp-w",
                "--sub-tool", "get_weather",
                "--arguments", '{"city": "杭州"}',
            ])
        assert result.exit_code == 0, result.output
        out = json.loads(result.output)
        assert out["result"]["temperature"] == "25°C"

    def test_invoke_with_args_file(self):
        tool_obj = MagicMock()
        tool_obj.call_tool.return_value = {"result": "ok"}

        with _patch_sdk_config(), \
             patch("agentrun.tool.Tool.get_by_name", return_value=tool_obj):
            runner = CliRunner()
            with runner.isolated_filesystem():
                with open("args.json", "w") as f:
                    json.dump({"city": "北京"}, f)
                result = runner.invoke(cli, [
                    "tool", "invoke",
                    "--name", "mcp-w",
                    "--sub-tool", "get_weather",
                    "--arguments-file", "args.json",
                ])
        assert result.exit_code == 0, result.output

    def test_invoke_no_args(self):
        tool_obj = MagicMock()
        tool_obj.call_tool.return_value = {"status": "pong"}

        with _patch_sdk_config(), \
             patch("agentrun.tool.Tool.get_by_name", return_value=tool_obj):
            runner = CliRunner()
            result = runner.invoke(cli, [
                "tool", "invoke",
                "--name", "mcp-w",
                "--sub-tool", "ping",
            ])
        assert result.exit_code == 0, result.output
        out = json.loads(result.output)
        assert out["result"]["status"] == "pong"

    def test_invoke_mutually_exclusive(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("args.json", "w") as f:
                json.dump({"x": 1}, f)
            result = runner.invoke(cli, [
                "tool", "invoke",
                "--name", "t",
                "--sub-tool", "fn",
                "--arguments", '{"a":1}',
                "--arguments-file", "args.json",
            ])
        assert result.exit_code != 0