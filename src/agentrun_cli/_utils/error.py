"""Centralised error handling for CLI commands.

Provides the ``@handle_errors`` decorator that catches SDK exceptions and
translates them into structured JSON error output on stderr with deterministic
exit codes.

Exit-code convention:
    0 — success
    1 — resource not found
    2 — bad input / resource already exists
    3 — authentication failure
    4 — server / unexpected error
    5 — runtime/endpoint reached a terminal *_FAILED status
    6 — polling timed out waiting for a terminal status
"""

import functools
import sys
from collections.abc import Callable

import click

from agentrun_cli._utils.output import echo_error

EXIT_SUCCESS = 0
EXIT_NOT_FOUND = 1
EXIT_BAD_INPUT = 2
EXIT_AUTH_ERROR = 3
EXIT_SERVER_ERROR = 4
EXIT_RESOURCE_FAILED = 5
EXIT_TIMEOUT = 6

PREREQUISITES_HINT = (
    "Complete the one-time setup at "
    "https://github.com/Serverless-Devs/agentrun-cli#prerequisites — "
    "authorize the AliyunAgentRunSuperAgentRole and grant "
    "AliyunAgentRunFullAccess to your AccessKey."
)

_AUTH_PATTERNS = (
    "Forbidden",
    "InvalidAccessKey",
    "SignatureDoesNotMatch",
    "AccessDenied",
    "NoPermission",
    "AliyunAgentRunSuperAgentRole",
    "EntityNotExist.Role",
)


class RuntimePollFailed(Exception):
    """Raised when a runtime/endpoint reaches a *_FAILED terminal status."""

    def __init__(
        self,
        resource_kind: str,
        name: str,
        status: str,
        reason: str | None = None,
    ):
        self.resource_kind = resource_kind
        self.name = name
        self.status = status
        self.reason = reason
        super().__init__(
            f"{resource_kind} {name!r} entered {status}: {reason or '(no reason)'}"
        )


class RuntimePollTimeout(Exception):
    """Raised when polling exceeds the configured timeout."""

    def __init__(self, resource_kind: str, name: str, elapsed: float):
        self.resource_kind = resource_kind
        self.name = name
        self.elapsed = elapsed
        super().__init__(
            f"Timed out after {elapsed:.1f}s waiting for {resource_kind} {name!r}"
        )


def handle_errors(func: Callable) -> Callable:
    """Decorator that catches common SDK / HTTP errors and exits cleanly."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)

        except click.UsageError:
            # Let click handle its own parameter-validation errors.
            raise

        except Exception as exc:
            exc_type = type(exc).__name__
            msg = str(exc)

            # Detect well-known SDK exception types by name so we don't
            # need a hard import (the SDK may or may not be installed).
            if "ResourceNotExistError" in exc_type or "NotExist" in exc_type:
                echo_error("ResourceNotFound", msg)
                sys.exit(EXIT_NOT_FOUND)
            if "ResourceAlreadyExistError" in exc_type or "AlreadyExist" in exc_type:
                echo_error("ResourceAlreadyExists", msg)
                sys.exit(EXIT_BAD_INPUT)
            if any(pattern in msg for pattern in _AUTH_PATTERNS):
                echo_error("AuthenticationFailed", msg, hint=PREREQUISITES_HINT)
                sys.exit(EXIT_AUTH_ERROR)
            if isinstance(exc, RuntimePollFailed):
                echo_error(
                    "RuntimePollFailed",
                    str(exc),
                    hint=None,
                )
                sys.exit(EXIT_RESOURCE_FAILED)
            if isinstance(exc, RuntimePollTimeout):
                echo_error("RuntimePollTimeout", str(exc))
                sys.exit(EXIT_TIMEOUT)

            # Generic fallback
            echo_error("Error", msg)
            sys.exit(EXIT_SERVER_ERROR)

    return wrapper
