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
"""

import functools
import sys
from typing import Callable

import click

from agentrun_cli._utils.output import echo_error


EXIT_SUCCESS = 0
EXIT_NOT_FOUND = 1
EXIT_BAD_INPUT = 2
EXIT_AUTH_ERROR = 3
EXIT_SERVER_ERROR = 4

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

            # Generic fallback
            echo_error("Error", msg)
            sys.exit(EXIT_SERVER_ERROR)

    return wrapper
