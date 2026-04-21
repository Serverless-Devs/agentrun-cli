"""``ar sa chat`` — interactive REPL against an existing super agent."""

import sys

import click

from agentrun_cli._utils.config import build_sdk_config
from agentrun_cli._utils.error import handle_errors
from agentrun_cli._utils.super_agent_render import pick_render_mode
from agentrun_cli._utils.super_agent_repl import ReplConfig, run_repl
from agentrun_cli._utils.super_agent_state import get_last_conv_id
from agentrun_cli.commands.super_agent._helpers import ctx_cfg

SuperAgentClient = None


def _get_client_cls():
    global SuperAgentClient
    if SuperAgentClient is None:
        from agentrun.super_agent import SuperAgentClient as _Cls
        SuperAgentClient = _Cls
    return SuperAgentClient


@click.command(
    "chat",
    help="Enter interactive REPL with an existing super agent.",
)
@click.argument("name")
@click.option("--conversation", "-c", "conversation_id", default=None,
              help="Resume a specific conversation id.")
@click.option("--new", "force_new", is_flag=True, default=False,
              help="Start a fresh conversation (ignore local state).")
@click.option("--message", "-m", "initial_message", default=None,
              help="Send an initial message right after entering the REPL.")
@click.option("--raw", is_flag=True, default=False)
@click.option("--text-only", is_flag=True, default=False)
@click.pass_context
@handle_errors
def chat_cmd(ctx, name, conversation_id, force_new, initial_message,
             raw, text_only):
    """Chat with an existing super agent."""
    try:
        mode = pick_render_mode(
            is_tty=sys.stdout.isatty(), raw=raw, text_only=text_only
        )
    except ValueError as e:
        raise click.UsageError(str(e))

    profile, region = ctx_cfg(ctx)
    cfg = build_sdk_config(profile_name=profile, region=region)
    client = _get_client_cls()(config=cfg)
    agent = client.get(name)

    if force_new:
        conv = None
    elif conversation_id:
        conv = conversation_id
    else:
        conv = get_last_conv_id(name)

    repl_cfg = ReplConfig(
        agent_name=name,
        render_mode=mode,
        initial_conv_id=conv,
        initial_message=initial_message,
    )
    final = run_repl(agent, repl_cfg)

    click.echo(
        f"\n─────────────────────────────────────────────\n"
        f"Agent: {name}\n"
        f"Last conversation: {final or '(none)'}\n"
        f"Resume: ar sa chat {name}\n"
        f"─────────────────────────────────────────────"
    )
