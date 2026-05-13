"""``ar sa invoke`` — single-shot non-interactive call to a super agent."""

import json
import sys

import click

from agentrun_cli._utils.config import build_sdk_config
from agentrun_cli._utils.error import handle_errors
from agentrun_cli._utils.super_agent_render import (
    RenderMode,
    StreamRenderer,
    pick_render_mode,
)
from agentrun_cli._utils.super_agent_state import set_last_conv_id
from agentrun_cli.commands.super_agent._helpers import asyncio_run, ctx_cfg

# Lazy-loaded; tests may patch these symbols
SuperAgentClient = None


def _get_client_cls():
    global SuperAgentClient
    if SuperAgentClient is None:
        from agentrun.super_agent import SuperAgentClient as _Cls

        SuperAgentClient = _Cls
    return SuperAgentClient


def _parse_messages(message: str | None, messages_json: str | None) -> list[dict]:
    if message and messages_json:
        raise click.UsageError("Use either --message/-m OR --messages, not both")
    if not message and not messages_json:
        raise click.UsageError("One of --message/-m or --messages is required")
    if message:
        return [{"role": "user", "content": message}]
    # At this point messages_json is guaranteed non-None by the guard above.
    try:
        parsed = json.loads(messages_json)
    except (TypeError, ValueError) as e:
        raise click.UsageError(f"--messages is not valid JSON: {e}") from e
    if not isinstance(parsed, list):
        raise click.UsageError("--messages must be a JSON array")
    return parsed


@click.command("invoke", help="Invoke a super agent (single call).")
@click.argument("name")
@click.option(
    "--message",
    "-m",
    default=None,
    help="User message (creates a single user-role message).",
)
@click.option(
    "--messages",
    "messages_json",
    default=None,
    help="Full messages JSON array (mutually exclusive with -m).",
)
@click.option(
    "--conversation",
    "-c",
    "conversation_id",
    default=None,
    help="Continue an existing conversation by id.",
)
@click.option(
    "--save-conv",
    is_flag=True,
    default=False,
    help="Save the returned conversation_id to local state "
    "for future 'ar sa chat' resume.",
)
@click.option(
    "--raw", is_flag=True, default=False, help="Force raw SSE JSON-line output."
)
@click.option(
    "--text-only",
    is_flag=True,
    default=False,
    help="Only emit assistant text (no envelope, no tool calls).",
)
@click.option(
    "--timeout",
    type=int,
    default=300,
    help="Overall timeout in seconds (default: 300).",
)
@click.pass_context
@handle_errors
def invoke_cmd(
    ctx,
    name,
    message,
    messages_json,
    conversation_id,
    save_conv,
    raw,
    text_only,
    timeout,
):
    """Invoke a super agent once and stream the response."""
    messages = _parse_messages(message, messages_json)
    try:
        mode = pick_render_mode(
            is_tty=sys.stdout.isatty(), raw=raw, text_only=text_only
        )
    except ValueError as e:
        raise click.UsageError(str(e)) from e

    profile, region = ctx_cfg(ctx)
    cfg = build_sdk_config(profile_name=profile, region=region)
    client = _get_client_cls()(config=cfg)
    agent = client.get(name)

    renderer = StreamRenderer(mode)

    async def _drive():
        stream = await agent.invoke_async(
            messages=messages, conversation_id=conversation_id
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

    final_conv_id = asyncio_run(_drive())

    if mode == RenderMode.RAW:
        renderer.finish_with_envelope()
    else:
        renderer.finish()

    if save_conv and final_conv_id:
        set_last_conv_id(name, final_conv_id)
