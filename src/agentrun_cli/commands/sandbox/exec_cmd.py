"""``ar sandbox exec`` and ``ar sandbox cmd`` — code and shell execution."""

import click

from agentrun_cli._utils.error import handle_errors
from agentrun_cli._utils.output import format_output

from ._helpers import _build_cfg, _read_code_input


def register_exec_commands(sandbox_group: click.Group):
    """Register exec and cmd commands directly on the sandbox group."""

    @sandbox_group.command("exec")
    @click.argument("sandbox_id")
    @click.option("--code", default=None, help="Inline code to execute.")
    @click.option("--file", "code_file", default=None, type=click.Path(exists=True), help="Path to code file.")
    @click.option("--language", default=None, help="Language: python / javascript. Defaults to python when --context-id is not set; must be omitted when --context-id is set.")
    @click.option("--context-id", default=None, help="Context ID for stateful execution.")
    @click.option("--timeout", type=int, default=30, help="Execution timeout (seconds).")
    @click.pass_context
    @handle_errors
    def sandbox_exec(ctx, sandbox_id, code, code_file, language, context_id, timeout):
        """Execute code in a sandbox."""
        from agentrun.sandbox import Sandbox

        if context_id and language:
            raise click.UsageError("--context-id and --language are mutually exclusive.")

        if not context_id and not language:
            language = "python"

        cfg = _build_cfg(ctx)
        code_str = _read_code_input(code, code_file)
        sb = Sandbox.connect(sandbox_id, config=cfg)
        result = sb.context.execute(
            code=code_str,
            language=language,
            context_id=context_id,
            timeout=timeout,
        )
        format_output(ctx, result)

    @sandbox_group.command("cmd")
    @click.argument("sandbox_id")
    @click.option("--command", required=True, help="Shell command to execute.")
    @click.option("--cwd", required=True, help="Working directory.")
    @click.option("--timeout", type=int, default=30, help="Execution timeout (seconds).")
    @click.pass_context
    @handle_errors
    def sandbox_cmd(ctx, sandbox_id, command, cwd, timeout):
        """Execute a shell command in a sandbox."""
        from agentrun.sandbox import Sandbox

        cfg = _build_cfg(ctx)
        sb = Sandbox.connect(sandbox_id, config=cfg)
        result = sb.process.cmd(command=command, cwd=cwd, timeout=timeout)
        format_output(ctx, result)
