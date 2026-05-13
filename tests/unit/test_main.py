"""Unit tests for agentrun_cli.main — main() entry point."""

from unittest.mock import patch

from agentrun_cli.main import main


class TestMainEntryPoint:
    def test_main_function_directly(self):
        """Call main() directly — it delegates to cli()."""
        with patch("agentrun_cli.main.cli") as mock_cli:
            main()
            mock_cli.assert_called_once()
