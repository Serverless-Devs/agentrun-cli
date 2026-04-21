"""Shared helpers for super_agent commands."""

import asyncio
from typing import Optional, Tuple


def serialize_super_agent(agent) -> dict:
    """Convert a SuperAgent SDK instance to a plain dict for output.

    Uses getattr so partial / mocked instances don't crash.
    """
    return {
        "name": getattr(agent, "name", None),
        "description": getattr(agent, "description", None),
        "prompt": getattr(agent, "prompt", None),
        "agents": list(getattr(agent, "agents", []) or []),
        "tools": list(getattr(agent, "tools", []) or []),
        "skills": list(getattr(agent, "skills", []) or []),
        "sandboxes": list(getattr(agent, "sandboxes", []) or []),
        "workspaces": list(getattr(agent, "workspaces", []) or []),
        "model_service_name": getattr(agent, "model_service_name", None),
        "model_name": getattr(agent, "model_name", None),
        "agent_runtime_id": getattr(agent, "agent_runtime_id", "") or "",
        "arn": getattr(agent, "arn", "") or "",
        "status": getattr(agent, "status", "") or "",
        "external_endpoint": getattr(agent, "external_endpoint", "") or "",
        "created_at": getattr(agent, "created_at", "") or "",
        "last_updated_at": getattr(agent, "last_updated_at", "") or "",
    }


def asyncio_run(coro):
    """Run an async coroutine and return its result.

    Wrapper kept as a module function so tests can patch a single symbol.
    """
    return asyncio.run(coro)


def ctx_cfg(ctx) -> Tuple[Optional[str], Optional[str]]:
    """Return (profile, region) from ctx.obj (tolerating None)."""
    obj = getattr(ctx, "obj", None) or {}
    return obj.get("profile"), obj.get("region")
