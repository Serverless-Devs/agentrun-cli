"""``ar sandbox process`` — manage sandbox processes."""

import click

from agentrun_cli._utils.error import handle_errors
from agentrun_cli._utils.output import format_output

from ._helpers import _build_cfg


@click.group("process", help="Manage sandbox processes.")
def process_group():
    pass


@process_group.command("list")
@click.argument("sandbox_id")
@click.pass_context
@handle_errors
def process_list(ctx, sandbox_id):
    """List processes in the sandbox."""
    from agentrun.sandbox import Sandbox

    cfg = _build_cfg(ctx)
    sb = Sandbox.connect(sandbox_id, config=cfg)
    result = sb.process.list()
    format_output(ctx, result)


@process_group.command("get")
@click.argument("sandbox_id")
@click.argument("pid")
@click.pass_context
@handle_errors
def process_get(ctx, sandbox_id, pid):
    """Get process details."""
    from agentrun.sandbox import Sandbox

    cfg = _build_cfg(ctx)
    sb = Sandbox.connect(sandbox_id, config=cfg)
    result = sb.process.get(pid=pid)
    format_output(ctx, result)


@process_group.command("kill")
@click.argument("sandbox_id")
@click.argument("pid")
@click.pass_context
@handle_errors
def process_kill(ctx, sandbox_id, pid):
    """Kill a process in the sandbox."""
    from agentrun.sandbox import Sandbox

    cfg = _build_cfg(ctx)
    sb = Sandbox.connect(sandbox_id, config=cfg)
    result = sb.process.kill(pid=pid)
    format_output(ctx, result if result else {"pid": pid, "killed": True})
