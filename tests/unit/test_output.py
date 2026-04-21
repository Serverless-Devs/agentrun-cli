"""Tests for agentrun_cli._utils.output — all output formatters."""

import json
from unittest.mock import MagicMock, patch

import click
from click.testing import CliRunner

from agentrun_cli._utils.output import (
    echo_error,
    echo_json,
    echo_quiet,
    echo_table,
    format_output,
)


class TestEchoTable:
    """Cover echo_table: rich available, rich missing, and empty rows."""

    def test_renders_with_rich(self, capsys):
        """When rich is installed, a table is printed (not JSON)."""
        rows = [{"name": "a", "value": "1"}, {"name": "b", "value": "2"}]
        echo_table(rows)
        out = capsys.readouterr().out
        # Rich tables contain the column names
        assert "name" in out
        assert "value" in out

    def test_renders_with_custom_columns(self, capsys):
        rows = [{"name": "a", "value": "1", "extra": "x"}]
        echo_table(rows, columns=["name", "value"])
        out = capsys.readouterr().out
        assert "name" in out
        assert "value" in out

    def test_fallback_without_rich(self, capsys):
        """When rich is not importable, fall back to JSON."""
        rows = [{"name": "hello"}]
        with patch.dict("sys.modules", {"rich.console": None, "rich.table": None}):
            # Force ImportError by patching builtins.__import__
            original_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__

            def mock_import(name, *args, **kwargs):
                if name in ("rich.console", "rich.table"):
                    raise ImportError("no rich")
                return original_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=mock_import):
                echo_table(rows)
        out = capsys.readouterr().out
        assert "hello" in out

    def test_empty_rows(self, capsys):
        echo_table([])
        out = capsys.readouterr().out
        assert "no results" in out


class TestEchoQuiet:
    """Cover echo_quiet: string, dict with field, dict with _name/_id, dict fallback, other."""

    def test_string_data(self, capsys):
        echo_quiet("hello")
        assert capsys.readouterr().out.strip() == "hello"

    def test_dict_with_explicit_field(self, capsys):
        echo_quiet({"id": "123", "name": "foo"}, field="name")
        assert capsys.readouterr().out.strip() == "foo"

    def test_dict_name_id_heuristic(self, capsys):
        echo_quiet({"service_name": "svc1", "status": "ok"})
        assert capsys.readouterr().out.strip() == "svc1"

    def test_dict_id_heuristic(self, capsys):
        echo_quiet({"resource_id": "r-123", "status": "ok"})
        assert capsys.readouterr().out.strip() == "r-123"

    def test_dict_fallback_json(self, capsys):
        echo_quiet({"status": "ok"})
        out = capsys.readouterr().out.strip()
        assert json.loads(out) == {"status": "ok"}

    def test_other_type(self, capsys):
        echo_quiet(42)
        assert capsys.readouterr().out.strip() == "42"


class TestFormatOutput:
    """Cover format_output: json, table, yaml, quiet, and defaults."""

    def _make_ctx(self, fmt="json"):
        ctx = MagicMock(spec=click.Context)
        ctx.obj = {"output": fmt}
        return ctx

    def test_json_format(self, capsys):
        format_output(self._make_ctx("json"), {"key": "val"})
        out = capsys.readouterr().out
        assert json.loads(out) == {"key": "val"}

    def test_table_format_list(self, capsys):
        format_output(self._make_ctx("table"), [{"a": "1"}])
        out = capsys.readouterr().out
        assert "a" in out

    def test_table_format_dict(self, capsys):
        format_output(self._make_ctx("table"), {"a": "1"})
        out = capsys.readouterr().out
        assert "a" in out

    def test_table_format_scalar(self, capsys):
        format_output(self._make_ctx("table"), "hello")
        out = capsys.readouterr().out
        assert "hello" in out

    def test_yaml_format(self, capsys):
        format_output(self._make_ctx("yaml"), {"key": "val"})
        out = capsys.readouterr().out
        assert "key:" in out
        assert "val" in out

    def test_yaml_fallback_without_pyyaml(self, capsys):
        """When PyYAML is not installed, fall back to JSON."""
        original_import = __import__

        def mock_import(name, *args, **kwargs):
            if name == "yaml":
                raise ImportError("no yaml")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            format_output(self._make_ctx("yaml"), {"key": "val"})
        out = capsys.readouterr().out
        assert json.loads(out) == {"key": "val"}

    def test_quiet_format(self, capsys):
        format_output(self._make_ctx("quiet"), {"service_name": "svc"}, quiet_field="service_name")
        assert capsys.readouterr().out.strip() == "svc"

    def test_none_ctx_obj(self, capsys):
        ctx = MagicMock(spec=click.Context)
        ctx.obj = None
        format_output(ctx, {"key": "val"})
        out = capsys.readouterr().out
        assert json.loads(out) == {"key": "val"}


class TestEchoError:
    """Cover echo_error."""

    def test_writes_to_stderr(self, capsys):
        echo_error("TestError", "something went wrong")
        err = capsys.readouterr().err
        parsed = json.loads(err)
        assert parsed["error"] == "TestError"
        assert parsed["message"] == "something went wrong"
