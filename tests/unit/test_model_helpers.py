"""Unit tests for model_cmd helper functions."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from agentrun_cli.commands.model_cmd import _load_json_option, _serialize_model_service


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


class TestSerializeModelService:
    def test_with_provider_settings_and_configs(self):
        mock_settings = MagicMock()
        mock_settings.model_dump.return_value = {"api_key": "sk-xxx"}

        mock_config1 = MagicMock()
        mock_config1.model_dump.return_value = {"model_name": "qwen-max"}

        svc = _make_mock_service(
            provider_settings=mock_settings,
            model_info_configs=[mock_config1],
        )
        result = _serialize_model_service(svc)
        assert result["provider_settings"] == {"api_key": "sk-xxx"}
        assert result["model_info_configs"] == [{"model_name": "qwen-max"}]


class TestLoadJsonOption:
    def test_none_input(self):
        assert _load_json_option(None) is None

    def test_inline_json(self):
        result = _load_json_option('{"key": "val"}')
        assert result == {"key": "val"}

    def test_file_path(self, tmp_path):
        f = tmp_path / "data.json"
        f.write_text('{"from": "file"}')
        result = _load_json_option(str(f))
        assert result == {"from": "file"}
