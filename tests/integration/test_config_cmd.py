"""Integration tests for config commands — empty profile via CliRunner."""

from unittest.mock import patch

from click.testing import CliRunner

from agentrun_cli.main import cli


class TestConfigListEmpty:

    def test_empty_profile_message(self, tmp_path):
        config_file = tmp_path / "config.json"
        with patch("agentrun_cli._utils.config.CONFIG_FILE", config_file), \
             patch("agentrun_cli._utils.config.CONFIG_DIR", tmp_path):
            runner = CliRunner()
            result = runner.invoke(cli, ["config", "list"])
            assert result.exit_code == 0
            assert "empty" in result.output.lower()
            assert "ar config set" in result.output

    def test_empty_named_profile_message(self, tmp_path):
        config_file = tmp_path / "config.json"
        with patch("agentrun_cli._utils.config.CONFIG_FILE", config_file), \
             patch("agentrun_cli._utils.config.CONFIG_DIR", tmp_path):
            runner = CliRunner()
            result = runner.invoke(cli, ["config", "list", "--profile", "staging"])
            assert result.exit_code == 0
            assert "staging" in result.output
