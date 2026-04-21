"""Unit tests for sandbox _helpers module."""

import io
from unittest.mock import patch

import click
import pytest

from agentrun_cli.commands.sandbox._helpers import (
    _build_cfg,
    _load_json_option,
    _read_code_input,
    _read_content_input,
)


class TestLoadJsonOption:

    def test_none(self):
        assert _load_json_option(None) is None

    def test_inline_json(self):
        assert _load_json_option('{"a": 1}') == {"a": 1}

    def test_file_path(self, tmp_path):
        f = tmp_path / "data.json"
        f.write_text('{"from": "file"}')
        assert _load_json_option(str(f)) == {"from": "file"}


class TestReadCodeInput:

    def test_code_string(self):
        assert _read_code_input("print(1)", None) == "print(1)"

    def test_code_file(self, tmp_path):
        f = tmp_path / "code.py"
        f.write_text("x = 42")
        assert _read_code_input(None, str(f)) == "x = 42"

    def test_both_raises(self, tmp_path):
        f = tmp_path / "code.py"
        f.write_text("x = 42")
        with pytest.raises(click.UsageError, match="mutually exclusive"):
            _read_code_input("print(1)", str(f))

    def test_stdin(self):
        with patch("sys.stdin", new=io.StringIO("stdin code")):
            with patch("sys.stdin.isatty", return_value=False):
                assert _read_code_input(None, None) == "stdin code"

    def test_no_input_raises(self):
        with patch("sys.stdin.isatty", return_value=True):
            with pytest.raises(click.UsageError, match="--code"):
                _read_code_input(None, None)


class TestReadContentInput:

    def test_content_string(self):
        assert _read_content_input("hello", False) == "hello"

    def test_stdin(self):
        with patch("sys.stdin", new=io.StringIO("from stdin")):
            assert _read_content_input(None, True) == "from stdin"

    def test_both_raises(self):
        with pytest.raises(click.UsageError, match="mutually exclusive"):
            _read_content_input("hello", True)

    def test_no_input_raises(self):
        with pytest.raises(click.UsageError, match="--content"):
            _read_content_input(None, False)


class TestBuildCfg:

    def test_build_cfg(self, tmp_path):
        from unittest.mock import MagicMock

        mock_ctx = MagicMock(spec=click.Context)
        mock_ctx.obj = {"profile": "test", "region": "cn-shanghai"}
        mock_sdk = MagicMock()
        with patch.dict("sys.modules", {
            "agentrun": MagicMock(),
            "agentrun.utils": MagicMock(),
            "agentrun.utils.config": MagicMock(Config=mock_sdk),
        }):
            with patch("agentrun_cli._utils.config.CONFIG_FILE", tmp_path / "config.json"), \
                 patch("agentrun_cli._utils.config.CONFIG_DIR", tmp_path):
                _build_cfg(mock_ctx)
                mock_sdk.assert_called_once()
                assert mock_sdk.call_args.kwargs["region_id"] == "cn-shanghai"
