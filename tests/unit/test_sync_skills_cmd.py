"""Unit tests for ``agentrun_cli.commands.sync_skills_cmd``."""

import json
import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from agentrun_cli.commands.sync_skills_cmd import sync_skills


def _mock_models_module():
    mod = MagicMock()
    mod.ListToolsRequest = MagicMock(side_effect=lambda **kw: SimpleNamespace(**kw))
    return mod


def _patch_client_with_items(items):
    client = MagicMock()
    client.list_tools_with_options.return_value = SimpleNamespace(
        body=SimpleNamespace(data=SimpleNamespace(items=items))
    )
    return patch(
        "agentrun_cli.commands.sync_skills_cmd.get_agentrun_client",
        return_value=(client, {}, MagicMock()),
    )


def _patch_tool_download():
    def _make_tool(name, **_kwargs):
        obj = MagicMock()
        obj.download_skill.return_value = f"/fake/skills/{name}"
        return obj

    return patch("agentrun.tool.Tool.get_by_name", side_effect=_make_tool)


class TestSyncSkillsValidation:

    def test_requires_exactly_one_tool(self):
        runner = CliRunner()
        result = runner.invoke(sync_skills, ["--user"])
        assert result.exit_code != 0
        assert "--claude-code or --codex" in result.output

    def test_rejects_both_tool_flags(self):
        runner = CliRunner()
        result = runner.invoke(sync_skills, ["--claude-code", "--codex", "--user"])
        assert result.exit_code != 0
        assert "--claude-code or --codex" in result.output

    def test_requires_exactly_one_scope(self):
        runner = CliRunner()
        result = runner.invoke(sync_skills, ["--claude-code"])
        assert result.exit_code != 0
        assert "--user or --project" in result.output

    def test_rejects_both_scope_flags(self):
        runner = CliRunner()
        result = runner.invoke(sync_skills, ["--claude-code", "--user", "--project"])
        assert result.exit_code != 0
        assert "--user or --project" in result.output


class TestSyncSkillsCommand:

    @patch(
        "agentrun_cli.commands.sync_skills_cmd.build_sdk_config",
        return_value=MagicMock(),
    )
    def test_sync_all_with_confirmation(self, _mock_cfg):
        items = [
            SimpleNamespace(tool_name="skill-a", updated_at="2026-01-01"),
            SimpleNamespace(tool_name="skill-b", updated_at="2026-01-02"),
        ]
        mock_models = _mock_models_module()

        with _patch_client_with_items(items), _patch_tool_download(), patch.dict(
            "sys.modules",
            {
                "alibabacloud_agentrun20250910": MagicMock(),
                "alibabacloud_agentrun20250910.models": mock_models,
            },
        ):
            runner = CliRunner()
            with runner.isolated_filesystem():
                result = runner.invoke(
                    sync_skills,
                    ["--claude-code", "--user"],
                    input="y\n",
                    env={"HOME": os.getcwd()},
                )

        assert result.exit_code == 0, result.output
        payload = result.output[result.output.find("{") :]
        out = json.loads(payload)
        assert out["managed_skill_total"] == 2
        assert len(out["downloaded"]) == 2

    @patch(
        "agentrun_cli.commands.sync_skills_cmd.build_sdk_config",
        return_value=MagicMock(),
    )
    def test_workspace_filter_and_skip_up_to_date(self, _mock_cfg):
        items = [
            SimpleNamespace(
                tool_name="skill-a",
                updated_at="2026-01-01",
                workspace_name="abc",
            ),
            SimpleNamespace(
                tool_name="skill-b",
                updated_at="2026-01-02",
                workspace_name="def",
            ),
        ]
        mock_models = _mock_models_module()

        with _patch_client_with_items(items), _patch_tool_download(), patch.dict(
            "sys.modules",
            {
                "alibabacloud_agentrun20250910": MagicMock(),
                "alibabacloud_agentrun20250910.models": mock_models,
            },
        ):
            runner = CliRunner()
            with runner.isolated_filesystem():
                os.makedirs(".claude/skills/skill-a", exist_ok=True)
                with open(
                    ".claude/skills/.agentrun-sync-skills.json",
                    "w",
                    encoding="utf-8",
                ) as f:
                    json.dump({"skill-a": {"updated_at": "2026-01-01"}}, f)

                result = runner.invoke(
                    sync_skills,
                    ["--claude-code", "--project", "--workspace", "abc", "-y"],
                )

        assert result.exit_code == 0, result.output
        out = json.loads(result.output)
        assert out["managed_skill_total"] == 1
        assert out["downloaded"] == []
        assert out["updated"] == []
        assert out["skipped"] == ["skill-a"]

    @patch(
        "agentrun_cli.commands.sync_skills_cmd.build_sdk_config",
        return_value=MagicMock(),
    )
    def test_delete_unmanaged(self, _mock_cfg):
        items = [SimpleNamespace(tool_name="skill-a", updated_at="2026-01-01")]
        mock_models = _mock_models_module()

        with _patch_client_with_items(items), _patch_tool_download(), patch.dict(
            "sys.modules",
            {
                "alibabacloud_agentrun20250910": MagicMock(),
                "alibabacloud_agentrun20250910.models": mock_models,
            },
        ):
            runner = CliRunner()
            with runner.isolated_filesystem():
                os.makedirs(".codex/skills/skill-a", exist_ok=True)
                os.makedirs(".codex/skills/skill-old", exist_ok=True)

                result = runner.invoke(
                    sync_skills,
                    ["--codex", "--project", "--delete-unmanaged", "-y"],
                )

                assert not os.path.exists(".codex/skills/skill-old")

        assert result.exit_code == 0, result.output
        out = json.loads(result.output)
        assert out["removed"] == ["skill-old"]
