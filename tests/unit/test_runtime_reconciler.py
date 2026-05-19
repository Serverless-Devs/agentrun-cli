"""Tests for the apply reconciler."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from agentrun_cli._utils.agentruntime_yaml import (
    ParsedAgentRuntime,
    ParsedContainer,
    ParsedEndpoint,
)
from agentrun_cli._utils.runtime_reconciler import (
    ApplyPlan,
    EndpointAction,
    RuntimeReconcileResult,
    find_runtime_by_name,
    reconcile_endpoints,
    reconcile_runtime,
)


def test_dataclasses_exist():
    rr = RuntimeReconcileResult(action="create", runtime=SimpleNamespace())
    ea = EndpointAction(action="create", name="default", endpoint=None)
    plan = ApplyPlan(runtime_result=rr, endpoint_actions=[ea])
    assert plan.runtime_result.action == "create"


def test_find_runtime_by_name_match():
    sdk = MagicMock()
    sdk.list_all.return_value = [
        SimpleNamespace(agent_runtime_name="other", agent_runtime_id="ar-1"),
        SimpleNamespace(agent_runtime_name="me", agent_runtime_id="ar-2"),
    ]
    out = find_runtime_by_name(sdk, "me")
    assert out is not None and out.agent_runtime_id == "ar-2"


def test_find_runtime_by_name_missing():
    sdk = MagicMock()
    sdk.list_all.return_value = []
    assert find_runtime_by_name(sdk, "me") is None


def _parsed():
    return ParsedAgentRuntime(
        name="my-agent",
        container=ParsedContainer(image="img:v1"),
    )


def test_reconcile_runtime_creates_when_absent():
    client = MagicMock()
    client.list_all.return_value = []
    created = SimpleNamespace(
        agent_runtime_name="my-agent",
        agent_runtime_id="ar-new",
        status="CREATING",
    )
    client.create.return_value = created

    out = reconcile_runtime(_parsed(), client=client)
    assert out.action == "create"
    assert out.runtime.agent_runtime_id == "ar-new"
    client.create.assert_called_once()


def test_reconcile_runtime_updates_when_present():
    client = MagicMock()
    existing = SimpleNamespace(
        agent_runtime_name="my-agent",
        agent_runtime_id="ar-1",
        status="READY",
    )
    client.list_all.return_value = [existing]
    updated = SimpleNamespace(
        agent_runtime_name="my-agent",
        agent_runtime_id="ar-1",
        status="UPDATING",
    )
    client.update_by_id.return_value = updated

    out = reconcile_runtime(_parsed(), client=client)
    assert out.action == "update"
    assert out.runtime.status == "UPDATING"
    client.update_by_id.assert_called_once()
    # First positional arg must be the existing id
    assert client.update_by_id.call_args[0][0] == "ar-1"


def _ep_remote(name, ep_id, **extra):
    return SimpleNamespace(
        agent_runtime_endpoint_name=name,
        agent_runtime_endpoint_id=ep_id,
        target_version=extra.get("target_version"),
        routing_configuration=extra.get("routing_configuration"),
        description=extra.get("description"),
        disable_public_network_access=extra.get("disable_public_network_access"),
    )


def test_reconcile_endpoints_creates_default_when_none_desired():
    runtime = MagicMock()
    runtime.agent_runtime_id = "ar-1"
    runtime.list_endpoints.return_value = []
    runtime.create_endpoint.return_value = _ep_remote("default", "ep-1")

    actions = reconcile_endpoints(runtime, desired=None, prune=True)
    assert len(actions) == 1
    assert actions[0].action == "create"
    assert actions[0].name == "default"
    runtime.create_endpoint.assert_called_once()


def test_reconcile_endpoints_empty_list_prunes_existing():
    runtime = MagicMock()
    runtime.agent_runtime_id = "ar-1"
    runtime.list_endpoints.return_value = [_ep_remote("default", "ep-1")]

    actions = reconcile_endpoints(runtime, desired=[], prune=True)
    assert len(actions) == 1
    assert actions[0].action == "delete"
    runtime.delete_endpoint.assert_called_once_with("ep-1")


def test_reconcile_endpoints_no_prune_keeps_existing():
    runtime = MagicMock()
    runtime.list_endpoints.return_value = [_ep_remote("orphan", "ep-9")]

    actions = reconcile_endpoints(
        runtime,
        desired=[ParsedEndpoint(name="prod", target_version="LATEST")],
        prune=False,
    )
    # Should create "prod"; orphan stays untouched (no delete action).
    assert {a.action for a in actions} == {"create"}
    runtime.delete_endpoint.assert_not_called()


def test_reconcile_endpoints_updates_on_drift():
    runtime = MagicMock()
    current = _ep_remote("prod", "ep-1", target_version="OLD")
    runtime.list_endpoints.return_value = [current]
    runtime.update_endpoint.return_value = _ep_remote(
        "prod",
        "ep-1",
        target_version="LATEST",
    )

    actions = reconcile_endpoints(
        runtime,
        desired=[ParsedEndpoint(name="prod", target_version="LATEST")],
        prune=True,
    )
    assert any(a.action == "update" for a in actions)
    runtime.update_endpoint.assert_called_once()


def test_reconcile_endpoints_noop_when_aligned():
    runtime = MagicMock()
    current = _ep_remote("prod", "ep-1", target_version="LATEST")
    runtime.list_endpoints.return_value = [current]

    actions = reconcile_endpoints(
        runtime,
        desired=[ParsedEndpoint(name="prod", target_version="LATEST")],
        prune=True,
    )
    assert any(a.action == "noop" for a in actions)
    runtime.update_endpoint.assert_not_called()
