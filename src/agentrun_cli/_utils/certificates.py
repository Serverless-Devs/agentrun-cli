"""Certificate bundle setup for frozen CLI binaries."""

import os
import sys

import certifi


def configure_default_ca_bundle() -> None:
    """Use the bundled certifi CA file when running as a frozen binary."""
    if not getattr(sys, "frozen", False):
        return
    if os.environ.get("SSL_CERT_FILE"):
        return
    os.environ["SSL_CERT_FILE"] = certifi.where()
