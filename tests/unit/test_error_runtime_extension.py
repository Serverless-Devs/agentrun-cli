"""Coverage for the runtime-specific exit codes added to _utils/error.py."""

import pytest

from agentrun_cli._utils.error import (
    EXIT_RESOURCE_FAILED,
    EXIT_TIMEOUT,
    RuntimePollFailed,
    RuntimePollTimeout,
    handle_errors,
)


def test_new_exit_code_constants():
    assert EXIT_RESOURCE_FAILED == 5
    assert EXIT_TIMEOUT == 6


def test_handle_errors_maps_poll_failed_to_5():
    @handle_errors
    def _cmd():
        raise RuntimePollFailed(
            resource_kind="AgentRuntime",
            name="my-agent",
            status="CREATE_FAILED",
            reason="image pull backoff",
        )

    with pytest.raises(SystemExit) as exc:
        _cmd()
    assert exc.value.code == 5


def test_handle_errors_maps_poll_timeout_to_6():
    @handle_errors
    def _cmd():
        raise RuntimePollTimeout(
            resource_kind="AgentRuntime",
            name="my-agent",
            elapsed=600.0,
        )

    with pytest.raises(SystemExit) as exc:
        _cmd()
    assert exc.value.code == 6


def test_existing_exit_codes_unchanged():
    from agentrun_cli._utils.error import (
        EXIT_AUTH_ERROR,
        EXIT_BAD_INPUT,
        EXIT_NOT_FOUND,
        EXIT_SERVER_ERROR,
        EXIT_SUCCESS,
    )

    assert (
        EXIT_SUCCESS,
        EXIT_NOT_FOUND,
        EXIT_BAD_INPUT,
        EXIT_AUTH_ERROR,
        EXIT_SERVER_ERROR,
    ) == (0, 1, 2, 3, 4)
