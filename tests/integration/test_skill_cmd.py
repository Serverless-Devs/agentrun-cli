"""Integration tests for skill CLI commands (via top-level ``ar skill``)."""

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
    """Build mock alibabacloud_agentrun20250910.models module."""
    mod = MagicMock()
    mod.CreateToolInputV2 = MagicMock(side_effect=lambda **kw: SimpleNamespace(**kw))
    mod.CreateToolRequest = MagicMock(side_effect=lambda **kw: SimpleNamespace(**kw))
    mod.ListToolsRequest = MagicMock(side_effect=lambda **kw: SimpleNamespace(**kw))
    mod.CodeConfiguration = MagicMock(side_effect=lambda **kw: SimpleNamespace(**kw))
    return mod


def _make_tool_obj(**overrides):
    defaults = {
        "tool_id": "t-xxx",
        "tool_name": "test-skill",
        "tool_type": "SKILL",
        "status": "ACTIVE",
        "description": "Test skill",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-02T00:00:00Z",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _patch_inner_client(client):
    return patch(
        "agentrun_cli.commands.skill_cmd.get_agentrun_client",
        return_value=(client, {}, MagicMock()),
    )


def _patch_sdk_config():
    return patch(
        "agentrun_cli.commands.skill_cmd.build_sdk_config",
        return_value=MagicMock(),
    )


# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------


class TestSkillHelp:
    def test_skill_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["skill", "--help"])
        assert result.exit_code == 0
        assert "create" in result.output
        assert "list" in result.output
        assert "get" in result.output
        assert "delete" in result.output
        assert "download" in result.output
        assert "scan" in result.output
        assert "load" in result.output
        assert "read-file" in result.output
        assert "exec" in result.output


# ---------------------------------------------------------------------------
# Control-plane CRUD
# ---------------------------------------------------------------------------


class TestSkillCreate:
    def test_create_skill(self):
        mock_mod = _mock_agentrun_models()
        client = MagicMock()
        data = _make_tool_obj(tool_name="new-skill", status="CREATED")
        client.create_tool_with_options.return_value = SimpleNamespace(
            body=SimpleNamespace(data=data)
        )

        with (
            _patch_inner_client(client),
            patch.dict(
                "sys.modules",
                {
                    "alibabacloud_agentrun20250910": MagicMock(),
                    "alibabacloud_agentrun20250910.models": mock_mod,
                },
            ),
        ):
            runner = CliRunner()
            with runner.isolated_filesystem():
                os.makedirs("my-skill")
                with open("my-skill/SKILL.md", "w") as f:
                    f.write("---\ndescription: A test skill\n---\n# Skill\n")
                with open("my-skill/main.py", "w") as f:
                    f.write("print('hello')")
                result = runner.invoke(
                    cli,
                    [
                        "skill",
                        "create",
                        "--name",
                        "new-skill",
                        "--code-dir",
                        "my-skill",
                    ],
                )
        assert result.exit_code == 0, result.output
        out = json.loads(result.output)
        assert out["tool_name"] == "new-skill"

    def test_create_from_file(self):
        mock_mod = _mock_agentrun_models()
        client = MagicMock()
        data = _make_tool_obj(tool_name="from-file", status="CREATED")
        client.create_tool_with_options.return_value = SimpleNamespace(
            body=SimpleNamespace(data=data)
        )

        with (
            _patch_inner_client(client),
            patch.dict(
                "sys.modules",
                {
                    "alibabacloud_agentrun20250910": MagicMock(),
                    "alibabacloud_agentrun20250910.models": mock_mod,
                },
            ),
        ):
            runner = CliRunner()
            with runner.isolated_filesystem():
                os.makedirs("my-skill")
                with open("my-skill/SKILL.md", "w") as f:
                    f.write("# Hello\n")
                with open("config.json", "w") as f:
                    json.dump({"tool_name": "from-file", "description": "from file"}, f)
                result = runner.invoke(
                    cli,
                    [
                        "skill",
                        "create",
                        "--name",
                        "from-file",
                        "--code-dir",
                        "my-skill",
                        "--from-file",
                        "config.json",
                    ],
                )
        assert result.exit_code == 0, result.output


class TestSkillList:
    def test_list_skills(self):
        mock_mod = _mock_agentrun_models()
        client = MagicMock()
        t1 = _make_tool_obj(tool_name="skill-a")
        t2 = _make_tool_obj(tool_name="skill-b")
        items_container = SimpleNamespace(items=[t1, t2])
        body = SimpleNamespace(data=items_container)
        client.list_tools_with_options.return_value = SimpleNamespace(body=body)

        with (
            _patch_inner_client(client),
            patch.dict(
                "sys.modules",
                {
                    "alibabacloud_agentrun20250910": MagicMock(),
                    "alibabacloud_agentrun20250910.models": mock_mod,
                },
            ),
        ):
            runner = CliRunner()
            result = runner.invoke(cli, ["skill", "list"])
        assert result.exit_code == 0, result.output
        out = json.loads(result.output)
        assert len(out) == 2

    def test_list_with_pagination(self):
        mock_mod = _mock_agentrun_models()
        client = MagicMock()
        items_container = SimpleNamespace(items=[])
        body = SimpleNamespace(data=items_container)
        client.list_tools_with_options.return_value = SimpleNamespace(body=body)

        with (
            _patch_inner_client(client),
            patch.dict(
                "sys.modules",
                {
                    "alibabacloud_agentrun20250910": MagicMock(),
                    "alibabacloud_agentrun20250910.models": mock_mod,
                },
            ),
        ):
            runner = CliRunner()
            result = runner.invoke(
                cli, ["skill", "list", "--page-number", "2", "--page-size", "5"]
            )
        assert result.exit_code == 0, result.output


