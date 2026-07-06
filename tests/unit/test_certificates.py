"""Unit tests for frozen-binary certificate setup."""

from agentrun_cli._utils import certificates


class TestConfigureDefaultCaBundle:
    def test_uses_certifi_for_frozen_binary(self, monkeypatch):
        monkeypatch.setattr(certificates.sys, "frozen", True, raising=False)
        monkeypatch.delenv("SSL_CERT_FILE", raising=False)
        monkeypatch.setattr(certificates.certifi, "where", lambda: "/tmp/cacert.pem")

        certificates.configure_default_ca_bundle()

        assert certificates.os.environ["SSL_CERT_FILE"] == "/tmp/cacert.pem"

    def test_preserves_user_ssl_cert_file(self, monkeypatch):
        monkeypatch.setattr(certificates.sys, "frozen", True, raising=False)
        monkeypatch.setenv("SSL_CERT_FILE", "/custom/ca.pem")
        monkeypatch.setattr(certificates.certifi, "where", lambda: "/tmp/cacert.pem")

        certificates.configure_default_ca_bundle()

        assert certificates.os.environ["SSL_CERT_FILE"] == "/custom/ca.pem"

    def test_skips_regular_python_runtime(self, monkeypatch):
        monkeypatch.delattr(certificates.sys, "frozen", raising=False)
        monkeypatch.delenv("SSL_CERT_FILE", raising=False)

        certificates.configure_default_ca_bundle()

        assert "SSL_CERT_FILE" not in certificates.os.environ
