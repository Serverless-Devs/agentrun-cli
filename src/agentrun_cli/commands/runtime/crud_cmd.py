"""``ar runtime get`` and ``ar runtime list``."""

import click

from agentrun_cli._utils.config import build_sdk_config
from agentrun_cli._utils.error import EXIT_NOT_FOUND, handle_errors
from agentrun_cli._utils.output import echo_error, format_output
from agentrun_cli._utils.runtime_constants import SYSTEM_TAG_CLI
from agentrun_cli._utils.runtime_reconciler import find_runtime_by_name
from agentrun_cli.commands.runtime._helpers import ctx_cfg, serialize_runtime

# Monkey-patch entry points used by integration tests:
AgentRuntime = None


def _lazy_sdk():
    global AgentRuntime
    if AgentRuntime is None:
        from agentrun.agent_runtime import AgentRuntime as _AR
        AgentRuntime = _AR
    return AgentRuntime


@click.command("get", help="Show a single Agent Runtime by name.")
@click.argument("name")
@click.pass_context
@handle_errors
def get_cmd(ctx, name):
    rt_cls = _lazy_sdk()
    profile, region = ctx_cfg(ctx)
    build_sdk_config(profile_name=profile, region=region)
    runtime = find_runtime_by_name(rt_cls, name)
    if runtime is None:
        echo_error("ResourceNotFound",
                   f"AgentRuntime {name!r} not found.")
        raise SystemExit(EXIT_NOT_FOUND)
    format_output(ctx, serialize_runtime(runtime), quiet_field="name")


@click.command("list", help="List Agent Runtimes.")
@click.option(
    "--created-by-cli", is_flag=True, default=False,
    help=f"Only show runtimes tagged with {SYSTEM_TAG_CLI!r}.",
)
@click.option(
    "--workspace", default=None,
    help="Restrict the listing to a workspace (by name).",
)
@click.pass_context
@handle_errors
def list_cmd(ctx, created_by_cli, workspace):
    rt_cls = _lazy_sdk()
    profile, region = ctx_cfg(ctx)
    build_sdk_config(profile_name=profile, region=region)
    items = list(rt_cls.list_all())
    if workspace is not None:
        items = [r for r in items if
                 getattr(r, "workspace_name", None) == workspace]
    if created_by_cli:
        items = [r for r in items if SYSTEM_TAG_CLI in
                 (getattr(r, "system_tags", None) or [])]
    format_output(ctx, [serialize_runtime(r) for r in items])
