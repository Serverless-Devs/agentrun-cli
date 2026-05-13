"""Integration tests for model commands — all sub-commands via CliRunner."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from agentrun_cli.main import cli


def _make_mock_service(**overrides):
    defaults = {
        "model_service_name": "test-svc",
        "provider": "tongyi",
        "model_type": "llm",
        "description": "test desc",
        "status": "active",
        "provider_settings": None,
        "model_info_configs": None,
        "credential_name": None,
        "created_at": "2025-01-01T00:00:00Z",
        "last_updated_at": "2025-01-01T00:00:00Z",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _sdk_patches():
    mock_model_module = MagicMock()
    mock_model_module.ModelType = MagicMock(side_effect=lambda x: x)
    mock_model_module.ModelServiceCreateInput = MagicMock(
        side_effect=lambda **kw: SimpleNamespace(**kw)
    )
    mock_model_module.ModelServiceUpdateInput = MagicMock(
        side_effect=lambda **kw: SimpleNamespace(**kw)
    )
    mock_model_module.ProviderSettings = MagicMock(
        side_effect=lambda **kw: SimpleNamespace(**kw)
    )
    return mock_model_module


def _patch_sdk(mock_mod):
    return patch.dict(
        "sys.modules",
        {
            "agentrun": MagicMock(),
            "agentrun.model": mock_mod,
            "agentrun.utils": MagicMock(),
            "agentrun.utils.config": MagicMock(
                Config=MagicMock(return_value=MagicMock())
            ),
        },
    )


class TestModelCreate:
    def test_create_with_flags(self):
        mock_mod = _sdk_patches()
        mock_mod.ModelService.create.return_value = _make_mock_service()
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "model",
                    "create",
                    "--name",
                    "test-svc",
                    "--provider",
                    "tongyi",
                    "--model-type",
                    "llm",
                    "--model-names",
                    "qwen-max,qwen-plus",
                    "--api-key",
                    "sk-test",
                    "--base-url",
                    "https://api.example.com",
                    "--description",
                    "my model",
                ],
            )
            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert data["model_service_name"] == "test-svc"

    def test_create_from_file(self, tmp_path):
        mock_mod = _sdk_patches()
        mock_mod.ModelService.create.return_value = _make_mock_service()
        payload_file = tmp_path / "input.json"
        payload_file.write_text(
            json.dumps(
                {
                    "model_service_name": "file-svc",
                    "provider": "openai",
                }
            )
        )
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "model",
                    "create",
                    "--name",
                    "file-svc",
                    "--provider",
                    "openai",
                    "--from-file",
                    str(payload_file),
                ],
            )
            assert result.exit_code == 0, result.output

    def test_create_with_credential(self):
        mock_mod = _sdk_patches()
        mock_mod.ModelService.create.return_value = _make_mock_service(
            credential_name="my-cred"
        )
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "model",
                    "create",
                    "--name",
                    "cred-svc",
                    "--provider",
                    "tongyi",
                    "--credential",
                    "my-cred",
                ],
            )
            assert result.exit_code == 0, result.output


class TestModelGet:
    def test_get_by_name(self):
        mock_mod = _sdk_patches()
        mock_mod.ModelService.get_by_name.return_value = _make_mock_service()
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(cli, ["model", "get", "--name", "test-svc"])
            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert data["model_service_name"] == "test-svc"


class TestModelList:
    def test_list_all(self):
        mock_mod = _sdk_patches()
        mock_mod.ModelService.list_all.return_value = [
            _make_mock_service(model_service_name="svc1"),
            _make_mock_service(model_service_name="svc2"),
        ]
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(cli, ["model", "list"])
            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert len(data) == 2

    def test_list_with_provider_filter(self):
        mock_mod = _sdk_patches()
        mock_mod.ModelService.list_all.return_value = []
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(cli, ["model", "list", "--provider", "openai"])
            assert result.exit_code == 0, result.output


class TestModelUpdate:
    def test_update_with_flags(self):
        mock_mod = _sdk_patches()
        mock_mod.ModelService.update_by_name.return_value = _make_mock_service(
            description="updated"
        )
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "model",
                    "update",
                    "--name",
                    "test-svc",
                    "--description",
                    "updated",
                    "--api-key",
                    "new-key",
                    "--base-url",
                    "https://new.api",
                    "--credential",
                    "new-cred",
                ],
            )
            assert result.exit_code == 0, result.output

    def test_update_description_only_no_provider_settings(self):
        mock_mod = _sdk_patches()
        mock_mod.ModelService.update_by_name.return_value = _make_mock_service(
            description="desc only"
        )
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "model",
                    "update",
                    "--name",
                    "test-svc",
                    "--description",
                    "desc only",
                ],
            )
            assert result.exit_code == 0, result.output
            mock_mod.ProviderSettings.assert_not_called()

    def test_update_from_file(self, tmp_path):
        mock_mod = _sdk_patches()
        mock_mod.ModelService.update_by_name.return_value = _make_mock_service()
        payload_file = tmp_path / "update.json"
        payload_file.write_text(json.dumps({"description": "file update"}))
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "model",
                    "update",
                    "--name",
                    "test-svc",
                    "--from-file",
                    str(payload_file),
                ],
            )
            assert result.exit_code == 0, result.output


class TestModelDelete:
    def test_delete_by_name(self):
        mock_mod = _sdk_patches()
        mock_mod.ModelService.delete_by_name.return_value = None
        with _patch_sdk(mock_mod):
            runner = CliRunner()
            result = runner.invoke(cli, ["model", "delete", "--name", "test-svc"])
            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert data["deleted"] == "test-svc"
