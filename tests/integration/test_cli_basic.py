"""Basic smoke tests for the CLI entry point and config commands."""

import json
import os
import tempfile
from unittest.mock import patch

from click.testing import CliRunner

from agentrun_cli.main import cli


class TestCLIEntryPoint:
    """Verify the top-level CLI group loads and responds."""

    def test_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "AgentRun CLI" in result.output

    def test_version(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "agentrun-cli" in result.output

    def test_model_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["model", "--help"])
        assert result.exit_code == 0
        assert "create" in result.output
        assert "list" in result.output
        assert "get" in result.output

    def test_config_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "--help"])
        assert result.exit_code == 0
        assert "set" in result.output
        assert "get" in result.output
        assert "list" in result.output


class TestConfigCommands:
    """Test config set / get / list with a temporary config file."""

    def test_set_and_get(self, tmp_path):
        config_file = tmp_path / "config.json"
        with patch("agentrun_cli._utils.config.CONFIG_FILE", config_file), \
             patch("agentrun_cli._utils.config.CONFIG_DIR", tmp_path):
            runner = CliRunner()

            result = runner.invoke(cli, ["config", "set", "region", "cn-shanghai"])
            assert result.exit_code == 0

            result = runner.invoke(cli, ["config", "get", "region"])
            assert result.exit_code == 0
            assert "cn-shanghai" in result.output

    def test_list_masks_secrets(self, tmp_path):
        config_file = tmp_path / "config.json"
        with patch("agentrun_cli._utils.config.CONFIG_FILE", config_file), \
             patch("agentrun_cli._utils.config.CONFIG_DIR", tmp_path):
            runner = CliRunner()

            runner.invoke(cli, ["config", "set", "access_key_id", "LTAI5tABC"])
            runner.invoke(cli, ["config", "set", "access_key_secret", "MySecretKeyValue123"])

            result = runner.invoke(cli, ["config", "list"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            # Secret should be masked
            assert "***" in data["access_key_secret"]
            # Key ID should be in plain text
            assert data["access_key_id"] == "LTAI5tABC"

    def test_get_missing_key(self, tmp_path):
        config_file = tmp_path / "config.json"
        with patch("agentrun_cli._utils.config.CONFIG_FILE", config_file), \
             patch("agentrun_cli._utils.config.CONFIG_DIR", tmp_path):
            runner = CliRunner()
            result = runner.invoke(cli, ["config", "get", "nonexistent"])
            assert result.exit_code != 0
