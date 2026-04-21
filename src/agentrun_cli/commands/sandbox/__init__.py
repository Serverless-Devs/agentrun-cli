"""``ar sandbox`` — manage sandbox instances and templates."""

import click

from .browser_cmd import browser_group
from .context_cmd import context_group
from .exec_cmd import register_exec_commands
from .file_cmd import file_group
from .lifecycle_cmd import register_lifecycle_commands
from .process_cmd import process_group
from .template_cmd import template_group


@click.group("sandbox", help="Manage sandbox instances and templates. (alias: sb)")
def sandbox_group():
    pass


# Register sub-groups
sandbox_group.add_command(template_group)
sandbox_group.add_command(context_group)
sandbox_group.add_command(file_group)
sandbox_group.add_command(process_group)
sandbox_group.add_command(browser_group)

# Register sub-group aliases
sandbox_group.add_command(template_group, "tpl")
sandbox_group.add_command(context_group, "ctx")
sandbox_group.add_command(file_group, "f")
sandbox_group.add_command(process_group, "ps")
sandbox_group.add_command(browser_group, "br")

# Register commands directly on sandbox_group
register_lifecycle_commands(sandbox_group)
register_exec_commands(sandbox_group)
