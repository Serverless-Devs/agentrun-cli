"""Integration tests for sandbox CLI commands."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from agentrun_cli.main import cli


def _mock_sandbox_modules():
    """Build mock SDK modules for sandbox commands."""
    mock_sandbox_mod = MagicMock()

    # TemplateType as identity function
    mock_sandbox_mod.TemplateType = MagicMock(side_effect=lambda x: x)
    mock_sandbox_mod.TemplateInput = MagicMock(side_effect=lambda **kw: SimpleNamespace(**kw))
    mock_sandbox_mod.PageableInput = MagicMock(side_effect=lambda **kw: SimpleNamespace(**kw))
    mock_sandbox_mod.ListSandboxesInput = MagicMock(side_effect=lambda **kw: SimpleNamespace(**kw))
    mock_sandbox_mod.SandboxInput = MagicMock(side_effect=lambda **kw: SimpleNamespace(**kw))
    mock_sandbox_mod.NASConfig = MagicMock(side_effect=lambda **kw: SimpleNamespace(**kw))
    mock_sandbox_mod.OSSMountConfig = MagicMock(side_effect=lambda **kw: SimpleNamespace(**kw))
    mock_sandbox_mod.TemplateNetworkConfiguration = MagicMock(side_effect=lambda **kw: SimpleNamespace(**kw))
    mock_sandbox_mod.TemplateCredentialConfiguration = MagicMock(side_effect=lambda **kw: SimpleNamespace(**kw))
    mock_sandbox_mod.TemplateContainerConfiguration = MagicMock(side_effect=lambda **kw: SimpleNamespace(**kw))

    return mock_sandbox_mod


def _make_template_obj(**overrides):
    defaults = {
        "template_id": "tpl-xxx",
        "template_name": "test-tpl",
        "template_type": "CodeInterpreter",
        "cpu": 2.0,
        "memory": 4096,
        "disk_size": 512,
        "status": "READY",
        "created_at": "2026-01-01T00:00:00Z",
        "last_updated_at": "2026-01-01T00:00:00Z",
    }
    defaults.update(overrides)
    mock = MagicMock()
    mock.model_dump.return_value = defaults
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


def _make_sandbox_obj(**overrides):
    defaults = {
        "sandbox_id": "sb-xxx",
        "template_name": "test-tpl",
        "status": "Running",
        "created_at": "2026-01-01T00:00:00Z",
    }
    defaults.update(overrides)
    mock = MagicMock()
    mock.model_dump.return_value = defaults
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


def _patch_sdk(mock_mod):
    return patch.dict("sys.modules", {
        "agentrun": MagicMock(),
        "agentrun.sandbox": mock_mod,
        "agentrun.utils": MagicMock(),
        "agentrun.utils.config": MagicMock(Config=MagicMock(return_value=MagicMock())),
    })


class TestSandboxHelp:

    def test_sandbox_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["sandbox", "--help"])
        assert result.exit_code == 0
        assert "template" in result.output
        assert "create" in result.output
        assert "exec" in result.output
        assert "file" in result.output

    def test_sb_alias(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["sb", "--help"])
        assert result.exit_code == 0
        assert "template" in result.output

    def test_sub_group_aliases(self):
        runner = CliRunner()
        for alias, full in [("tpl", "template"), ("ctx", "context"), ("f", "file"), ("ps", "process"), ("br", "browser")]:
            result = runner.invoke(cli, ["sb", alias, "--help"])
            assert result.exit_code == 0, f"Alias {alias} failed: {result.output}"


class TestTemplateCommands:

    def test_template_create(self):
        mock_mod = _mock_sandbox_modules()
        tpl = _make_template_obj()
        mock_mod.Sandbox.create_template.return_value = tpl
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(cli, [
                "sandbox", "template", "create",
                "--type", "CodeInterpreter",
                "--name", "test-tpl",
            ])
            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert data["template_name"] == "test-tpl"

    def test_template_get(self):
        mock_mod = _mock_sandbox_modules()
        tpl = _make_template_obj()
        mock_mod.Sandbox.get_template.return_value = tpl
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(cli, ["sandbox", "template", "get", "test-tpl"])
            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert data["template_name"] == "test-tpl"

    def test_template_list(self):
        mock_mod = _mock_sandbox_modules()
        mock_mod.Sandbox.list_templates.return_value = [_make_template_obj(), _make_template_obj(template_name="tpl2")]
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(cli, ["sandbox", "template", "list"])
            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert len(data) == 2

    def test_template_update(self):
        mock_mod = _mock_sandbox_modules()
        existing = _make_template_obj()
        mock_mod.Sandbox.get_template.return_value = existing
        mock_mod.Sandbox.update_template.return_value = _make_template_obj(cpu=4.0)
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(cli, [
                "sandbox", "template", "update", "test-tpl",
                "--cpu", "4",
            ])
            assert result.exit_code == 0, result.output

    def test_template_delete(self):
        mock_mod = _mock_sandbox_modules()
        mock_mod.Sandbox.delete_template.return_value = None
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(cli, ["sandbox", "template", "delete", "test-tpl"])
            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert data["status"] == "DELETED"

    def test_template_create_from_file(self, tmp_path):
        mock_mod = _mock_sandbox_modules()
        tpl = _make_template_obj()
        mock_mod.Sandbox.create_template.return_value = tpl
        f = tmp_path / "tpl.json"
        f.write_text(json.dumps({"template_type": "CodeInterpreter", "template_name": "from-file"}))
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(cli, [
                "sandbox", "template", "create",
                "--type", "CodeInterpreter",
                "--from-file", str(f),
            ])
            assert result.exit_code == 0, result.output


class TestLifecycleCommands:

    def test_sandbox_create(self):
        mock_mod = _mock_sandbox_modules()
        sb = _make_sandbox_obj()
        mock_mod.Sandbox.create.return_value = sb
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(cli, [
                "sandbox", "create",
                "--template", "test-tpl",
                "--type", "CodeInterpreter",
            ])
            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert data["sandbox_id"] == "sb-xxx"

    def test_sandbox_get(self):
        mock_mod = _mock_sandbox_modules()
        sb = _make_sandbox_obj()
        mock_mod.Sandbox.connect.return_value = sb
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(cli, ["sandbox", "get", "sb-xxx"])
            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert data["sandbox_id"] == "sb-xxx"

    def test_sandbox_list(self):
        mock_mod = _mock_sandbox_modules()
        sb1 = _make_sandbox_obj(sandbox_id="sb-1")
        sb2 = _make_sandbox_obj(sandbox_id="sb-2")
        list_output = MagicMock()
        list_output.sandboxes = [sb1, sb2]
        list_output.next_token = None
        mock_mod.Sandbox.list.return_value = list_output
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(cli, ["sandbox", "list"])
            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert len(data["sandboxes"]) == 2

    def test_sandbox_stop(self):
        mock_mod = _mock_sandbox_modules()
        mock_mod.Sandbox.stop_by_id.return_value = None
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(cli, ["sandbox", "stop", "sb-xxx"])
            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert data["status"] == "Stopped"

    def test_sandbox_delete(self):
        mock_mod = _mock_sandbox_modules()
        mock_mod.Sandbox.delete_by_id.return_value = None
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(cli, ["sandbox", "delete", "sb-xxx"])
            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert data["status"] == "Deleted"

    def test_sandbox_health(self):
        mock_mod = _mock_sandbox_modules()
        sb = _make_sandbox_obj()
        sb.check_health.return_value = {"status": "ok"}
        mock_mod.Sandbox.connect.return_value = sb
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(cli, ["sandbox", "health", "sb-xxx"])
            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert data["status"] == "ok"


class TestExecCommands:

    def test_exec_with_code(self):
        mock_mod = _mock_sandbox_modules()
        sb = _make_sandbox_obj()
        sb.context.execute.return_value = {"output": "hello\n", "error": "", "exit_code": 0}
        mock_mod.Sandbox.connect.return_value = sb
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(cli, [
                "sandbox", "exec", "sb-xxx",
                "--code", "print('hello')",
            ])
            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert data["output"] == "hello\n"

    def test_cmd(self):
        mock_mod = _mock_sandbox_modules()
        sb = _make_sandbox_obj()
        sb.process.cmd.return_value = {"stdout": "ok\n", "stderr": "", "exit_code": 0}
        mock_mod.Sandbox.connect.return_value = sb
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(cli, [
                "sandbox", "cmd", "sb-xxx",
                "--command", "echo ok",
                "--cwd", "/home/user",
            ])
            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert data["stdout"] == "ok\n"


class TestContextCommands:

    def test_context_create(self):
        mock_mod = _mock_sandbox_modules()
        sb = _make_sandbox_obj()
        sb.context.create.return_value = {"id": "ctx-xxx", "language": "python"}
        mock_mod.Sandbox.connect.return_value = sb
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(cli, ["sandbox", "context", "create", "sb-xxx"])
            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert data["id"] == "ctx-xxx"

    def test_context_list(self):
        mock_mod = _mock_sandbox_modules()
        sb = _make_sandbox_obj()
        sb.context.list.return_value = [{"id": "ctx-1"}, {"id": "ctx-2"}]
        mock_mod.Sandbox.connect.return_value = sb
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(cli, ["sandbox", "ctx", "list", "sb-xxx"])
            assert result.exit_code == 0, result.output

    def test_context_get(self):
        mock_mod = _mock_sandbox_modules()
        sb = _make_sandbox_obj()
        sb.context.get.return_value = {"id": "ctx-xxx", "language": "python"}
        mock_mod.Sandbox.connect.return_value = sb
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(cli, ["sandbox", "ctx", "get", "sb-xxx", "ctx-xxx"])
            assert result.exit_code == 0, result.output

    def test_context_delete(self):
        mock_mod = _mock_sandbox_modules()
        sb = _make_sandbox_obj()
        sb.context.delete.return_value = None
        mock_mod.Sandbox.connect.return_value = sb
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(cli, ["sandbox", "ctx", "delete", "sb-xxx", "ctx-xxx"])
            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert data["deleted"] is True


class TestFileCommands:

    def _setup(self):
        mock_mod = _mock_sandbox_modules()
        sb = _make_sandbox_obj()
        mock_mod.Sandbox.connect.return_value = sb
        return mock_mod, sb

    def test_file_read(self):
        mock_mod, sb = self._setup()
        sb.file.read.return_value = {"path": "/test.txt", "content": "hello"}
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(cli, ["sandbox", "file", "read", "sb-xxx", "/test.txt"])
            assert result.exit_code == 0, result.output

    def test_file_write(self):
        mock_mod, sb = self._setup()
        sb.file.write.return_value = {"path": "/test.txt", "size": 5, "success": True}
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(cli, ["sandbox", "f", "write", "sb-xxx", "/test.txt", "--content", "hello"])
            assert result.exit_code == 0, result.output

    def test_file_upload(self, tmp_path):
        mock_mod, sb = self._setup()
        sb.file_system.upload.return_value = {"success": True}
        local_file = tmp_path / "data.csv"
        local_file.write_text("a,b\n1,2")
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(cli, ["sandbox", "f", "upload", "sb-xxx", str(local_file), "/data.csv"])
            assert result.exit_code == 0, result.output

    def test_file_download(self):
        mock_mod, sb = self._setup()
        sb.file_system.download.return_value = {"saved_path": "./out.txt", "size": 10}
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(cli, ["sandbox", "f", "download", "sb-xxx", "/remote.txt", "./out.txt"])
            assert result.exit_code == 0, result.output

    def test_file_ls(self):
        mock_mod, sb = self._setup()
        sb.file_system.list.return_value = {"path": "/", "entries": []}
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(cli, ["sandbox", "f", "ls", "sb-xxx"])
            assert result.exit_code == 0, result.output

    def test_file_stat(self):
        mock_mod, sb = self._setup()
        sb.file_system.stat.return_value = {"path": "/test.txt", "type": "file", "size": 5}
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(cli, ["sandbox", "f", "stat", "sb-xxx", "/test.txt"])
            assert result.exit_code == 0, result.output

    def test_file_mv(self):
        mock_mod, sb = self._setup()
        sb.file_system.move.return_value = {"success": True}
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(cli, ["sandbox", "f", "mv", "sb-xxx", "/old.txt", "/new.txt"])
            assert result.exit_code == 0, result.output

    def test_file_rm(self):
        mock_mod, sb = self._setup()
        sb.file_system.remove.return_value = {"success": True}
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(cli, ["sandbox", "f", "rm", "sb-xxx", "/tmp.txt"])
            assert result.exit_code == 0, result.output

    def test_file_mkdir(self):
        mock_mod, sb = self._setup()
        sb.file_system.mkdir.return_value = {"success": True}
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(cli, ["sandbox", "f", "mkdir", "sb-xxx", "/new_dir"])
            assert result.exit_code == 0, result.output


class TestProcessCommands:

    def test_process_list(self):
        mock_mod = _mock_sandbox_modules()
        sb = _make_sandbox_obj()
        sb.process.list.return_value = [{"pid": "1", "command": "init"}]
        mock_mod.Sandbox.connect.return_value = sb
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(cli, ["sandbox", "ps", "list", "sb-xxx"])
            assert result.exit_code == 0, result.output

    def test_process_get(self):
        mock_mod = _mock_sandbox_modules()
        sb = _make_sandbox_obj()
        sb.process.get.return_value = {"pid": "128", "command": "python"}
        mock_mod.Sandbox.connect.return_value = sb
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(cli, ["sandbox", "ps", "get", "sb-xxx", "128"])
            assert result.exit_code == 0, result.output

    def test_process_kill(self):
        mock_mod = _mock_sandbox_modules()
        sb = _make_sandbox_obj()
        sb.process.kill.return_value = None
        mock_mod.Sandbox.connect.return_value = sb
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(cli, ["sandbox", "ps", "kill", "sb-xxx", "128"])
            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert data["killed"] is True


class TestBrowserCommands:

    def test_cdp_url(self):
        mock_mod = _mock_sandbox_modules()
        sb = _make_sandbox_obj()
        sb.get_cdp_url.return_value = "wss://example.com/cdp"
        mock_mod.Sandbox.connect.return_value = sb
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(cli, ["sandbox", "br", "cdp-url", "sb-xxx"])
            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert "cdp_url" in data

    def test_cdp_url_with_headers(self):
        mock_mod = _mock_sandbox_modules()
        sb = _make_sandbox_obj()
        sb.get_cdp_url.return_value = ("wss://example.com/cdp", {"Authorization": "Bearer xxx"})
        mock_mod.Sandbox.connect.return_value = sb
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(cli, ["sandbox", "br", "cdp-url", "sb-xxx", "--with-headers"])
            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert "headers" in data

    def test_vnc_url(self):
        mock_mod = _mock_sandbox_modules()
        sb = _make_sandbox_obj()
        sb.get_vnc_url.return_value = "wss://example.com/vnc"
        mock_mod.Sandbox.connect.return_value = sb
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(cli, ["sandbox", "br", "vnc-url", "sb-xxx"])
            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert "vnc_url" in data

    def test_navigate(self):
        mock_mod = _mock_sandbox_modules()
        sb = _make_sandbox_obj()
        mock_page = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_page.goto.return_value = mock_response
        mock_page.title.return_value = "Example"
        mock_pw = MagicMock()
        mock_pw.pages = [mock_page]
        sb.sync_playwright.return_value = mock_pw
        mock_mod.Sandbox.connect.return_value = sb
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(cli, ["sandbox", "br", "navigate", "sb-xxx", "https://example.com"])
            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert data["title"] == "Example"
            assert data["status"] == 200
