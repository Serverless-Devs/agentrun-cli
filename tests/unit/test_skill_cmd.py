"""Unit tests for agentrun_cli.commands.skill_cmd — helpers and CLI commands."""

import base64
import io
import json
import os
import zipfile
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from agentrun_cli.commands.skill_cmd import (
    _ctx_cfg,
    _extract_description,
    _load_json_option,
    _serialize_tool,
    _zip_directory,
    skill_group,
)

# ---------------------------------------------------------------------------
# Helper: _ctx_cfg
# ---------------------------------------------------------------------------


class TestCtxCfg:
    def test_returns_profile_and_region(self):
        ctx = SimpleNamespace(obj={"profile": "dev", "region": "cn-hangzhou"})
        assert _ctx_cfg(ctx) == ("dev", "cn-hangzhou")

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
            tool_id="t-123",
            tool_name="my-skill",
            tool_type="SKILL",
            status="ACTIVE",
            description="A skill",
            created_at="2025-01-01",
            updated_at="2025-01-02",
        )
        result = _serialize_tool(t)
        assert result == {
            "tool_id": "t-123",
            "tool_name": "my-skill",
            "tool_type": "SKILL",
            "status": "ACTIVE",
            "description": "A skill",
            "created_at": "2025-01-01",
            "updated_at": "2025-01-02",
        }

    def test_none_fields_excluded(self):
        t = SimpleNamespace(
            tool_id=None,
            tool_name="s",
            tool_type=None,
            status=None,
            description=None,
            created_at=None,
            updated_at=None,
        )
        result = _serialize_tool(t)
        assert result == {"tool_name": "s"}

    def test_fallback_name_field(self):
        t = SimpleNamespace(name="fallback-name")
        result = _serialize_tool(t)
        assert result["tool_name"] == "fallback-name"

    def test_fallback_created_time(self):
        t = SimpleNamespace(created_time="2025-06-01")
        result = _serialize_tool(t)
        assert result["created_at"] == "2025-06-01"

    def test_fallback_last_modified_time(self):
        t = SimpleNamespace(last_modified_time="2025-06-02")
        result = _serialize_tool(t)
        assert result["updated_at"] == "2025-06-02"

    def test_fallback_last_updated_at(self):
        t = SimpleNamespace(last_updated_at="2025-06-03")
        result = _serialize_tool(t)
        assert result["updated_at"] == "2025-06-03"


# ---------------------------------------------------------------------------
# Helper: _zip_directory
# ---------------------------------------------------------------------------


class TestZipDirectory:
    def test_zips_directory(self, tmp_path):
        (tmp_path / "a.txt").write_text("hello")
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "b.txt").write_text("world")

        b64 = _zip_directory(str(tmp_path))
        raw = base64.b64decode(b64)
        buf = io.BytesIO(raw)
        with zipfile.ZipFile(buf, "r") as zf:
            names = sorted(zf.namelist())
            assert "a.txt" in names
            assert "sub/b.txt" in names
            assert zf.read("a.txt") == b"hello"
            assert zf.read("sub/b.txt") == b"world"

    def test_empty_directory(self, tmp_path):
        b64 = _zip_directory(str(tmp_path))
        raw = base64.b64decode(b64)
        buf = io.BytesIO(raw)
        with zipfile.ZipFile(buf, "r") as zf:
            assert zf.namelist() == []


# ---------------------------------------------------------------------------
# Helper: _load_json_option
# ---------------------------------------------------------------------------


class TestLoadJsonOption:
    def test_none(self):
        assert _load_json_option(None) is None

    def test_inline_json(self):
        assert _load_json_option('{"key": "val"}') == {"key": "val"}

    def test_file_path(self, tmp_path):
        f = tmp_path / "cfg.json"
        f.write_text('{"from": "file"}')
        assert _load_json_option(str(f)) == {"from": "file"}

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _load_json_option("{bad}")


# ---------------------------------------------------------------------------
# Helper: _extract_description
# ---------------------------------------------------------------------------


