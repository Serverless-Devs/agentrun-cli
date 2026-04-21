"""``ar sa run`` — one-command quickstart: create + enter REPL."""

import sys
from datetime import datetime

import click

from agentrun_cli._utils.config import build_sdk_config
from agentrun_cli._utils.error import handle_errors
from agentrun_cli._utils.super_agent_picker import (
    PickerInputError,
    resolve_model,
)
from agentrun_cli._utils.super_agent_render import pick_render_mode
from agentrun_cli._utils.super_agent_repl import ReplConfig, run_repl
from agentrun_cli.commands.super_agent._helpers import ctx_cfg

SuperAgentClient = None


def _get_client_cls():
    global SuperAgentClient
    if SuperAgentClient is None:
        from agentrun.super_agent import SuperAgentClient as _Cls
        SuperAgentClient = _Cls
    return SuperAgentClient


def _auto_name() -> str:
    return f"super-agent-tmp-{datetime.now().strftime('%Y%m%d%H%M%S')}"


@click.command(
    "run",
    help="Quickstart: create a super agent and chat in one command.",
)
@click.option("--name", default=None,
              help="Agent name (default: auto-generated super-agent-tmp-<ts>).")
@click.option("--prompt", "-p", default="You are a helpful assistant.",
              help="System prompt.")
@click.option("--model-service", default=None,
              help="ModelService name (TTY prompts interactively if omitted).")
@click.option("--model", default=None,
              help="Model name (TTY prompts interactively if omitted).")
@click.option("--tool", "tools", multiple=True)
@click.option("--skill", "skills", multiple=True)
@click.option("--sandbox", "sandboxes", multiple=True)
@click.option("--workspace", "workspaces", multiple=True)
@click.option("--sub-agent", "sub_agents", multiple=True)
@click.option("--message", "-m", "initial_message", default=None)
@click.option("--raw", is_flag=True, default=False)
@click.option("--text-only", is_flag=True, default=False)
@click.option("--no-input", is_flag=True, default=False,
              help="Skip interactive prompts; required args must be given.")
@click.pass_context
@handle_errors
def run_cmd(ctx, name, prompt, model_service, model,
            tools, skills, sandboxes, workspaces, sub_agents,
            initial_message, raw, text_only, no_input):
    """Create a super agent (auto-named if --name omitted) and enter REPL."""
    profile, region = ctx_cfg(ctx)
    cfg = build_sdk_config(profile_name=profile, region=region)

    is_tty = (
        sys.stdin.isatty() and sys.stdout.isatty() and not no_input
    )
    try:
        resolved_svc, resolved_model = resolve_model(
            cli_service=model_service, cli_model=model,
            is_tty=is_tty, cfg=cfg,
        )
    except PickerInputError as e:
        raise click.UsageError(str(e))

    resolved_name = name or _auto_name()

    client = _get_client_cls()(config=cfg)

    click.echo(f"Creating super agent: {resolved_name} ...")
    agent = client.create(
        name=resolved_name,
        prompt=prompt,
        model_service_name=resolved_svc,
        model_name=resolved_model,
        tools=list(tools),
        skills=list(skills),
        sandboxes=list(sandboxes),
        workspaces=list(workspaces),
        agents=list(sub_agents),
    )
    click.echo("Ready. Type your message (/help for commands).\n")

    try:
        mode = pick_render_mode(
            is_tty=sys.stdout.isatty(), raw=raw, text_only=text_only,
        )
    except ValueError as e:
        raise click.UsageError(str(e))

    repl_cfg = ReplConfig(
        agent_name=resolved_name,
        render_mode=mode,
        initial_conv_id=None,
        initial_message=initial_message,
    )
    final = run_repl(agent, repl_cfg)

    click.echo(
        f"\n─────────────────────────────────────────────\n"
        f"Super agent created: {resolved_name}\n"
        f"Last conversation: {final or '(none)'}\n"
        f"Resume: ar sa chat {resolved_name}\n"
        f"Delete: ar sa delete {resolved_name}\n"
        f"─────────────────────────────────────────────"
    )
