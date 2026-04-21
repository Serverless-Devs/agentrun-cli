"""Tests for agentrun_cli._utils.error — the handle_errors decorator."""

import sys
from unittest.mock import patch

import click
import pytest

from agentrun_cli._utils.error import (
    EXIT_AUTH_ERROR,
    EXIT_BAD_INPUT,
    EXIT_NOT_FOUND,
    EXIT_SERVER_ERROR,
    handle_errors,
)


def _make_raising_func(exc):
    """Return a decorated function that raises *exc* when called."""

    @handle_errors
    def fn():
        raise exc

    return fn


class TestHandleErrors:
    """Cover all exception branches in the handle_errors decorator."""

    def test_success_passthrough(self):
        @handle_errors
        def fn():
            return "ok"

        assert fn() == "ok"

    def test_click_usage_error_reraises(self):
        with pytest.raises(click.UsageError):
            _make_raising_func(click.UsageError("bad param"))()

    def test_resource_not_exist(self):
        # Simulate SDK exception with matching type name
        exc = type("ResourceNotExistError", (Exception,), {})("resource missing")
        with pytest.raises(SystemExit) as exc_info:
            _make_raising_func(exc)()
        assert exc_info.value.code == EXIT_NOT_FOUND

    def test_not_exist_variant(self):
        exc = type("SomethingNotExistException", (Exception,), {})("not found")
        with pytest.raises(SystemExit) as exc_info:
            _make_raising_func(exc)()
        assert exc_info.value.code == EXIT_NOT_FOUND

    def test_resource_already_exist(self):
        exc = type("ResourceAlreadyExistError", (Exception,), {})("already exists")
        with pytest.raises(SystemExit) as exc_info:
            _make_raising_func(exc)()
        assert exc_info.value.code == EXIT_BAD_INPUT

    def test_already_exist_variant(self):
        exc = type("AlreadyExistException", (Exception,), {})("dup")
        with pytest.raises(SystemExit) as exc_info:
            _make_raising_func(exc)()
        assert exc_info.value.code == EXIT_BAD_INPUT

    def test_forbidden_auth_error(self):
        exc = Exception("Forbidden: access denied")
        with pytest.raises(SystemExit) as exc_info:
            _make_raising_func(exc)()
        assert exc_info.value.code == EXIT_AUTH_ERROR

    def test_invalid_access_key_auth_error(self):
        exc = Exception("InvalidAccessKeyId.NotFound")
        with pytest.raises(SystemExit) as exc_info:
            _make_raising_func(exc)()
        assert exc_info.value.code == EXIT_AUTH_ERROR

    def test_signature_mismatch_auth_error(self):
        exc = Exception("SignatureDoesNotMatch")
        with pytest.raises(SystemExit) as exc_info:
            _make_raising_func(exc)()
        assert exc_info.value.code == EXIT_AUTH_ERROR

    def test_generic_exception(self):
        exc = Exception("something unexpected")
        with pytest.raises(SystemExit) as exc_info:
            _make_raising_func(exc)()
        assert exc_info.value.code == EXIT_SERVER_ERROR