class TestExtractDescription:
    def test_extracts_from_frontmatter(self, tmp_path):
        md = tmp_path / "SKILL.md"
        md.write_text("---\ndescription: My cool skill\n---\n# Heading\n")
        assert _extract_description(str(md)) == "My cool skill"

    def test_quoted_description(self, tmp_path):
        md = tmp_path / "SKILL.md"
        md.write_text('---\ndescription: "Quoted desc"\n---\n')
        assert _extract_description(str(md)) == "Quoted desc"

    def test_no_frontmatter(self, tmp_path):
        md = tmp_path / "SKILL.md"
        md.write_text("# Just a heading\nNo frontmatter here.\n")
        assert _extract_description(str(md)) is None

    def test_no_description_key(self, tmp_path):
        md = tmp_path / "SKILL.md"
        md.write_text("---\nname: my-skill\n---\n")
        assert _extract_description(str(md)) is None

    def test_empty_description(self, tmp_path):
        md = tmp_path / "SKILL.md"
        md.write_text("---\ndescription:\n---\n")
        assert _extract_description(str(md)) is None

    def test_missing_file(self):
        assert _extract_description("/nonexistent/SKILL.md") is None


# ---------------------------------------------------------------------------
# CLI commands (via CliRunner, mock SDK)
# ---------------------------------------------------------------------------


class TestSkillListCommand:
    @patch("agentrun_cli.commands.skill_cmd.get_agentrun_client")
    def test_list_empty(self, mock_client_fn):
        client = MagicMock()
        mock_client_fn.return_value = (client, {}, MagicMock())
        items_container = SimpleNamespace(items=[])
        body = SimpleNamespace(data=items_container)
        client.list_tools_with_options.return_value = SimpleNamespace(body=body)

        runner = CliRunner()
        result = runner.invoke(skill_group, ["list"])
        assert result.exit_code == 0

    @patch("agentrun_cli.commands.skill_cmd.get_agentrun_client")
    def test_list_with_items(self, mock_client_fn):
        client = MagicMock()
        mock_client_fn.return_value = (client, {}, MagicMock())
        t1 = SimpleNamespace(
            tool_id="t1",
            tool_name="skill-a",
            tool_type="SKILL",
            status="ACTIVE",
            description=None,
            created_at=None,
            updated_at=None,
        )
        items_container = SimpleNamespace(items=[t1])
        body = SimpleNamespace(data=items_container)
        client.list_tools_with_options.return_value = SimpleNamespace(body=body)

        runner = CliRunner()
        result = runner.invoke(skill_group, ["list"])
        assert result.exit_code == 0
        assert "skill-a" in result.output

    @patch("agentrun_cli.commands.skill_cmd.get_agentrun_client")
    def test_list_with_pagination(self, mock_client_fn):
        client = MagicMock()
        mock_client_fn.return_value = (client, {}, MagicMock())
        items_container = SimpleNamespace(items=[])
        body = SimpleNamespace(data=items_container)
        client.list_tools_with_options.return_value = SimpleNamespace(body=body)

        runner = CliRunner()
        result = runner.invoke(
            skill_group, ["list", "--page-number", "2", "--page-size", "5"]
        )
        assert result.exit_code == 0


class TestSkillDeleteCommand:
    @patch("agentrun_cli.commands.skill_cmd.get_agentrun_client")
    def test_delete(self, mock_client_fn):
        client = MagicMock()
        mock_client_fn.return_value = (client, {}, MagicMock())

        runner = CliRunner()
        result = runner.invoke(skill_group, ["delete", "--name", "my-skill"])
        assert result.exit_code == 0
        client.delete_tool_with_options.assert_called_once()
        assert "my-skill" in result.output


