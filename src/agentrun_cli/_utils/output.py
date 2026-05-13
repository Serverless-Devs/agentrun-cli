"""Unified output formatting for all CLI commands.

Supports four modes controlled by the global ``--output`` flag:
  - json   (default) — indented JSON, ideal for AI agents to parse
  - table  — human-friendly table via ``rich``
  - yaml   — YAML serialisation
  - quiet  — print only the primary identifier (e.g. resource name/id)
"""

import json
from collections.abc import Sequence
from typing import Any

import click


def echo_json(data: Any) -> None:
    """Pretty-print *data* as indented JSON to stdout."""
    click.echo(json.dumps(data, indent=2, ensure_ascii=False, default=str))


def echo_table(rows: Sequence[dict], columns: list[str] | None = None) -> None:
    """Render a list of dicts as a rich table.

    Falls back to JSON if ``rich`` is unavailable.
    """
    try:
        from rich.console import Console
        from rich.table import Table
    except ImportError:
        echo_json(rows)
        return

    if not rows:
        click.echo("(no results)")
        return

    cols = columns or list(rows[0].keys())
    table = Table(show_header=True, header_style="bold")
    for c in cols:
        table.add_column(c)
    for row in rows:
        table.add_row(*[str(row.get(c, "")) for c in cols])
    Console().print(table)


def echo_quiet(data: Any, field: str | None = None) -> None:
    """Print only the most relevant value — useful for shell pipelines.

    Heuristic for picking the value:
      1. *field* if supplied and present in *data*
      2. First key that ends with ``_name`` or ``_id``
      3. The raw value if *data* is a plain string
    """
    if isinstance(data, str):
        click.echo(data)
        return
    if isinstance(data, dict):
        if field and field in data:
            click.echo(data[field])
            return
        for key in data:
            if key.endswith("_name") or key.endswith("_id"):
                click.echo(data[key])
                return
        click.echo(json.dumps(data, ensure_ascii=False, default=str))
        return
    click.echo(str(data))


def format_output(
    ctx: click.Context, data: Any, quiet_field: str | None = None
) -> None:
    """Route *data* to the appropriate formatter based on ``ctx.obj["output"]``."""
    fmt = (ctx.obj or {}).get("output", "json")

    if fmt == "table":
        if isinstance(data, list):
            echo_table(data)
        elif isinstance(data, dict):
            echo_table([data])
        else:
            echo_json(data)
    elif fmt == "yaml":
        try:
            import yaml

            click.echo(yaml.dump(data, allow_unicode=True, default_flow_style=False))
        except ImportError:
            echo_json(data)
    elif fmt == "quiet":
        echo_quiet(data, quiet_field)
    else:
        echo_json(data)


def echo_error(error_type: str, message: str, hint: str | None = None) -> None:
    """Write a structured JSON error to stderr.

    When *hint* is provided it is included as a ``hint`` field in the JSON
    payload — used to surface Prerequisites links on permission failures.
    """
    payload: dict = {"error": error_type, "message": message}
    if hint:
        payload["hint"] = hint
    click.echo(json.dumps(payload, ensure_ascii=False), err=True)
