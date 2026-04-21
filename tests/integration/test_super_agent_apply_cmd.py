"""Integration tests for ``ar sa apply`` and ``ar sa render``."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from agentrun_cli.main import cli

VALID_YAML = """
apiVersion: agentrun/v1
kind: SuperAgent
metadata:
  name: my-helper
spec:
  prompt: You are helpful
  model:
    service: svc-tongyi
    name: qwen-max
  tools:
    - web-search
"""


def _make_agent(name, status="READY"):
    return SimpleNamespace(
        name=name, description=None, prompt=None,
        agents=[], tools=[], skills=[], sandboxes=[], workspaces=[],
        model_service_name=None, model_name=None,
        agent_runtime_id="ar-xxx", arn="", status=status,
        external_endpoint="", created_at="", last_updated_at="",
    )


class TestRenderDryRun:

    def test_render_prints_rendered_input(self):
        fake_input = MagicMock()
        fake_input.model_dump.return_value = {
            "agentRuntimeName": "my-helper",
            "tags": ["x-agentrun-external", "x-agentrun-super-agent"],
        }
        with patch(
            "agentrun_cli.commands.super_agent.apply_cmd.to_create_input",
            return_value=fake_input,
        ), patch(
            "agentrun_cli.commands.super_agent.apply_cmd.build_sdk_config",
            return_value=MagicMock(),
        ):
            runner = CliRunner()
            with runner.isolated_filesystem():
                with open("sa.yaml", "w") as f:
                    f.write(VALID_YAML)
                result = runner.invoke(cli, ["sa", "render", "-f", "sa.yaml"])
        assert result.exit_code == 0, result.output
        out = json.loads(result.output)
        assert isinstance(out, list)
        assert out[0]["kind"] == "SuperAgent"
        assert out[0]["name"] == "my-helper"
        assert "rendered_create_input" in out[0]

    def test_render_invalid_yaml_exits_nonzero(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("bad.yaml", "w") as f:
                f.write(
                    "apiVersion: wrong/v1\nkind: SuperAgent\n"
                    "metadata:\n  name: x\nspec: {}\n"
                )
            result = runner.invoke(cli, ["sa", "render", "-f", "bad.yaml"])
        assert result.exit_code != 0


class TestApplyCreate:

    def test_apply_creates_when_absent(self):
        client = MagicMock()
        client.get.side_effect = ValueError("not found")
        client.create.return_value = _make_agent("my-helper")
        with patch(
            "agentrun_cli.commands.super_agent.apply_cmd.SuperAgentClient",
            return_value=client,
        ), patch(
            "agentrun_cli.commands.super_agent.apply_cmd.build_sdk_config",
            return_value=MagicMock(),
        ):
            runner = CliRunner()
            with runner.isolated_filesystem():
                with open("sa.yaml", "w") as f:
                    f.write(VALID_YAML)
                result = runner.invoke(cli, ["sa", "apply", "-f", "sa.yaml"])
        assert result.exit_code == 0, result.output
        out = json.loads(result.output)
        assert out[0]["action"] == "created"
        assert out[0]["name"] == "my-helper"
        client.create.assert_called_once()


class TestApplyUpdate:

    def test_apply_updates_when_present(self):
        client = MagicMock()
        client.get.return_value = _make_agent("my-helper")
        client.update.return_value = _make_agent("my-helper")
        with patch(
            "agentrun_cli.commands.super_agent.apply_cmd.SuperAgentClient",
            return_value=client,
        ), patch(
            "agentrun_cli.commands.super_agent.apply_cmd.build_sdk_config",
            return_value=MagicMock(),
        ):
            runner = CliRunner()
            with runner.isolated_filesystem():
                with open("sa.yaml", "w") as f:
                    f.write(VALID_YAML)
                result = runner.invoke(cli, ["sa", "apply", "-f", "sa.yaml"])
        assert result.exit_code == 0, result.output
        out = json.loads(result.output)
        assert out[0]["action"] == "updated"
        client.update.assert_called_once()


class TestApplyDryRun:

    def test_dry_run_no_api_calls(self):
        client = MagicMock()
        fake_input = MagicMock()
        fake_input.model_dump.return_value = {"agentRuntimeName": "my-helper"}
        with patch(
            "agentrun_cli.commands.super_agent.apply_cmd.SuperAgentClient",
            return_value=client,
        ), patch(
            "agentrun_cli.commands.super_agent.apply_cmd.to_create_input",
            return_value=fake_input,
        ), patch(
            "agentrun_cli.commands.super_agent.apply_cmd.build_sdk_config",
            return_value=MagicMock(),
        ):
            runner = CliRunner()
            with runner.isolated_filesystem():
                with open("sa.yaml", "w") as f:
                    f.write(VALID_YAML)
                result = runner.invoke(cli, [
                    "sa", "apply", "-f", "sa.yaml", "--dry-run",
                ])
        assert result.exit_code == 0, result.output
        client.create.assert_not_called()
        client.update.assert_not_called()


class TestApplyMultiDoc:

    def test_multi_doc(self):
        client = MagicMock()
        client.get.side_effect = ValueError("not found")
        client.create.side_effect = [_make_agent("a"), _make_agent("b")]
        multi = (
            "apiVersion: agentrun/v1\nkind: SuperAgent\n"
            "metadata:\n  name: a\nspec:\n  prompt: p1\n"
            "---\n"
            "apiVersion: agentrun/v1\nkind: SuperAgent\n"
            "metadata:\n  name: b\nspec:\n  prompt: p2\n"
        )
        with patch(
            "agentrun_cli.commands.super_agent.apply_cmd.SuperAgentClient",
            return_value=client,
        ), patch(
            "agentrun_cli.commands.super_agent.apply_cmd.build_sdk_config",
            return_value=MagicMock(),
        ):
            runner = CliRunner()
            with runner.isolated_filesystem():
                with open("stack.yaml", "w") as f:
                    f.write(multi)
                result = runner.invoke(
                    cli, ["sa", "apply", "-f", "stack.yaml"],
                )
        assert result.exit_code == 0, result.output
        out = json.loads(result.output)
        assert [r["name"] for r in out] == ["a", "b"]
        assert all(r["action"] == "created" for r in out)
