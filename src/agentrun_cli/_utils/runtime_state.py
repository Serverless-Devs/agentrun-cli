"""Async-status polling primitives for AgentRuntime / AgentRuntimeEndpoint.

These helpers know nothing about the SDK shape — callers pass in a callable
(``refresh_fn``) plus accessors for ``status`` and the resource name. This keeps
the module trivially mockable and lets us reuse it for both ``AgentRuntime`` and
``AgentRuntimeEndpoint`` (which share ``Status`` semantics).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

from agentrun_cli._utils.error import RuntimePollFailed, RuntimePollTimeout
from agentrun_cli._utils.runtime_constants import (
    ENDPOINT_POLL_CONCURRENCY,
    POLL_BACKOFF_FACTOR,
    POLL_INITIAL_INTERVAL,
    POLL_MAX_INTERVAL,
)

_FAILED_SUFFIX = "_FAILED"
_READY = "READY"


@dataclass
class PollConfig:
    initial_interval: float = POLL_INITIAL_INTERVAL
    max_interval: float = POLL_MAX_INTERVAL
    backoff_factor: float = POLL_BACKOFF_FACTOR
    timeout: float = 600.0


def poll_until_final(
    resource: Any,
    *,
    resource_kind: str,
    cfg: PollConfig | None = None,
    on_tick: Callable[[Any, float], None] | None = None,
) -> Any:
    """Block until ``resource.status`` is a final state.

    Final = ``READY`` or any ``*_FAILED``. ``DELETING`` is NOT final (use
    ``poll_until_deleted`` for delete paths).

    Side effects: calls ``resource.refresh()`` between checks; sleeps with
    exponential backoff capped at ``cfg.max_interval``.

    Raises:
        RuntimePollFailed: status ends in ``_FAILED``.
        RuntimePollTimeout: elapsed time exceeds ``cfg.timeout``.
    """
    cfg = cfg or PollConfig()
    start = time.monotonic()
    interval = cfg.initial_interval
    name = _resource_name(resource)
    while True:
        status = getattr(resource, "status", None)
        elapsed = time.monotonic() - start
        if on_tick:
            on_tick(resource, elapsed)
        if status == _READY:
            return resource
        if isinstance(status, str) and status.endswith(_FAILED_SUFFIX):
            raise RuntimePollFailed(
                resource_kind=resource_kind,
                name=name,
                status=status,
                reason=getattr(resource, "status_reason", None),
            )
        if elapsed >= cfg.timeout:
            raise RuntimePollTimeout(
                resource_kind=resource_kind,
                name=name,
                elapsed=elapsed,
            )
        time.sleep(interval)
        interval = min(interval * cfg.backoff_factor, cfg.max_interval)
        resource.refresh()


def poll_until_deleted(
    resource: Any,
    *,
    resource_kind: str,
    is_not_found: Callable[[BaseException], bool],
    cfg: PollConfig | None = None,
    on_tick: Callable[[Any, float], None] | None = None,
) -> None:
    """Poll until ``resource.refresh()`` raises a NotFound-like exception.

    The caller supplies ``is_not_found`` because the SDK uses different
    exception classes (and we avoid importing them at module load time).
    """
    cfg = cfg or PollConfig()
    start = time.monotonic()
    interval = cfg.initial_interval
    name = _resource_name(resource)
    while True:
        elapsed = time.monotonic() - start
        if on_tick:
            on_tick(resource, elapsed)
        status = getattr(resource, "status", None)
        if isinstance(status, str) and status.endswith(_FAILED_SUFFIX):
            raise RuntimePollFailed(
                resource_kind=resource_kind,
                name=name,
                status=status,
                reason=getattr(resource, "status_reason", None),
            )
        if elapsed >= cfg.timeout:
            raise RuntimePollTimeout(
                resource_kind=resource_kind,
                name=name,
                elapsed=elapsed,
            )
        time.sleep(interval)
        interval = min(interval * cfg.backoff_factor, cfg.max_interval)
        try:
            resource.refresh()
        except BaseException as e:  # noqa: BLE001 — caller decides
            if is_not_found(e):
                return
            raise


def _resource_name(resource: Any) -> str:
    for attr in (
        "agent_runtime_name",
        "agent_runtime_endpoint_name",
        "name",
        "agent_runtime_id",
        "agent_runtime_endpoint_id",
    ):
        v = getattr(resource, attr, None)
        if v:
            return str(v)
    return "<unnamed>"


def poll_many_parallel(
    resources: list,
    *,
    resource_kind: str,
    cfg: PollConfig | None = None,
    concurrency: int = ENDPOINT_POLL_CONCURRENCY,
    on_tick: Callable[[Any, float], None] | None = None,
) -> list:
    """Poll multiple resources to terminal state concurrently.

    Re-raises the first ``RuntimePollFailed`` / ``RuntimePollTimeout`` that
    surfaces. Already-completed pollers are cancelled (best-effort) on
    failure — Python's ThreadPoolExecutor doesn't preempt running tasks, so
    in-flight pollers continue until their next sleep boundary.
    """
    cfg = cfg or PollConfig()
    if not resources:
        return []
    concurrency = max(1, min(concurrency, len(resources)))
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures = {
            ex.submit(
                poll_until_final,
                r,
                resource_kind=resource_kind,
                cfg=cfg,
                on_tick=on_tick,
            ): r
            for r in resources
        }
        results: list = []
        for fut in as_completed(futures):
            results.append(fut.result())  # re-raises first exception
        return results
