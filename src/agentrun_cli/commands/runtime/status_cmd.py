"""``ar runtime status`` — fetch (and optionally wait for) terminal status."""

from __future__ import annotations

import sys

import click

from agentrun_cli._utils.config import build_sdk_config
from agentrun_cli._utils.error import EXIT_NOT_FOUND, handle_errors
from agentrun_cli._utils.output import echo_error, format_output
from agentrun_cli._utils.runtime_constants import DEFAULT_APPLY_TIMEOUT_SECONDS
from agentrun_cli._utils.runtime_reconciler import find_runtime_by_name
from agentrun_cli._utils.runtime_state import PollConfig, poll_until_final
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


@click.command(
    "status",
    help="Show the status of an Agent Runtime (optionally wait for terminal).",
)
@click.argument("name")
@click.option(
    "--wait",
    is_flag=True,
    default=False,
    help="Poll until the runtime reaches READY/*_FAILED.",
)
@click.option(
    "--timeout",
    default="10m",
    show_default=True,
    help="Polling timeout (only with --wait).",
)
@click.pass_context
@handle_errors
def status_cmd(ctx, name, wait, timeout):
    rt_cls = _lazy_sdk()
    profile, region = ctx_cfg(ctx)
    build_sdk_config(profile_name=profile, region=region)
    runtime = find_runtime_by_name(rt_cls, name)
    if runtime is None:
        echo_error("ResourceNotFound", f"AgentRuntime {name!r} not found.")
        raise SystemExit(EXIT_NOT_FOUND)
    if wait:
        poll_until_final(
            runtime,
            resource_kind="AgentRuntime",
            cfg=PollConfig(
                timeout=float(
                    parse_duration(timeout) or DEFAULT_APPLY_TIMEOUT_SECONDS,
                )
            ),
            on_tick=lambda r, e: (
                sys.stderr.isatty()
                and sys.stderr.write(
                    f"[runtime {name}] status={getattr(r, 'status', None)} ({e:.1f}s)\n"
                )
            ),
        )
    format_output(ctx, serialize_runtime(runtime), quiet_field="name")
