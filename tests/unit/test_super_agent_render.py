"""Unit tests for SSE stream rendering."""

import json
from types import SimpleNamespace

import pytest

from agentrun_cli._utils.super_agent_render import (
    RenderMode,
    StreamRenderer,
    pick_render_mode,
)


def _ev(event, data, sse_id=None):
    return SimpleNamespace(event=event, data=data, id=sse_id, retry=None)


class TestPickRenderMode:
    def test_tty_no_flags_is_pretty(self):
        m = pick_render_mode(is_tty=True, raw=False, text_only=False)
        assert m == RenderMode.PRETTY

    def test_non_tty_no_flags_is_raw(self):
        m = pick_render_mode(is_tty=False, raw=False, text_only=False)
        assert m == RenderMode.RAW

    def test_raw_flag_forces_raw(self):
        m = pick_render_mode(is_tty=True, raw=True, text_only=False)
        assert m == RenderMode.RAW

    def test_text_only_flag(self):
        m = pick_render_mode(is_tty=False, raw=False, text_only=True)
        assert m == RenderMode.TEXT_ONLY

    def test_raw_and_text_only_conflict(self):
        with pytest.raises(ValueError):
            pick_render_mode(is_tty=True, raw=True, text_only=True)


class TestRawRenderer:
    def test_emits_json_per_event(self, capsys):
        events = [
            _ev("RUN_STARTED", '{"threadId":"t1","runId":"r1"}'),
            _ev("TEXT_MESSAGE_CONTENT", '{"delta":"hello"}'),
            _ev("RUN_FINISHED", "{}"),
        ]
        r = StreamRenderer(RenderMode.RAW)
        for e in events:
            r.feed(e)
        r.finish()
        out = capsys.readouterr().out.strip().splitlines()
        assert len(out) == 3
        first = json.loads(out[0])
        assert first["event"] == "RUN_STARTED"
        assert first["data"] == '{"threadId":"t1","runId":"r1"}'

    def test_skips_empty_data(self, capsys):
        r = StreamRenderer(RenderMode.RAW)
        r.feed(_ev(None, ""))
        r.finish()
        out = capsys.readouterr().out
        assert out == ""


class TestTextOnlyRenderer:
    def test_accumulates_text(self, capsys):
        r = StreamRenderer(RenderMode.TEXT_ONLY)
        r.feed(_ev("TEXT_MESSAGE_START", "{}"))
        r.feed(_ev("TEXT_MESSAGE_CONTENT", '{"delta":"Hello "}'))
        r.feed(_ev("TEXT_MESSAGE_CONTENT", '{"delta":"world"}'))
        r.feed(_ev("TEXT_MESSAGE_END", "{}"))
        r.feed(_ev("RUN_FINISHED", "{}"))
        r.finish()
        out = capsys.readouterr().out
        assert "Hello world" in out

    def test_ignores_tool_calls(self, capsys):
        r = StreamRenderer(RenderMode.TEXT_ONLY)
        r.feed(_ev("TOOL_CALL_START", '{"toolCallId":"tc1","toolCallName":"search"}'))
        r.feed(_ev("TOOL_CALL_ARGS", '{"delta":"{}"}'))
        r.feed(_ev("TOOL_CALL_END", '{"toolCallId":"tc1"}'))
        r.finish()
        out = capsys.readouterr().out
        assert out.strip() == ""


class TestPrettyRenderer:
    def test_renders_text_delta(self, capsys):
        r = StreamRenderer(RenderMode.PRETTY, use_color=False)
        r.feed(_ev("TEXT_MESSAGE_CONTENT", '{"delta":"hi"}'))
        r.finish()
        out = capsys.readouterr().out
        assert "hi" in out

    def test_text_message_end_newline(self, capsys):
        r = StreamRenderer(RenderMode.PRETTY, use_color=False)
        r.feed(_ev("TEXT_MESSAGE_CONTENT", '{"delta":"hi"}'))
        r.feed(_ev("TEXT_MESSAGE_END", "{}"))
        r.finish()
        out = capsys.readouterr().out
        assert out.endswith("\n")

    def test_renders_tool_call_header(self, capsys):
        r = StreamRenderer(RenderMode.PRETTY, use_color=False)
        r.feed(
            _ev("TOOL_CALL_START", '{"toolCallId":"tc1","toolCallName":"web_search"}')
        )
        r.finish()
        out = capsys.readouterr().out
        assert "web_search" in out
        assert "tool" in out.lower()

    def test_renders_tool_result_truncated(self, capsys):
        r = StreamRenderer(RenderMode.PRETTY, use_color=False)
        long_content = "x" * 500
        r.feed(
            _ev(
                "TOOL_CALL_RESULT",
                json.dumps({"toolCallId": "tc1", "content": long_content}),
            )
        )
        r.finish()
        out = capsys.readouterr().out
        assert "..." in out
        assert len(out) < 400

    def test_run_error_shows_message(self, capsys):
        r = StreamRenderer(RenderMode.PRETTY, use_color=False)
        r.feed(_ev("RUN_ERROR", '{"message":"boom"}'))
        r.finish()
        out = capsys.readouterr().out
        assert "boom" in out
        assert "error" in out.lower()

    def test_run_finished_emits_separator(self, capsys):
        r = StreamRenderer(RenderMode.PRETTY, use_color=False)
        r.feed(_ev("TEXT_MESSAGE_CONTENT", '{"delta":"hi"}'))
        r.feed(_ev("RUN_FINISHED", "{}"))
        r.finish()
        out = capsys.readouterr().out
        assert "─" in out

    def test_color_styling(self, capsys):
        r = StreamRenderer(RenderMode.PRETTY, use_color=True)
        r.feed(_ev("TOOL_CALL_START", '{"toolCallName":"x"}'))
        r.finish()
        out = capsys.readouterr().out
        # ANSI codes present when color enabled
        assert "\x1b[" in out


