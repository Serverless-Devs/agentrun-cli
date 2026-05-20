"""Tests for runtime_state polling primitives."""

from types import SimpleNamespace

import pytest

from agentrun_cli._utils.error import RuntimePollFailed, RuntimePollTimeout
from agentrun_cli._utils.runtime_state import PollConfig, poll_until_final


def _mk_resource(statuses, name="my-agent"):
    """Build a fake resource whose .refresh() advances through statuses."""
    states = iter(statuses)
    res = SimpleNamespace(
        status=next(states),
        status_reason=None,
        agent_runtime_name=name,
        name=name,
    )

    def _refresh(*args, **kwargs):
        try:
            res.status = next(states)
        except StopIteration:
            pass
        return res

    res.refresh = _refresh
    return res


def test_poll_config_defaults():
    cfg = PollConfig()
    assert cfg.initial_interval == 3.0
    assert cfg.max_interval == 10.0
    assert cfg.backoff_factor == 1.5
    assert cfg.timeout == 600.0


def test_poll_config_override():
    cfg = PollConfig(timeout=42.0, initial_interval=1.0)
    assert cfg.timeout == 42.0
    assert cfg.initial_interval == 1.0


def test_poll_until_ready(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    res = _mk_resource(["CREATING", "CREATING", "READY"])
    out = poll_until_final(
        res,
        resource_kind="AgentRuntime",
        cfg=PollConfig(timeout=10.0, initial_interval=0.0),
    )
    assert out.status == "READY"


def test_poll_failed_raises(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    res = _mk_resource(["CREATING", "CREATE_FAILED"])
    res.status_reason = "image pull backoff"
    with pytest.raises(RuntimePollFailed) as exc:
        poll_until_final(
            res,
            resource_kind="AgentRuntime",
            cfg=PollConfig(timeout=10.0, initial_interval=0.0),
        )
    assert exc.value.status == "CREATE_FAILED"
    assert "image pull" in str(exc.value)


def test_poll_timeout(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    res = _mk_resource(["CREATING"] * 50)
    fake_clock = iter([0.0, 5.0, 11.0])  # passes timeout=10 on 3rd check
    monkeypatch.setattr("time.monotonic", lambda: next(fake_clock))
    with pytest.raises(RuntimePollTimeout):
        poll_until_final(
            res,
            resource_kind="AgentRuntime",
            cfg=PollConfig(timeout=10.0, initial_interval=0.0),
        )


class FakeNotFound(Exception):
    pass


def test_poll_until_deleted(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    res = SimpleNamespace(status="DELETING", status_reason=None, agent_runtime_name="x")
    call_count = {"n": 0}

    def _refresh(*a, **k):
        call_count["n"] += 1
        if call_count["n"] >= 2:
            raise FakeNotFound("gone")
        return res

    res.refresh = _refresh
    from agentrun_cli._utils.runtime_state import poll_until_deleted

    poll_until_deleted(
        res,
        resource_kind="AgentRuntime",
        is_not_found=lambda e: isinstance(e, FakeNotFound),
        cfg=PollConfig(timeout=10.0, initial_interval=0.0),
    )


def test_poll_until_delete_failed(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    states = iter(["DELETING", "DELETE_FAILED"])
    res = SimpleNamespace(
        status=next(states),
        status_reason="quota exceeded",
        agent_runtime_name="x",
    )

    def _refresh(*a, **k):
        try:
            res.status = next(states)
        except StopIteration:
            pass
        return res

    res.refresh = _refresh
    from agentrun_cli._utils.runtime_state import poll_until_deleted

    with pytest.raises(RuntimePollFailed) as exc:
        poll_until_deleted(
            res,
            resource_kind="AgentRuntime",
            is_not_found=lambda e: False,
            cfg=PollConfig(timeout=10.0, initial_interval=0.0),
        )
    assert "DELETE_FAILED" in str(exc.value)


def test_poll_many_parallel_all_ready(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    from agentrun_cli._utils.runtime_state import poll_many_parallel

    res_a = _mk_resource(["CREATING", "READY"], name="a")
    res_b = _mk_resource(["CREATING", "CREATING", "READY"], name="b")
    out = poll_many_parallel(
        [res_a, res_b],
        resource_kind="AgentRuntimeEndpoint",
        cfg=PollConfig(timeout=10.0, initial_interval=0.0),
        concurrency=2,
    )
    assert len(out) == 2
    assert all(r.status == "READY" for r in out)


def test_poll_many_parallel_one_fails(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    from agentrun_cli._utils.runtime_state import poll_many_parallel

    res_a = _mk_resource(["CREATING", "READY"], name="a")
    res_b = _mk_resource(["CREATING", "CREATE_FAILED"], name="b")
    with pytest.raises(RuntimePollFailed):
        poll_many_parallel(
            [res_a, res_b],
            resource_kind="AgentRuntimeEndpoint",
            cfg=PollConfig(timeout=10.0, initial_interval=0.0),
            concurrency=2,
        )


def test_poll_until_final_on_tick_invoked(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    res = _mk_resource(["CREATING", "READY"])
    seen: list = []
    poll_until_final(
        res,
        resource_kind="AgentRuntime",
        cfg=PollConfig(timeout=10.0, initial_interval=0.0),
        on_tick=lambda r, e: seen.append((r.status, e)),
    )
    assert seen  # at least one tick
    assert seen[0][0] == "CREATING"


def test_poll_until_deleted_on_tick_and_timeout(monkeypatch):
    """Exercise on_tick + timeout branches in poll_until_deleted."""
    monkeypatch.setattr("time.sleep", lambda *_: None)
    res = SimpleNamespace(status="DELETING", status_reason=None, agent_runtime_name="x")
    res.refresh = lambda *a, **k: res  # never raises
    fake_clock = iter([0.0, 11.0])  # passes timeout=10 on 2nd check
    monkeypatch.setattr("time.monotonic", lambda: next(fake_clock))
    from agentrun_cli._utils.runtime_state import poll_until_deleted

    seen: list = []
    with pytest.raises(RuntimePollTimeout):
        poll_until_deleted(
            res,
            resource_kind="AgentRuntime",
            is_not_found=lambda e: False,
            cfg=PollConfig(timeout=10.0, initial_interval=0.0),
            on_tick=lambda r, e: seen.append(e),
        )
    assert seen


def test_poll_until_deleted_refresh_raises_other(monkeypatch):
    """Non-not-found exceptions from refresh propagate."""
    monkeypatch.setattr("time.sleep", lambda *_: None)
    res = SimpleNamespace(status="DELETING", status_reason=None, agent_runtime_name="x")

    def _refresh(*a, **k):
        raise RuntimeError("boom")

    res.refresh = _refresh
    from agentrun_cli._utils.runtime_state import poll_until_deleted

    with pytest.raises(RuntimeError, match="boom"):
        poll_until_deleted(
            res,
            resource_kind="AgentRuntime",
            is_not_found=lambda e: False,
            cfg=PollConfig(timeout=10.0, initial_interval=0.0),
        )


def test_resource_name_fallback_to_unnamed():
    """_resource_name returns '<unnamed>' when no known attr is set."""
    from agentrun_cli._utils.runtime_state import _resource_name

    res = SimpleNamespace()  # no name attributes at all
    assert _resource_name(res) == "<unnamed>"


def test_resource_name_skips_falsy_first_attrs():
    """Skip empty values and fall through to a later populated attr."""
    from agentrun_cli._utils.runtime_state import _resource_name

    res = SimpleNamespace(
        agent_runtime_name=None,
        agent_runtime_endpoint_name="",
        name="resolved",
    )
    assert _resource_name(res) == "resolved"


def test_poll_many_parallel_empty_list():
    from agentrun_cli._utils.runtime_state import poll_many_parallel

    assert poll_many_parallel([], resource_kind="AgentRuntimeEndpoint") == []
