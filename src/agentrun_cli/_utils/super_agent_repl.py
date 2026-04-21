"""REPL (interactive prompt loop) for ``ar sa run`` and ``ar sa chat``.

Responsibilities:
  - Prompt for user input line-by-line
  - Dispatch slash commands (/exit, /new, /conv, /raw, /help)
  - Send messages to agent.invoke_async, stream reply through StreamRenderer
  - Persist last conversation_id to local state file after each turn
"""

from __future__ import annotations

import asyncio
import enum
from dataclasses import dataclass
from typing import Any, Callable, Optional

import click

from agentrun_cli._utils.super_agent_render import (
    RenderMode,
    StreamRenderer,
)


class SlashResult(enum.Enum):
    NOT_SLASH = "not-slash"
    UNKNOWN = "unknown"
    EXIT = "exit"
    NEW_CONV = "new-conv"
    PRINT_CONV = "print-conv"
    TOGGLE_RAW = "toggle-raw"
    HELP = "help"


HELP_TEXT = (
    "Slash commands:\n"
    "  /exit, /quit   exit REPL\n"
    "  /new           start a fresh conversation\n"
    "  /conv          print current conversation_id\n"
    "  /raw           toggle raw SSE output\n"
    "  /help          show this help\n"
)


def handle_slash(line: str) -> SlashResult:
    stripped = line.strip()
    if not stripped.startswith("/"):
        return SlashResult.NOT_SLASH
    cmd = stripped.split()[0]
    mapping = {
        "/exit": SlashResult.EXIT,
        "/quit": SlashResult.EXIT,
        "/new": SlashResult.NEW_CONV,
        "/conv": SlashResult.PRINT_CONV,
        "/raw": SlashResult.TOGGLE_RAW,
        "/help": SlashResult.HELP,
    }
    return mapping.get(cmd, SlashResult.UNKNOWN)


@dataclass
class ReplConfig:
    agent_name: str
    render_mode: RenderMode
    initial_conv_id: Optional[str] = None
    input_fn: Optional[Callable[[str], str]] = None
    initial_message: Optional[str] = None


# Indirection so tests can patch the state-file writer without importing
# super_agent_state at repl-module level.
def _default_state_writer(agent_name: str, conv_id: str) -> None:
    from agentrun_cli._utils.super_agent_state import set_last_conv_id
    set_last_conv_id(agent_name, conv_id)


STATE_FILE_WRITER = _default_state_writer


def run_repl(agent, cfg: ReplConfig) -> Optional[str]:
    """Drive the REPL. Returns the final conversation_id (or None)."""
    state = _ReplState(
        agent=agent,
        cfg=cfg,
        conversation_id=cfg.initial_conv_id,
        render_mode=cfg.render_mode,
    )
    if cfg.initial_message:
        state.pending_user_input = cfg.initial_message

    input_fn = cfg.input_fn or _default_input

    while True:
        if state.pending_user_input is not None:
            line = state.pending_user_input
            state.pending_user_input = None
        else:
            try:
                line = input_fn("> ")
            except (EOFError, KeyboardInterrupt):
                click.echo("")
                break
            if line is None:
                break  # type: ignore[unreachable]

        slash = handle_slash(line)
        if slash == SlashResult.EXIT:
            break
        if slash == SlashResult.NEW_CONV:
            state.conversation_id = None
            click.echo("(new conversation)")
            continue
        if slash == SlashResult.PRINT_CONV:
            click.echo(state.conversation_id or "(none yet)")
            continue
        if slash == SlashResult.TOGGLE_RAW:
            state.render_mode = (
                RenderMode.PRETTY
                if state.render_mode == RenderMode.RAW
                else RenderMode.RAW
            )
            click.echo(f"(render: {state.render_mode.value})")
            continue
        if slash == SlashResult.HELP:
            click.echo(HELP_TEXT)
            continue
        if slash == SlashResult.UNKNOWN:
            click.echo(f"(unknown command: {line}; try /help)")
            continue
        if not line.strip():
            continue

        _run_one_turn(state, user_text=line)

    return state.conversation_id


@dataclass
class _ReplState:
    agent: Any
    cfg: ReplConfig
    conversation_id: Optional[str]
    render_mode: RenderMode
    pending_user_input: Optional[str] = None


def _run_one_turn(state: _ReplState, *, user_text: str) -> None:
    renderer = StreamRenderer(state.render_mode)
    messages = [{"role": "user", "content": user_text}]

    async def drive():
        stream = await state.agent.invoke_async(
            messages=messages, conversation_id=state.conversation_id,
        )
        renderer.set_conversation_id(stream.conversation_id)
        try:
            async for ev in stream:
                renderer.feed(ev)
        finally:
            close = getattr(stream, "aclose", None)
            if close is not None:
                await close()
        return stream.conversation_id

    try:
        new_conv_id = asyncio.run(drive())
    except KeyboardInterrupt:
        click.echo("\n(turn interrupted)")
        return
    renderer.finish()

    if new_conv_id:
        state.conversation_id = new_conv_id
        try:
            STATE_FILE_WRITER(state.cfg.agent_name, new_conv_id)
        except Exception as e:
            click.echo(f"[warn] failed to persist conv_id: {e}", err=True)


def _default_input(prompt: str) -> str:
    return input(prompt)
