"""Integration tests for CLI entry point — debug flag, help output."""

import logging
from unittest.mock import patch

from click.testing import CliRunner

from agentrun_cli.main import cli


class TestDebugFlag:

    def test_debug_enables_logging(self):
        runner = CliRunner()
        with patch("logging.basicConfig") as mock_basic:
            result = runner.invoke(cli, ["--debug", "config", "--help"])
            assert result.exit_code == 0
            mock_basic.assert_called_once_with(level=logging.DEBUG)

    def test_no_debug_by_default(self):
        runner = CliRunner()
        with patch("logging.basicConfig") as mock_basic:
            result = runner.invoke(cli, ["config", "--help"])
            assert result.exit_code == 0
            mock_basic.assert_not_called()
