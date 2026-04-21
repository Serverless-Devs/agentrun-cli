"""``ar super-agent`` (``ar sa``) — manage super agents.

Super agents are platform-hosted AI agents configured declaratively with
``prompt / tools / skills / model``. Users don't need to manage runtime code
or containers.

See ``docs_inner/cli-design-super-agent.md`` for the full design.
"""

import click

from agentrun_cli.commands.super_agent import apply_cmd as _apply_mod
from agentrun_cli.commands.super_agent import chat_cmd as _chat_mod
from agentrun_cli.commands.super_agent import conv_cmd as _conv_mod
from agentrun_cli.commands.super_agent import invoke_cmd as _invoke_mod
from agentrun_cli.commands.super_agent import run_cmd as _run_mod
from agentrun_cli.commands.super_agent.crud_cmd import (
    create_cmd,
    delete_cmd,
    get_cmd,
    list_cmd,
    update_cmd,
)


class _AliasedSuperAgentGroup(click.Group):
    """Super-agent group with ``conv`` as an alias for ``conversation``."""

    _ALIASES = {"conv": "conversation"}

    def get_command(self, ctx, cmd_name):
        cmd = super().get_command(ctx, cmd_name)
        if cmd is not None:
            return cmd
        real = self._ALIASES.get(cmd_name)
        if real:
            return super().get_command(ctx, real)
        return None


@click.group(
    "super-agent",
    cls=_AliasedSuperAgentGroup,
    help="Manage super agents (platform-hosted AI agents).",
)
def super_agent_group():
    pass


super_agent_group.add_command(create_cmd)
super_agent_group.add_command(get_cmd)
super_agent_group.add_command(list_cmd)
super_agent_group.add_command(update_cmd)
super_agent_group.add_command(delete_cmd)
super_agent_group.add_command(_invoke_mod.invoke_cmd)
super_agent_group.add_command(_chat_mod.chat_cmd)
super_agent_group.add_command(_run_mod.run_cmd)
super_agent_group.add_command(_apply_mod.apply_cmd)
super_agent_group.add_command(_apply_mod.render_cmd)
super_agent_group.add_command(_conv_mod.conv_group)


__all__ = ["super_agent_group"]
