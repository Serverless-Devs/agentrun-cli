"""Unit tests for agentrun_cli.main — main() entry point."""

import importlib
from unittest.mock import Mock, patch

import agentrun_cli.main as main_module


class TestMainEntryPoint:
    def test_main_function_directly(self):
        """Call main() directly — it delegates to cli()."""
        with patch("agentrun_cli.main.cli") as mock_cli:
            main_module.main()
            mock_cli.assert_called_once()

    def test_default_ssl_cert_file_uses_certifi(self, monkeypatch):
        """Default SSL_CERT_FILE to certifi when the user has not set it."""
        monkeypatch.delenv("SSL_CERT_FILE", raising=False)
        monkeypatch.setattr(main_module.certifi, "where", lambda: "/tmp/cacert.pem")

        importlib.reload(main_module)

        assert main_module.os.environ["SSL_CERT_FILE"] == "/tmp/cacert.pem"

    def test_preserves_user_ssl_cert_file(self, monkeypatch):
        """Do not override an explicit user SSL_CERT_FILE."""
        monkeypatch.setenv("SSL_CERT_FILE", "/custom/ca.pem")
        mock_where = Mock(return_value="/tmp/cacert.pem")
        monkeypatch.setattr(main_module.certifi, "where", mock_where)

        importlib.reload(main_module)

        assert main_module.os.environ["SSL_CERT_FILE"] == "/custom/ca.pem"
        mock_where.assert_not_called()
