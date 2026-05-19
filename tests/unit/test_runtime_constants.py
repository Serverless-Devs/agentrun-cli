"""Constants for the `ar runtime` command group."""

from agentrun_cli._utils import runtime_constants as C


def test_system_tag_cli():
    assert C.SYSTEM_TAG_CLI == "x-agentrun-cli"


def test_default_endpoint_and_version():
    assert C.DEFAULT_ENDPOINT_NAME == "default"
    assert C.DEFAULT_TARGET_VERSION == "LATEST"


def test_poll_defaults():
    assert C.POLL_INITIAL_INTERVAL == 3.0
    assert C.POLL_MAX_INTERVAL == 10.0
    assert C.POLL_BACKOFF_FACTOR == 1.5
    assert C.ENDPOINT_POLL_CONCURRENCY == 4


def test_timeout_defaults():
    assert C.DEFAULT_APPLY_TIMEOUT_SECONDS == 600
    assert C.DEFAULT_DELETE_TIMEOUT_SECONDS == 300


def test_env_concurrency_override_key():
    assert C.ENV_POLL_CONCURRENCY == "AGENTRUN_CLI_ENDPOINT_POLL_CONCURRENCY"


def test_artifact_type_container():
    assert C.ARTIFACT_TYPE_CONTAINER == "Container"
