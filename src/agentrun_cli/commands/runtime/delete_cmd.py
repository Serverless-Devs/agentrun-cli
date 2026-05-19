"""``ar runtime delete``."""

from __future__ import annotations

import sys

import click

from agentrun_cli._utils.config import build_sdk_config
from agentrun_cli._utils.error import EXIT_NOT_FOUND, handle_errors
from agentrun_cli._utils.output import echo_error, format_output
from agentrun_cli._utils.runtime_constants import DEFAULT_DELETE_TIMEOUT_SECONDS
from agentrun_cli._utils.runtime_reconciler import find_runtime_by_name
from agentrun_cli._utils.runtime_state import PollConfig, poll_until_deleted
from agentrun_cli.commands.runtime._helpers import (
    ctx_cfg,
    parse_duration,
    serialize_runtime,
)

AgentRuntime = None


def _lazy_sdk():
    global AgentRuntime
    if AgentRuntime is None:
        from agentrun.agent_runtime import AgentRuntime as _AR
        AgentRuntime = _AR
    return AgentRuntime


def _is_not_found(exc: BaseException) -> bool:
    """Default predicate. SDK raises ``ResourceNotExistError`` after delete."""
    name = type(exc).__name__
    return "NotExist" in name or "NotFound" in name


def _progress(parsed_name, runtime, elapsed):
    if sys.stderr.isatty():
        sys.stderr.write(
            f"[runtime {parsed_name}] status={getattr(runtime, 'status', None)} "
            f"({elapsed:.1f}s)\n"
        )


@click.command(
    "delete",
    help=(
        "Delete an Agent Runtime by name. By default waits until the resource "
        "is gone (or fails)."
    ),
)
@click.argument("name")
@click.option("--wait/--no-wait", default=True, show_default=True)
@click.option(
    "--timeout", default="5m", show_default=True,
    help="Polling timeout (e.g. 300s, 5m).",
)
@click.option(
    "--yes", is_flag=True, default=False,
    help="Skip the interactive confirmation.",
)
@click.pass_context
@handle_errors
def delete_cmd(ctx, name, wait, timeout, yes):
    rt_cls = _lazy_sdk()
    profile, region = ctx_cfg(ctx)
    build_sdk_config(profile_name=profile, region=region)
    runtime = find_runtime_by_name(rt_cls, name)
    if runtime is None:
        echo_error("ResourceNotFound", f"AgentRuntime {name!r} not found.")
        raise SystemExit(EXIT_NOT_FOUND)
    if not yes and sys.stdin.isatty():
        click.confirm(f"Delete AgentRuntime {name!r}?", abort=True)
    runtime.delete()  # SDK chains endpoint deletes internally
    if wait:
        poll_until_deleted(
            runtime, resource_kind="AgentRuntime",
            is_not_found=_is_not_found,
            cfg=PollConfig(timeout=float(
                parse_duration(timeout) or DEFAULT_DELETE_TIMEOUT_SECONDS,
            )),
            on_tick=lambda r, e: _progress(name, r, e),
        )
    format_output(
        ctx,
        {"action": "delete", "runtime": serialize_runtime(runtime)},
        quiet_field="name",
    )
