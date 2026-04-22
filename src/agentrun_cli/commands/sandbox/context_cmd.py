"""``ar sandbox context`` — manage execution contexts."""

import click

from agentrun_cli._utils.error import handle_errors
from agentrun_cli._utils.output import format_output

from ._helpers import _build_cfg


def _serialize_context(ops):
    """Flatten the SDK's ContextOperations chain object into a dict."""
    cid = getattr(ops, "context_id", None) or getattr(ops, "_context_id", None)
    return {
        "id": cid,
        "language": getattr(ops, "_language", None),
        "cwd": getattr(ops, "_cwd", None),
    }


@click.group("context", help="Manage execution contexts.")
def context_group():
    pass


@context_group.command("create")
@click.argument("sandbox_id")
@click.option("--language", default="python", help="Language: python / javascript.")
@click.option("--cwd", default=None, help="Working directory.")
@click.pass_context
@handle_errors
def context_create(ctx, sandbox_id, language, cwd):
    """Create a new execution context."""
    from agentrun.sandbox import Sandbox

    cfg = _build_cfg(ctx)
    sb = Sandbox.connect(sandbox_id, config=cfg)
    result = sb.context.create(language=language, cwd=cwd)
    format_output(ctx, _serialize_context(result), quiet_field="id")


@context_group.command("list")
@click.argument("sandbox_id")
@click.pass_context
@handle_errors
def context_list(ctx, sandbox_id):
    """List execution contexts."""
    from agentrun.sandbox import Sandbox

    cfg = _build_cfg(ctx)
    sb = Sandbox.connect(sandbox_id, config=cfg)
    result = sb.context.list()
    format_output(ctx, result)


@context_group.command("get")
@click.argument("sandbox_id")
@click.argument("context_id")
@click.pass_context
@handle_errors
def context_get(ctx, sandbox_id, context_id):
    """Get execution context details."""
    from agentrun.sandbox import Sandbox

    cfg = _build_cfg(ctx)
    sb = Sandbox.connect(sandbox_id, config=cfg)
    result = sb.context.get(context_id=context_id)
    format_output(ctx, _serialize_context(result), quiet_field="id")


@context_group.command("delete")
@click.argument("sandbox_id")
@click.argument("context_id")
@click.pass_context
@handle_errors
def context_delete(ctx, sandbox_id, context_id):
    """Delete an execution context."""
    from agentrun.sandbox import Sandbox

    cfg = _build_cfg(ctx)
    sb = Sandbox.connect(sandbox_id, config=cfg)
    result = sb.context.delete(context_id=context_id)
    format_output(ctx, result if result else {"id": context_id, "deleted": True})
