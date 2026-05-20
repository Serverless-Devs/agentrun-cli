"""Constants for the ``ar runtime`` command group.

Centralises CLI-side defaults so commands and tests share a single source.
"""

SYSTEM_TAG_CLI = "x-agentrun-cli"
"""Auto-injected into ``system_tags`` for every Runtime/Endpoint create or update
issued by this CLI. SDK 0.0.200 removed the user-facing ``tags`` field; the
``system_tags`` slot is the only place such markers can live."""

ARTIFACT_TYPE_CONTAINER = "Container"
"""Forced ``artifact_type`` value — this CLI only supports Container mode."""

DEFAULT_ENDPOINT_NAME = "default"
DEFAULT_TARGET_VERSION = "LATEST"

# Resource defaults — the backend rejects CreateAgentRuntime with HTTP 400
# "CPU is required; Memory is required; Port is required" when these are null.
# Injecting them in the render layer keeps the minimal YAML example runnable.
DEFAULT_CPU = 2.0  # cores
DEFAULT_MEMORY_MB = 4096
DEFAULT_PORT = 9000

POLL_INITIAL_INTERVAL = 3.0  # seconds
POLL_MAX_INTERVAL = 10.0  # seconds (cap of exponential backoff)
POLL_BACKOFF_FACTOR = 1.5
ENDPOINT_POLL_CONCURRENCY = 4  # parallel endpoint pollers

DEFAULT_APPLY_TIMEOUT_SECONDS = 600  # 10 min
DEFAULT_DELETE_TIMEOUT_SECONDS = 300  # 5 min

ENV_POLL_CONCURRENCY = "AGENTRUN_CLI_ENDPOINT_POLL_CONCURRENCY"
"""Env override for ``ENDPOINT_POLL_CONCURRENCY`` (clamped 1..16)."""