class TestEnvelopeFooter:
    def test_raw_emits_envelope_on_finish(self, capsys):
        r = StreamRenderer(RenderMode.RAW)
        r.set_conversation_id("conv-xxx")
        r.feed(_ev("RUN_FINISHED", "{}"))
        r.finish_with_envelope()
        out = capsys.readouterr().out.strip().splitlines()
        envelope = json.loads(out[-1])
        assert envelope["_meta"] == "envelope"
        assert envelope["conversation_id"] == "conv-xxx"
        assert envelope["status"] == "completed"

    def test_text_only_no_envelope(self, capsys):
        r = StreamRenderer(RenderMode.TEXT_ONLY)
        r.set_conversation_id("conv-xxx")
        r.finish_with_envelope()
        out = capsys.readouterr().out
        assert "_meta" not in out
        assert "envelope" not in out

    def test_pretty_no_envelope(self, capsys):
        r = StreamRenderer(RenderMode.PRETTY, use_color=False)
        r.set_conversation_id("conv-xxx")
        r.finish_with_envelope()
        out = capsys.readouterr().out
        assert "_meta" not in out


class TestSafeJson:
    def test_invalid_json_handled(self, capsys):
        r = StreamRenderer(RenderMode.PRETTY, use_color=False)
        r.feed(_ev("TEXT_MESSAGE_CONTENT", "not-json"))
        r.finish()
        # No crash; no output since delta not extracted
        out = capsys.readouterr().out
        assert "not-json" not in out


class TestFlushAndErrorEdges:
    def _stream_that_raises_on_flush(self):
        class S:
            def __init__(self):
                self.buf = []

            def write(self, s):
                self.buf.append(s)

            def flush(self):
                raise OSError("flush failed")

            def isatty(self):
                return False

        return S()

    def test_finish_swallows_flush_error_pretty(self):
        """`finish()` flush failures are silently swallowed."""
        s = self._stream_that_raises_on_flush()
        r = StreamRenderer(RenderMode.PRETTY, use_color=False, stream=s)
        # Should not raise even though flush() throws.
        r.finish()

    def test_finish_with_envelope_swallows_flush_error_raw(self):
        """RAW envelope finisher: both flushes (finish + envelope) tolerate errors."""
        s = self._stream_that_raises_on_flush()
        r = StreamRenderer(RenderMode.RAW, use_color=False, stream=s)
        r.set_conversation_id("c-1")
        # Should not raise even though both flush() calls throw.
        r.finish_with_envelope()
        joined = "".join(s.buf)
        assert "envelope" in joined

    def test_color_error_path(self, capsys):
        """RUN_ERROR with color enabled hits the styled branch of `_write_error`."""
        r = StreamRenderer(RenderMode.PRETTY, use_color=True)
        r.feed(_ev("RUN_ERROR", '{"message":"boom"}'))
        r.finish()
        out = capsys.readouterr().out
        # ANSI escape present and message visible.
        assert "\x1b[" in out
        assert "boom" in out


class TestEventTypeInData:
    """The real server streams SSE with empty event: field.

    Event type lives inside ``data.type`` instead. Renderer must fall back.
    """

    def test_text_only_uses_data_type(self, capsys):
        r = StreamRenderer(RenderMode.TEXT_ONLY)
        # event field is None (matches server behavior)
        r.feed(_ev(None, '{"type":"TEXT_MESSAGE_CONTENT","delta":"hi"}'))
        r.finish()
        out = capsys.readouterr().out
        assert out == "hi"

    def test_pretty_uses_data_type(self, capsys):
        r = StreamRenderer(RenderMode.PRETTY, use_color=False)
        r.feed(_ev(None, '{"type":"TEXT_MESSAGE_CONTENT","delta":"Hi!"}'))
        r.finish()
        out = capsys.readouterr().out
        assert "Hi!" in out

    def test_pretty_tool_call_start_from_data_type(self, capsys):
        r = StreamRenderer(RenderMode.PRETTY, use_color=False)
        r.feed(_ev(None, '{"type":"TOOL_CALL_START","toolCallName":"search"}'))
        r.finish()
        out = capsys.readouterr().out
        assert "search" in out
