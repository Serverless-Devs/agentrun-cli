"""PyInstaller runtime hook for bundled CA certificates."""

from agentrun_cli._utils.certificates import configure_default_ca_bundle

configure_default_ca_bundle()