class TestSkillGet:
    def test_get_skill(self):
        tool_obj = _make_tool_obj(tool_name="web-scraper")
        with (
            _patch_sdk_config(),
            patch("agentrun.tool.Tool.get_by_name", return_value=tool_obj),
        ):
            runner = CliRunner()
            result = runner.invoke(cli, ["skill", "get", "--name", "web-scraper"])
        assert result.exit_code == 0, result.output
        out = json.loads(result.output)
        assert out["tool_name"] == "web-scraper"


class TestSkillDelete:
    def test_delete_skill(self):
        client = MagicMock()
        with _patch_inner_client(client):
            runner = CliRunner()
            result = runner.invoke(cli, ["skill", "delete", "--name", "old-skill"])
        assert result.exit_code == 0, result.output
        out = json.loads(result.output)
        assert out["deleted"] == "old-skill"
        client.delete_tool_with_options.assert_called_once()


class TestSkillDownload:
    def test_download_skill(self):
        tool_obj = MagicMock()
        tool_obj.download_skill.return_value = ".skills/web-scraper"
        with (
            _patch_sdk_config(),
            patch("agentrun.tool.Tool.get_by_name", return_value=tool_obj),
        ):
            runner = CliRunner()
            result = runner.invoke(cli, ["skill", "download", "--name", "web-scraper"])
        assert result.exit_code == 0, result.output
        out = json.loads(result.output)
        assert out["skill_name"] == "web-scraper"
        assert out["status"] == "downloaded"


# ---------------------------------------------------------------------------
# Local-side (data plane)
# ---------------------------------------------------------------------------


class TestSkillScan:
    def test_scan(self):
        s1 = SimpleNamespace(
            name="s1", description="Skill 1", version="1.0", path="/skills/s1"
        )
        mock_loader = MagicMock()
        mock_loader.scan_skills.return_value = [s1]

        with patch(
            "agentrun.integration.utils.skill_loader.SkillLoader",
            return_value=mock_loader,
        ):
            runner = CliRunner()
            result = runner.invoke(cli, ["skill", "scan", "--dir", "/skills"])
        assert result.exit_code == 0, result.output
        out = json.loads(result.output)
        assert len(out) == 1
        assert out[0]["name"] == "s1"


class TestSkillLoad:
    def test_load_found(self):
        detail = SimpleNamespace(
            name="web-scraper",
            description="A scraper",
            version="1.0",
            path="/skills/web-scraper",
            instruction="Do scraping",
            files=["scraper.py"],
        )
        mock_loader = MagicMock()
        mock_loader.load_skill.return_value = detail

        with patch(
            "agentrun.integration.utils.skill_loader.SkillLoader",
            return_value=mock_loader,
        ):
            runner = CliRunner()
            result = runner.invoke(cli, ["skill", "load", "--name", "web-scraper"])
        assert result.exit_code == 0, result.output
        out = json.loads(result.output)
        assert out["name"] == "web-scraper"
        assert out["instruction"] == "Do scraping"

    def test_load_not_found(self):
        mock_loader = MagicMock()
        mock_loader.load_skill.return_value = None

        with patch(
            "agentrun.integration.utils.skill_loader.SkillLoader",
            return_value=mock_loader,
        ):
            runner = CliRunner()
            result = runner.invoke(cli, ["skill", "load", "--name", "nope"])
        assert result.exit_code != 0


class TestSkillReadFile:
    def test_read_file(self):
        mock_loader = MagicMock()
        mock_loader._read_skill_file_func.return_value = json.dumps(
            {"content": "x = 1"}
        )

        with patch(
            "agentrun.integration.utils.skill_loader.SkillLoader",
            return_value=mock_loader,
        ):
            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "skill",
                    "read-file",
                    "--name",
                    "s",
                    "--path",
                    "main.py",
                ],
            )
        assert result.exit_code == 0, result.output
        assert "x = 1" in result.output


class TestSkillExec:
    def test_exec(self):
        mock_loader = MagicMock()
        mock_loader._execute_command_func.return_value = json.dumps(
            {"stdout": "hello\n", "stderr": "", "exit_code": 0}
        )

        with patch(
            "agentrun.integration.utils.skill_loader.SkillLoader",
            return_value=mock_loader,
        ):
            runner = CliRunner()
            with runner.isolated_filesystem():
                os.makedirs(".skills/my-skill")
                result = runner.invoke(
                    cli,
                    [
                        "skill",
                        "exec",
                        "--name",
                        "my-skill",
                        "--command",
                        "echo hello",
                    ],
                )
        assert result.exit_code == 0, result.output
        out = json.loads(result.output)
        assert out["exit_code"] == 0

    def test_exec_missing_dir(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                [
                    "skill",
                    "exec",
                    "--name",
                    "nope",
                    "--command",
                    "ls",
                ],
            )
        assert result.exit_code != 0
