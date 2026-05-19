"""Shared helpers for ``ar runtime`` commands."""

from __future__ import annotations

import re


def ctx_cfg(ctx) -> tuple[str | None, str | None]:
    obj = getattr(ctx, "obj", None) or {}
    return obj.get("profile"), obj.get("region")


def parse_duration(value: str) -> int:
    """Parse ``10m`` / ``300s`` / ``1h`` / plain integer seconds → seconds."""
    if isinstance(value, int):
        return value
    if value is None:
        return 0
    m = re.fullmatch(r"(\d+)\s*(s|sec|m|min|h|hr|hour)?", str(value).strip(),
                     re.IGNORECASE)
    if not m:
        raise ValueError(f"Invalid duration {value!r}")
    n = int(m.group(1))
    unit = (m.group(2) or "s").lower()
    if unit.startswith("s"):
        return n
    if unit.startswith("m"):
        return n * 60
    return n * 3600


def serialize_runtime(rt) -> dict:
    """Convert an AgentRuntime SDK object to a plain dict."""
    return {
        "name": getattr(rt, "agent_runtime_name", None),
        "id": getattr(rt, "agent_runtime_id", None),
        "arn": getattr(rt, "agent_runtime_arn", None),
        "version": getattr(rt, "agent_runtime_version", None),
        "status": _coerce_status(getattr(rt, "status", None)),
        "statusReason": getattr(rt, "status_reason", None),
        "createdAt": getattr(rt, "created_at", None),
        "lastUpdatedAt": getattr(rt, "last_updated_at", None),
    }


def serialize_endpoint(ep) -> dict:
    return {
        "name": getattr(ep, "agent_runtime_endpoint_name", None),
        "id": getattr(ep, "agent_runtime_endpoint_id", None),
        "status": _coerce_status(getattr(ep, "status", None)),
        "statusReason": getattr(ep, "status_reason", None),
        "publicUrl": getattr(ep, "endpoint_public_url", None),
        "targetVersion": getattr(ep, "target_version", None),
    }


def _coerce_status(s):
    if s is None:
        return None
    if hasattr(s, "value"):
        return s.value
    return str(s)
