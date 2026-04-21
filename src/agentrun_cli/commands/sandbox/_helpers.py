"""Shared utilities for sandbox CLI commands."""

import json
import sys
from typing import Optional

import click

from agentrun_cli._utils.config import build_sdk_config


def _build_cfg(ctx: click.Context):
    """Build SDK Config from CLI context."""
    return build_sdk_config(
        profile_name=(ctx.obj or {}).get("profile"),
        region=(ctx.obj or {}).get("region"),
    )


def _load_json_option(raw: Optional[str]) -> Optional[dict]:
    """Parse a --from-file path or inline JSON string into a dict."""
    if raw is None:
        return None
    if not raw.strip().startswith("{"):
        with open(raw, "r", encoding="utf-8") as f:
            return json.load(f)
    return json.loads(raw)


def _read_code_input(code: Optional[str], code_file: Optional[str]) -> str:
    """Resolve code from --code, --file, or stdin."""
    if code and code_file:
        raise click.UsageError("--code and --file are mutually exclusive.")
    if code:
        return code
    if code_file:
        with open(code_file, "r", encoding="utf-8") as f:
            return f.read()
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise click.UsageError("Provide code via --code, --file, or stdin.")


def _read_content_input(content: Optional[str], use_stdin: bool) -> str:
    """Resolve content from --content or --stdin flag."""
    if content and use_stdin:
        raise click.UsageError("--content and --stdin are mutually exclusive.")
    if content:
        return content
    if use_stdin:
        return sys.stdin.read()
    raise click.UsageError("Provide content via --content or --stdin.")
