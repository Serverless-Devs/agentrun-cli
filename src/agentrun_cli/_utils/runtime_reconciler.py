"""Apply-time reconciler: list → diff → create/update/delete.

This module is the orchestration brain for ``ar runtime apply``. It does not
poll — it just submits the SDK calls and hands the in-flight resource handles
back to the command layer (which then drives ``runtime_state.poll_*``).

Endpoint reconciliation does a by-name diff and supports pruning unknown
endpoints (default on; toggled by ``ar runtime apply --no-prune-endpoints``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from agentrun_cli._utils.agentruntime_yaml import (
    ParsedAgentRuntime,
    ParsedEndpoint,
)
from agentrun_cli._utils.runtime_render import (
    endpoint_needs_update,
    to_endpoint_create_inputs,
    to_endpoint_update_input,
    to_runtime_create_input,
    to_runtime_update_input,
)

Action = Literal["create", "update", "delete", "noop"]


@dataclass
class RuntimeReconcileResult:
    action: Action
    runtime: Any


@dataclass
class EndpointAction:
    action: Action
    name: str
    endpoint: Any | None


@dataclass
class ApplyPlan:
    runtime_result: RuntimeReconcileResult
    endpoint_actions: list[EndpointAction] = field(default_factory=list)


def find_runtime_by_name(client: Any, name: str):
    """List runtimes and return the first whose ``agent_runtime_name`` matches.

    The SDK exposes ``list_all`` returning an iterable of AgentRuntime objects.
    Filtering happens client-side; the backend has no name-filter on list.
    """
    for rt in client.list_all():
        if getattr(rt, "agent_runtime_name", None) == name:
            return rt
    return None


def reconcile_runtime(
    parsed: ParsedAgentRuntime,
    *,
    client: Any,
) -> RuntimeReconcileResult:
    """List by name → create or update_by_id.

    Returns the in-flight resource (status likely CREATING / UPDATING) so the
    caller can poll it.
    """
    existing = find_runtime_by_name(client, parsed.name)
    if existing is None:
        runtime = client.create(to_runtime_create_input(parsed))
        return RuntimeReconcileResult(action="create", runtime=runtime)
    runtime = client.update_by_id(
        existing.agent_runtime_id,
        to_runtime_update_input(parsed),
    )
    return RuntimeReconcileResult(action="update", runtime=runtime)


def reconcile_endpoints(
    runtime: Any,
    *,
    desired: list[ParsedEndpoint] | None,
    prune: bool = True,
) -> list[EndpointAction]:
    """Apply-time endpoint diff.

    Args:
        runtime: a Runtime instance with ``list_endpoints / create_endpoint /
            update_endpoint / delete_endpoint`` methods (matches SDK 0.0.200).
        desired: parsed list. ``None`` means "user omitted endpoints"; the CLI
            injects a single ``default`` endpoint. ``[]`` means "explicitly no
            endpoints"; the CLI deletes orphans when ``prune`` is True.
        prune: when True, endpoints present remotely but absent from ``desired``
            are deleted.

    Returns:
        Ordered list of ``EndpointAction`` capturing what happened.
    """
    if desired is None:
        # CLI injects a single default endpoint.
        desired = [ParsedEndpoint(name="default", target_version="LATEST")]

    current_by_name = {
        getattr(ep, "agent_runtime_endpoint_name", None): ep
        for ep in runtime.list_endpoints()
    }
    desired_names = {ep.name for ep in desired}
    actions: list[EndpointAction] = []

    # to_create / to_update / noop
    create_inputs = to_endpoint_create_inputs(
        # Build a stub-parsed runtime carrying just .endpoints
        _StubWithEndpoints(desired)
    )
    create_inputs_by_name = {ci.agent_runtime_endpoint_name: ci for ci in create_inputs}

    for ep in desired:
        current = current_by_name.get(ep.name)
        if current is None:
            ci = create_inputs_by_name[ep.name]
            new_ep = runtime.create_endpoint(ci)
            actions.append(
                EndpointAction(action="create", name=ep.name, endpoint=new_ep)
            )
            continue
        if endpoint_needs_update(ep, current):
            updated = runtime.update_endpoint(
                current.agent_runtime_endpoint_id,
                to_endpoint_update_input(ep),
            )
            actions.append(
                EndpointAction(action="update", name=ep.name, endpoint=updated)
            )
        else:
            actions.append(
                EndpointAction(action="noop", name=ep.name, endpoint=current)
            )

    # prune
    if prune:
        for name, current in current_by_name.items():
            if name in desired_names:
                continue
            runtime.delete_endpoint(current.agent_runtime_endpoint_id)
            actions.append(EndpointAction(action="delete", name=name, endpoint=current))

    return actions


class _StubWithEndpoints:
    """Tiny adapter so we can reuse ``to_endpoint_create_inputs``."""

    def __init__(self, endpoints):
        self.endpoints = endpoints
