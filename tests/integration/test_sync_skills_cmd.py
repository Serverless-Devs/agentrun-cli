"""Integration tests for top-level ``ar sync-skills`` command."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from agentrun_cli.main import cli


def _mock_models_module():
    mod = MagicMock()
    mod.ListToolsRequest = MagicMock(side_effect=lambda **kw: SimpleNamespace(**kw))
    return mod


class TestSyncSkillsCommand:

    @patch(
        "agentrun_cli.commands.sync_skills_cmd.build_sdk_config",
        return_value=MagicMock(),
    )
    @patch("agentrun.tool.Tool.get_by_name")
    @patch("agentrun_cli.commands.sync_skills_cmd.get_agentrun_client")
    def test_sync_success(self, mock_client_fn, mock_get_tool, _mock_cfg):
        items = [SimpleNamespace(tool_name="skill-a", updated_at="2026-01-01")]
        client = MagicMock()
        client.list_tools_with_options.return_value = SimpleNamespace(
            body=SimpleNamespace(data=SimpleNamespace(items=items))
        )
        mock_client_fn.return_value = (client, {}, MagicMock())

        tool_obj = MagicMock()
        tool_obj.download_skill.return_value = "/tmp/skills/skill-a"
        mock_get_tool.return_value = tool_obj

        mock_models = _mock_models_module()
        with patch.dict(
            "sys.modules",
            {
                "alibabacloud_agentrun20250910": MagicMock(),
                "alibabacloud_agentrun20250910.models": mock_models,
            },
        ):
            runner = CliRunner()
            result = runner.invoke(
                cli,
                ["sync-skills", "--claude-code", "--project", "-y"],
            )

        assert result.exit_code == 0, result.output
        out = json.loads(result.output)
        assert out["ai_tool"] == "claude-code"
        assert out["managed_skill_total"] == 1

    def test_sync_usage_error(self):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["sync-skills", "--claude-code", "--user", "--project"],
        )
        assert result.exit_code != 0
        assert "--user or --project" in result.output
