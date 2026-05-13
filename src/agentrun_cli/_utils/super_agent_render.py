"""SSE stream rendering for super agent invoke/chat/run.

Three modes:
  - RAW: each SSE event as a JSON line (for piping/script use)
  - PRETTY: human-friendly rendering of AG-UI events (text + collapsed tool calls)
  - TEXT_ONLY: only TEXT_MESSAGE_CONTENT.delta accumulated to stdout

Use ``pick_render_mode`` to auto-detect based on TTY + flag combos.
"""

from __future__ import annotations

import enum
import json
import sys

import click


class RenderMode(str, enum.Enum):
    PRETTY = "pretty"
    RAW = "raw"
    TEXT_ONLY = "text-only"


def pick_render_mode(*, is_tty: bool, raw: bool, text_only: bool) -> RenderMode:
    """Resolve render mode from TTY + user flags.

    Raises ValueError if --raw and --text-only are both set.
    """
    if raw and text_only:
        raise ValueError("--raw and --text-only are mutually exclusive")
    if raw:
        return RenderMode.RAW
    if text_only:
        return RenderMode.TEXT_ONLY
    return RenderMode.PRETTY if is_tty else RenderMode.RAW


_TOOL_RESULT_PREVIEW_LIMIT = 200


def _event_name(event, payload: dict) -> str | None:
    """Resolve the AG-UI event type.

    The real server streams SSE with an empty ``event:`` field and puts the
    type inside ``data.type``. Earlier versions used the SSE ``event:`` field
    directly. Support both so the renderer doesn't break on either wire
    layout.
    """
    name = getattr(event, "event", None)
    if name:
        return name
    t = payload.get("type") if isinstance(payload, dict) else None
    return t if isinstance(t, str) else None


class StreamRenderer:
    """Consume SSEEvents and render them according to mode."""

    def __init__(
        self,
        mode: RenderMode,
        *,
        use_color: bool | None = None,
        stream=None,
    ):
        self.mode = mode
        self._conversation_id: str | None = None
        self._out = stream if stream is not None else sys.stdout
        if use_color is None:
            use_color = self._out.isatty() if hasattr(self._out, "isatty") else False
        self._use_color = use_color

    def set_conversation_id(self, conv_id: str) -> None:
        self._conversation_id = conv_id

    def feed(self, event) -> None:
        """Consume one SSEEvent."""
        if self.mode == RenderMode.RAW:
            self._render_raw(event)
        elif self.mode == RenderMode.TEXT_ONLY:
            self._render_text_only(event)
        else:
            self._render_pretty(event)

    def finish(self) -> None:
        """Called at stream end. Flushes anything buffered."""
        try:
            self._out.flush()
        except Exception:  # noqa: S110 — broken-pipe on flush is harmless
            pass

    def finish_with_envelope(self) -> None:
        """RAW mode finisher: emit the envelope JSON line."""
        self.finish()
        if self.mode == RenderMode.RAW:
            envelope = {
                "_meta": "envelope",
                "conversation_id": self._conversation_id or "",
                "status": "completed",
            }
            self._out.write(json.dumps(envelope, ensure_ascii=False) + "\n")
            try:
                self._out.flush()
            except Exception:  # noqa: S110 — broken-pipe on flush is harmless
                pass

    # ───────────────────────────────────────── internal renderers

    def _render_raw(self, event) -> None:
        data = getattr(event, "data", "")
        name = getattr(event, "event", None)
        if not data and not name:
            return
        line = json.dumps(
            {
                "event": name,
                "data": data,
                "id": getattr(event, "id", None),
                "retry": getattr(event, "retry", None),
            },
            ensure_ascii=False,
        )
        self._out.write(line + "\n")

    def _render_text_only(self, event) -> None:
        payload = _safe_json(getattr(event, "data", ""))
        if _event_name(event, payload) == "TEXT_MESSAGE_CONTENT":
            delta = payload.get("delta", "") if payload else ""
            if delta:
                self._out.write(delta)

    def _render_pretty(self, event) -> None:
        payload = _safe_json(getattr(event, "data", "") or "")
        name = _event_name(event, payload)

        if name == "TEXT_MESSAGE_CONTENT":
            delta = payload.get("delta", "") if payload else ""
            if delta:
                self._out.write(delta)
        elif name == "TEXT_MESSAGE_END":
            self._out.write("\n")
        elif name == "TOOL_CALL_START":
            tool_name = (
                payload.get("toolCallName")
                or payload.get("tool_call_name")
                or "unknown"
            )
            self._write_meta(f"▸ tool: {tool_name}\n")
        elif name == "TOOL_CALL_RESULT":
            content = payload.get("content", "") if payload else ""
            if len(content) > _TOOL_RESULT_PREVIEW_LIMIT:
                content = content[:_TOOL_RESULT_PREVIEW_LIMIT] + "..."
            self._write_meta(f"▸ tool result: {content}\n")
        elif name == "RUN_ERROR":
            msg = payload.get("message", "") if payload else ""
            self._write_error(f"✖ run error: {msg}\n")
        elif name == "RUN_FINISHED":
            self._out.write("─────────────────────────────────────────────\n")

    def _write_meta(self, text: str) -> None:
        if self._use_color:
            self._out.write(click.style(text, fg="bright_black"))
        else:
            self._out.write(text)

    def _write_error(self, text: str) -> None:
        if self._use_color:
            self._out.write(click.style(text, fg="red"))
        else:
            self._out.write(text)


def _safe_json(s: str) -> dict:
    try:
        obj = json.loads(s) if s else {}
        return obj if isinstance(obj, dict) else {}
    except (TypeError, ValueError):
        return {}