class TestSkillCreateCommand:
    @patch("agentrun_cli.commands.skill_cmd.get_agentrun_client")
    def test_create_missing_skill_md(self, mock_client_fn):
        mock_client_fn.return_value = (MagicMock(), {}, MagicMock())

        runner = CliRunner()
        with runner.isolated_filesystem():
            os.makedirs("my-skill")
            result = runner.invoke(
                skill_group, ["create", "--name", "s", "--code-dir", "my-skill"]
            )
        assert result.exit_code != 0
        assert "SKILL.md" in result.output

    @patch("agentrun_cli.commands.skill_cmd.get_agentrun_client")
    def test_create_success(self, mock_client_fn):
        client = MagicMock()
        mock_client_fn.return_value = (client, {}, MagicMock())

        data = SimpleNamespace(
            tool_id="t-new",
            tool_name="s",
            tool_type="SKILL",
            status="CREATED",
            description=None,
            created_at=None,
            updated_at=None,
        )
        client.create_tool_with_options.return_value = SimpleNamespace(
            body=SimpleNamespace(data=data)
        )

        runner = CliRunner()
        with runner.isolated_filesystem():
            os.makedirs("my-skill")
            with open("my-skill/SKILL.md", "w") as f:
                f.write("---\ndescription: test skill\n---\n# Hello\n")
            result = runner.invoke(
                skill_group, ["create", "--name", "s", "--code-dir", "my-skill"]
            )

        assert result.exit_code == 0
        client.create_tool_with_options.assert_called_once()

    @patch("agentrun_cli.commands.skill_cmd.get_agentrun_client")
    def test_create_with_description_and_credential(self, mock_client_fn):
        client = MagicMock()
        mock_client_fn.return_value = (client, {}, MagicMock())

        data = SimpleNamespace(
            tool_id="t-new",
            tool_name="s",
            tool_type="SKILL",
            status="CREATED",
            description="explicit desc",
            created_at=None,
            updated_at=None,
        )
        client.create_tool_with_options.return_value = SimpleNamespace(
            body=SimpleNamespace(data=data)
        )

        runner = CliRunner()
        with runner.isolated_filesystem():
            os.makedirs("my-skill")
            with open("my-skill/SKILL.md", "w") as f:
                f.write("# Hello\n")
            result = runner.invoke(
                skill_group,
                [
                    "create",
                    "--name",
                    "s",
                    "--code-dir",
                    "my-skill",
                    "--description",
                    "explicit desc",
                    "--credential",
                    "cred-1",
                ],
            )

        assert result.exit_code == 0

    @patch("agentrun_cli.commands.skill_cmd.get_agentrun_client")
    def test_create_from_file(self, mock_client_fn):
        client = MagicMock()
        mock_client_fn.return_value = (client, {}, MagicMock())

        data = SimpleNamespace(
            tool_id="t-new",
            tool_name="s",
            tool_type="SKILL",
            status="CREATED",
            description=None,
            created_at=None,
            updated_at=None,
        )
        client.create_tool_with_options.return_value = SimpleNamespace(
            body=SimpleNamespace(data=data)
        )

        runner = CliRunner()
        with runner.isolated_filesystem():
            os.makedirs("my-skill")
            with open("my-skill/SKILL.md", "w") as f:
                f.write("# Hello\n")
            with open("config.json", "w") as f:
                json.dump({"tool_name": "s", "description": "from file"}, f)
            result = runner.invoke(
                skill_group,
                [
                    "create",
                    "--name",
                    "s",
                    "--code-dir",
                    "my-skill",
                    "--from-file",
                    "config.json",
                ],
            )

        assert result.exit_code == 0

    @patch("agentrun_cli.commands.skill_cmd.get_agentrun_client")
    def test_create_null_data_response(self, mock_client_fn):
        client = MagicMock()
        mock_client_fn.return_value = (client, {}, MagicMock())
        client.create_tool_with_options.return_value = SimpleNamespace(
            body=SimpleNamespace(data=None)
        )

        runner = CliRunner()
        with runner.isolated_filesystem():
            os.makedirs("my-skill")
            with open("my-skill/SKILL.md", "w") as f:
                f.write("---\ndescription: test\n---\n")
            result = runner.invoke(
                skill_group, ["create", "--name", "s", "--code-dir", "my-skill"]
            )

        assert result.exit_code == 0
        assert "s" in result.output


class TestSkillGetCommand:
    @patch("agentrun_cli.commands.skill_cmd.build_sdk_config")
    @patch("agentrun_cli.commands.skill_cmd.format_output")
    def test_get(self, mock_fmt, mock_cfg):
        mock_cfg.return_value = MagicMock()
        tool_obj = SimpleNamespace(
            tool_id="t-1",
            tool_name="web-scraper",
            tool_type="SKILL",
            status="ACTIVE",
            description="A scraper",
            created_at=None,
            updated_at=None,
        )
        with patch("agentrun.tool.Tool.get_by_name", return_value=tool_obj):
            runner = CliRunner()
            result = runner.invoke(skill_group, ["get", "--name", "web-scraper"])
        assert result.exit_code == 0


class TestSkillDownloadCommand:
    @patch("agentrun_cli.commands.skill_cmd.build_sdk_config")
    def test_download(self, mock_cfg):
        mock_cfg.return_value = MagicMock()
        tool_obj = MagicMock()
        tool_obj.download_skill.return_value = "/tmp/.skills/web-scraper"
        with patch("agentrun.tool.Tool.get_by_name", return_value=tool_obj):
            runner = CliRunner()
            result = runner.invoke(skill_group, ["download", "--name", "web-scraper"])
        assert result.exit_code == 0
        assert "web-scraper" in result.output

    @patch("agentrun_cli.commands.skill_cmd.build_sdk_config")
    def test_download_custom_dir(self, mock_cfg):
        mock_cfg.return_value = MagicMock()
        tool_obj = MagicMock()
        tool_obj.download_skill.return_value = "/custom/web-scraper"
        with patch("agentrun.tool.Tool.get_by_name", return_value=tool_obj):
            runner = CliRunner()
            result = runner.invoke(
                skill_group, ["download", "--name", "web-scraper", "--dir", "/custom"]
            )
        assert result.exit_code == 0


