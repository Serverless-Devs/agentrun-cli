"""``ar sa conv`` / ``ar sa conversation`` — manage conversations."""

import click

from agentrun_cli._utils.config import build_sdk_config
from agentrun_cli._utils.error import handle_errors
from agentrun_cli._utils.output import format_output
from agentrun_cli._utils.super_agent_state import clear_conv_if_matches
from agentrun_cli.commands.super_agent._helpers import asyncio_run, ctx_cfg

SuperAgentClient = None


def _get_client_cls():
    global SuperAgentClient
    if SuperAgentClient is None:
        from agentrun.super_agent import SuperAgentClient as _Cls

        SuperAgentClient = _Cls
    return SuperAgentClient


@click.group("conversation", help="Manage super agent conversations.")
def conv_group():
    pass


def _serialize_message(m) -> dict:
    return {
        "role": getattr(m, "role", ""),
        "content": getattr(m, "content", ""),
        "message_id": getattr(m, "message_id", None),
        "created_at": getattr(m, "created_at", None),
    }


def _serialize_conversation_info(info) -> dict:
    return {
        "conversation_id": getattr(info, "conversation_id", ""),
        "agent_id": getattr(info, "agent_id", ""),
        "title": getattr(info, "title", None),
        "main_user_id": getattr(info, "main_user_id", None),
        "sub_user_id": getattr(info, "sub_user_id", None),
        "created_at": getattr(info, "created_at", 0),
        "updated_at": getattr(info, "updated_at", 0),
        "error_message": getattr(info, "error_message", None),
        "invoke_info": getattr(info, "invoke_info", None),
        "messages": [_serialize_message(m) for m in getattr(info, "messages", [])],
        "params": getattr(info, "params", None),
    }


@conv_group.command("get", help="Get a conversation by id.")
@click.argument("name")
@click.argument("conversation_id")
@click.pass_context
@handle_errors
def conv_get_cmd(ctx, name, conversation_id):
    profile, region = ctx_cfg(ctx)
    cfg = build_sdk_config(profile_name=profile, region=region)
    client = _get_client_cls()(config=cfg)
    agent = client.get(name)
    info = asyncio_run(agent.get_conversation_async(conversation_id))
    format_output(ctx, _serialize_conversation_info(info))


@conv_group.command("delete", help="Delete a conversation.")
@click.argument("name")
@click.argument("conversation_id")
@click.pass_context
@handle_errors
def conv_delete_cmd(ctx, name, conversation_id):
    profile, region = ctx_cfg(ctx)
    cfg = build_sdk_config(profile_name=profile, region=region)
    client = _get_client_cls()(config=cfg)
    agent = client.get(name)
    asyncio_run(agent.delete_conversation_async(conversation_id))
    clear_conv_if_matches(name, conversation_id)
    format_output(
        ctx,
        {
            "name": name,
            "conversation_id": conversation_id,
            "deleted": True,
        },
        quiet_field="conversation_id",
    )


@conv_group.command("list", help="List conversations of a super agent.")
@click.argument("name")
@click.pass_context
@handle_errors
def conv_list_cmd(ctx, name):
    """List all conversations belonging to a super agent."""
    profile, region = ctx_cfg(ctx)
    cfg = build_sdk_config(profile_name=profile, region=region)
    client = _get_client_cls()(config=cfg)
    agent = client.get(name)
    list_fn = getattr(agent, "list_conversations_async", None)
    if list_fn is None:
        raise click.ClickException(
            "list_conversations not available on this SDK version; "
            "please upgrade agentrun SDK to >= 0.0.157."
        )
    result = asyncio_run(list_fn())
    # Normalize: result may be a list of ConversationInfo-like or dicts.
    rows = []
    if isinstance(result, list):
        for item in result:
            if isinstance(item, dict):
                rows.append(item)
            else:
                rows.append(_serialize_conversation_info(item))
    format_output(ctx, rows)
