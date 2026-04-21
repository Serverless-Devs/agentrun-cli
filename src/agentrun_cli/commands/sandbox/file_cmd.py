"""``ar sandbox file`` — file operations on a sandbox."""

import click

from agentrun_cli._utils.error import handle_errors
from agentrun_cli._utils.output import format_output

from ._helpers import _build_cfg, _read_content_input


@click.group("file", help="File operations on a sandbox.")
def file_group():
    pass


@file_group.command("read")
@click.argument("sandbox_id")
@click.argument("path")
@click.pass_context
@handle_errors
def file_read(ctx, sandbox_id, path):
    """Read a file from the sandbox."""
    from agentrun.sandbox import Sandbox

    cfg = _build_cfg(ctx)
    sb = Sandbox.connect(sandbox_id, config=cfg)
    result = sb.file.read(path=path)
    format_output(ctx, result)


@file_group.command("write")
@click.argument("sandbox_id")
@click.argument("path")
@click.option("--content", default=None, help="File content.")
@click.option("--stdin", "use_stdin", is_flag=True, help="Read content from stdin.")
@click.option("--mode", default="644", help="File permission mode.")
@click.option("--encoding", default="utf-8", help="File encoding.")
@click.pass_context
@handle_errors
def file_write(ctx, sandbox_id, path, content, use_stdin, mode, encoding):
    """Write content to a file in the sandbox."""
    from agentrun.sandbox import Sandbox

    cfg = _build_cfg(ctx)
    content_str = _read_content_input(content, use_stdin)
    sb = Sandbox.connect(sandbox_id, config=cfg)
    result = sb.file.write(path=path, content=content_str, mode=mode, encoding=encoding)
    format_output(ctx, result)


@file_group.command("upload")
@click.argument("sandbox_id")
@click.argument("local_path", type=click.Path(exists=True))
@click.argument("remote_path")
@click.pass_context
@handle_errors
def file_upload(ctx, sandbox_id, local_path, remote_path):
    """Upload a local file to the sandbox."""
    from agentrun.sandbox import Sandbox

    cfg = _build_cfg(ctx)
    sb = Sandbox.connect(sandbox_id, config=cfg)
    result = sb.file_system.upload(local_path=local_path, remote_path=remote_path)
    format_output(ctx, result)


@file_group.command("download")
@click.argument("sandbox_id")
@click.argument("remote_path")
@click.argument("local_path")
@click.pass_context
@handle_errors
def file_download(ctx, sandbox_id, remote_path, local_path):
    """Download a file from the sandbox to local."""
    from agentrun.sandbox import Sandbox

    cfg = _build_cfg(ctx)
    sb = Sandbox.connect(sandbox_id, config=cfg)
    result = sb.file_system.download(path=remote_path, save_path=local_path)
    format_output(ctx, result)


@file_group.command("ls")
@click.argument("sandbox_id")
@click.argument("path", default="/")
@click.option("--depth", type=int, default=1, help="Recursive depth.")
@click.pass_context
@handle_errors
def file_ls(ctx, sandbox_id, path, depth):
    """List directory contents in the sandbox."""
    from agentrun.sandbox import Sandbox

    cfg = _build_cfg(ctx)
    sb = Sandbox.connect(sandbox_id, config=cfg)
    result = sb.file_system.list(path=path, depth=depth)
    format_output(ctx, result)


@file_group.command("stat")
@click.argument("sandbox_id")
@click.argument("path")
@click.pass_context
@handle_errors
def file_stat(ctx, sandbox_id, path):
    """Get file metadata in the sandbox."""
    from agentrun.sandbox import Sandbox

    cfg = _build_cfg(ctx)
    sb = Sandbox.connect(sandbox_id, config=cfg)
    result = sb.file_system.stat(path=path)
    format_output(ctx, result)


@file_group.command("mv")
@click.argument("sandbox_id")
@click.argument("source")
@click.argument("destination")
@click.pass_context
@handle_errors
def file_mv(ctx, sandbox_id, source, destination):
    """Move or rename a file in the sandbox."""
    from agentrun.sandbox import Sandbox

    cfg = _build_cfg(ctx)
    sb = Sandbox.connect(sandbox_id, config=cfg)
    result = sb.file_system.move(source=source, destination=destination)
    format_output(ctx, result)


@file_group.command("rm")
@click.argument("sandbox_id")
@click.argument("path")
@click.pass_context
@handle_errors
def file_rm(ctx, sandbox_id, path):
    """Remove a file or directory in the sandbox."""
    from agentrun.sandbox import Sandbox

    cfg = _build_cfg(ctx)
    sb = Sandbox.connect(sandbox_id, config=cfg)
    result = sb.file_system.remove(path=path)
    format_output(ctx, result)


@file_group.command("mkdir")
@click.argument("sandbox_id")
@click.argument("path")
@click.option("--mode", default="0755", help="Directory permission mode.")
@click.pass_context
@handle_errors
def file_mkdir(ctx, sandbox_id, path, mode):
    """Create a directory in the sandbox."""
    from agentrun.sandbox import Sandbox

    cfg = _build_cfg(ctx)
    sb = Sandbox.connect(sandbox_id, config=cfg)
    result = sb.file_system.mkdir(path=path, mode=mode)
    format_output(ctx, result)
