"""``ar runtime`` (``ar rt``) — declarative Agent Runtime management.

See ``projects/agent-infra-build-runit/design/runtime-cli-design.md`` for the
full design. PR4 ships ``apply`` and ``render``; PR5 adds ``get / list /
delete / status``.
"""

import os

# Mirror ``main.py``: silence the SDK's "you are using version 0.0.200"
# warning even when the command is invoked through a test harness that
# bypasses ``main`` (e.g. tests/integration/test_runtime_cmd.py::_root).
os.environ.setdefault("DISABLE_BREAKING_CHANGES_WARNING", "1")

import click  # noqa: E402

from agentrun_cli.commands.runtime import apply_cmd as _apply_mod  # noqa: E402
from agentrun_cli.commands.runtime import (
    cloud_build_cmd as _cloud_build_mod,  # noqa: E402
)
from agentrun_cli.commands.runtime import crud_cmd as _crud_mod  # noqa: E402
from agentrun_cli.commands.runtime import delete_cmd as _delete_mod  # noqa: E402
from agentrun_cli.commands.runtime import render_cmd as _render_mod  # noqa: E402
from agentrun_cli.commands.runtime import status_cmd as _status_mod  # noqa: E402


@click.group(
    "runtime",
    help="Manage Agent Runtimes declaratively (container mode only).",
)
def runtime_group():
    pass


runtime_group.add_command(_apply_mod.apply_cmd)
runtime_group.add_command(_cloud_build_mod.cloud_build_cmd)
runtime_group.add_command(_render_mod.render_cmd)
runtime_group.add_command(_crud_mod.get_cmd)
runtime_group.add_command(_crud_mod.list_cmd)
runtime_group.add_command(_delete_mod.delete_cmd)
runtime_group.add_command(_status_mod.status_cmd)


__all__ = ["runtime_group"]
