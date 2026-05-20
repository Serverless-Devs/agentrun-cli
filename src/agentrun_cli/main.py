"""AgentRun CLI — entry point.

This module wires up the top-level ``ar`` / ``agentrun`` command group and
registers all sub-command groups (config, model, sandbox, runtime, …).

Usage::

    agentrun --help
    agentrun config set region cn-hangzhou
    agentrun super-agent run
"""

import logging
import os

import click

os.environ.setdefault("DISABLE_BREAKING_CHANGES_WARNING", "1")

from agentrun_cli import __version__
from agentrun_cli.commands.config_cmd import config_group
from agentrun_cli.commands.model_cmd import model_group
from agentrun_cli.commands.runtime import runtime_group
from agentrun_cli.commands.sandbox import sandbox_group
from agentrun_cli.commands.skill_cmd import skill_group
from agentrun_cli.commands.super_agent import super_agent_group
from agentrun_cli.commands.tool_cmd import tool_group


class _DropSdkValidationWarnings(logging.Filter):
    """Drop the SDK's pydantic 'validate type failed' WARNINGs.

    They fire from ``agentrun.utils.model.from_object`` whenever the SDK
    deserializes a server-side record whose shape doesn't match its current
    pydantic schema (e.g. a runtime someone else created with
    ``codeConfiguration.language=java17`` or with an empty ``logConfiguration``).
    That noise is not actionable for the CLI user — a single ``ar runtime list``
    can emit a dozen of them. ``--debug`` re-enables full logging.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        return "validate type failed" not in record.getMessage()


logging.getLogger("agentrun-logger").addFilter(_DropSdkValidationWarnings())


class AliasGroup(click.Group):
    """Click Group that supports hidden command aliases."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._aliases: dict = {}

    def get_command(self, ctx, cmd_name):
        cmd = super().get_command(ctx, cmd_name)
        if cmd is not None:
            return cmd
        real_name = self._aliases.get(cmd_name)
        if real_name:
            return super().get_command(ctx, real_name)
        return None


@click.group(
    cls=AliasGroup,
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.option(
    "--profile",
    default=None,
    envvar="AGENTRUN_PROFILE",
    help="Configuration profile to use (default: 'default').",
)
@click.option(
    "--region",
    default=None,
    envvar="AGENTRUN_REGION",
    help="Override the region setting (e.g. cn-hangzhou, cn-shanghai).",
)
@click.option(
    "--output",
    type=click.Choice(["json", "table", "yaml", "quiet"], case_sensitive=False),
    default="json",
    envvar="AGENTRUN_OUTPUT",
    help="Output format (default: json).",
)
@click.option(
    "--debug",
    is_flag=True,
    default=False,
    help="Enable debug logging.",
)
@click.version_option(__version__, "-V", "--version", prog_name="agentrun-cli")
@click.pass_context
def cli(ctx: click.Context, profile, region, output, debug):
    """AgentRun CLI — manage AI agent infrastructure from the command line.

    Configure credentials first:

        agentrun config set access_key_id <YOUR_AK>

        agentrun config set access_key_secret <YOUR_SK>

        agentrun config set account_id <YOUR_ACCOUNT_ID>

    Then spin up an Agent and start chatting:

        agentrun super-agent run
    """
    ctx.ensure_object(dict)
    ctx.obj["profile"] = profile
    ctx.obj["region"] = region
    ctx.obj["output"] = output

    if debug:
        logging.basicConfig(level=logging.DEBUG)
        # In debug mode users want to see the SDK's validation warnings, so
        # strip the filter we installed at import time.
        sdk_logger = logging.getLogger("agentrun-logger")
        for f in list(sdk_logger.filters):
            if isinstance(f, _DropSdkValidationWarnings):
                sdk_logger.removeFilter(f)


# Register sub-command groups
cli.add_command(config_group)
cli.add_command(model_group)
cli.add_command(sandbox_group)
cli._aliases["sb"] = "sandbox"
cli.add_command(tool_group)
cli.add_command(skill_group)
cli.add_command(super_agent_group)
cli._aliases["sa"] = "super-agent"
cli.add_command(runtime_group)
cli._aliases["rt"] = "runtime"


def main():
    """Callable entry point for console_scripts and ``python -m``."""
    cli()


if __name__ == "__main__":
    main()