class TestSkillScanCommand:
    def test_scan(self):
        skill1 = SimpleNamespace(
            name="s1", description="Skill 1", version="1.0", path="/skills/s1"
        )
        skill2 = SimpleNamespace(
            name="s2", description="Skill 2", version="2.0", path="/skills/s2"
        )
        mock_loader = MagicMock()
        mock_loader.scan_skills.return_value = [skill1, skill2]

        with patch(
            "agentrun.integration.utils.skill_loader.SkillLoader",
            return_value=mock_loader,
        ):
            runner = CliRunner()
            result = runner.invoke(skill_group, ["scan", "--dir", "/skills"])
        assert result.exit_code == 0
        assert "s1" in result.output
        assert "s2" in result.output


class TestSkillLoadCommand:
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
            result = runner.invoke(skill_group, ["load", "--name", "web-scraper"])
        assert result.exit_code == 0
        assert "web-scraper" in result.output

    def test_load_not_found(self):
        mock_loader = MagicMock()
        mock_loader.load_skill.return_value = None

        with patch(
            "agentrun.integration.utils.skill_loader.SkillLoader",
            return_value=mock_loader,
        ):
            runner = CliRunner()
            result = runner.invoke(skill_group, ["load", "--name", "nonexistent"])
        assert result.exit_code != 0
        assert "not found" in result.output


class TestSkillReadFileCommand:
    def test_read_file_content(self):
        mock_loader = MagicMock()
        mock_loader._read_skill_file_func.return_value = json.dumps(
            {"content": "print('hi')"}
        )

        with patch(
            "agentrun.integration.utils.skill_loader.SkillLoader",
            return_value=mock_loader,
        ):
            runner = CliRunner()
            result = runner.invoke(
                skill_group, ["read-file", "--name", "s", "--path", "main.py"]
            )
        assert result.exit_code == 0
        assert "print('hi')" in result.output

    def test_read_file_error(self):
        mock_loader = MagicMock()
        mock_loader._read_skill_file_func.return_value = json.dumps(
            {"error": "File not found"}
        )

        with patch(
            "agentrun.integration.utils.skill_loader.SkillLoader",
            return_value=mock_loader,
        ):
            runner = CliRunner()
            result = runner.invoke(
                skill_group, ["read-file", "--name", "s", "--path", "missing.py"]
            )
        assert result.exit_code != 0
        assert "File not found" in result.output

    def test_read_file_directory_listing(self):
        mock_loader = MagicMock()
        mock_loader._read_skill_file_func.return_value = json.dumps(
            {"entries": ["a.py", "b.py"]}
        )

        with patch(
            "agentrun.integration.utils.skill_loader.SkillLoader",
            return_value=mock_loader,
        ):
            runner = CliRunner()
            result = runner.invoke(
                skill_group, ["read-file", "--name", "s", "--path", "."]
            )
        assert result.exit_code == 0
        assert "a.py" in result.output


class TestSkillExecCommand:
    def test_exec_success(self):
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
                    skill_group,
                    [
                        "exec",
                        "--name",
                        "my-skill",
                        "--command",
                        "echo hello",
                    ],
                )
        assert result.exit_code == 0
        assert "hello" in result.output

    def test_exec_missing_dir(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                skill_group,
                [
                    "exec",
                    "--name",
                    "nonexistent",
                    "--command",
                    "echo hi",
                ],
            )
        assert result.exit_code != 0
        assert "not found" in result.output

    def test_exec_custom_dir_and_timeout(self):
        mock_loader = MagicMock()
        mock_loader._execute_command_func.return_value = json.dumps(
            {"stdout": "ok\n", "stderr": "", "exit_code": 0}
        )

        with patch(
            "agentrun.integration.utils.skill_loader.SkillLoader",
            return_value=mock_loader,
        ):
            runner = CliRunner()
            with runner.isolated_filesystem():
                os.makedirs("custom-skills/my-skill")
                result = runner.invoke(
                    skill_group,
                    [
                        "exec",
                        "--name",
                        "my-skill",
                        "--command",
                        "ls",
                        "--dir",
                        "custom-skills",
                        "--timeout",
                        "60",
                    ],
                )
        assert result.exit_code == 0
