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
    """List processes in the sandbox.

    Returns all processes visible to the container, including ones not
    started via the Process API. To act on a process via ``get`` / ``kill``,
    start it with ``cmd`` first, or fall back to ``cmd --command "kill <pid>"``.
    """
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
    """Get process details. Only PIDs started via the Process API are resolvable."""
    from agentrun.sandbox import Sandbox

    cfg = _build_cfg(ctx)
    sb = Sandbox.connect(sandbox_id, config=cfg)
    result = sb.process.get(pid=pid)
    format_output(ctx, result)


@process_group.command("kill")
@click.argument("sandbox_id")
@click.argument("pid")
@click.option(
    "--force-shell",
    is_flag=True,
    help=(
        "If the Process API does not know this PID, "
        "fall back to 'kill -9 <pid>' via the shell."
    ),
)
@click.pass_context
@handle_errors
def process_kill(ctx, sandbox_id, pid, force_shell):
    """Kill a process in the sandbox.

    By default this targets processes registered through the Process API.
    Container-level PIDs returned by ``process list`` but not registered
    through Process API will report ``process with PID ... not found``; pass
    ``--force-shell`` to fall back to ``kill -9 <pid>`` via the shell.
    """
    from agentrun.sandbox import Sandbox

    cfg = _build_cfg(ctx)
    sb = Sandbox.connect(sandbox_id, config=cfg)

    if force_shell:
        shell_result = sb.process.cmd(command=f"kill -9 {pid}", cwd="/", timeout=10)
        format_output(
            ctx,
            {"pid": pid, "killed_via": "shell", "result": shell_result},
            quiet_field="pid",
        )
        return

    result = sb.process.kill(pid=pid)
    format_output(ctx, result if result else {"pid": pid, "killed": True})
