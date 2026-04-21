"""Unit tests for super_agent helpers."""

from types import SimpleNamespace

from agentrun_cli.commands.super_agent._helpers import (
    asyncio_run,
    ctx_cfg,
    serialize_super_agent,
)


class TestSerializeSuperAgent:

    def test_serialize_full(self):
        agent = SimpleNamespace(
            name="my-agent",
            description="test",
            prompt="You are helpful",
            agents=["sub-a"],
            tools=["t1", "t2"],
            skills=["s1"],
            sandboxes=[],
            workspaces=[],
            model_service_name="svc-tongyi",
            model_name="qwen-max",
            agent_runtime_id="ar-xxx",
            arn="acs:agentrun:...:ar-xxx",
            status="READY",
            external_endpoint="https://...",
            created_at="2026-04-16T00:00:00Z",
            last_updated_at="2026-04-16T00:00:00Z",
        )
        out = serialize_super_agent(agent)
        assert out["name"] == "my-agent"
        assert out["tools"] == ["t1", "t2"]
        assert out["model_service_name"] == "svc-tongyi"
        assert out["model_name"] == "qwen-max"
        assert out["status"] == "READY"
        assert out["agent_runtime_id"] == "ar-xxx"
        assert out["external_endpoint"] == "https://..."

    def test_serialize_empty_lists(self):
        agent = SimpleNamespace(
            name="x", description=None, prompt=None,
            agents=[], tools=[], skills=[], sandboxes=[], workspaces=[],
            model_service_name=None, model_name=None,
            agent_runtime_id="", arn="", status="",
            external_endpoint="", created_at="", last_updated_at="",
        )
        out = serialize_super_agent(agent)
        assert out["tools"] == []
        assert out["model_service_name"] is None

    def test_serialize_partial_object(self):
        agent = SimpleNamespace(name="x")
        out = serialize_super_agent(agent)
        assert out["name"] == "x"
        assert out["tools"] == []
        assert out["model_service_name"] is None


class TestAsyncioRun:

    def test_runs_coroutine(self):
        async def coro():
            return 42
        assert asyncio_run(coro()) == 42

    def test_propagates_exception(self):
        async def coro():
            raise ValueError("boom")
        try:
            asyncio_run(coro())
        except ValueError as e:
            assert "boom" in str(e)
        else:
            raise AssertionError("expected ValueError")


class TestCtxCfg:

    def test_ctx_cfg_from_obj(self):
        class FakeCtx:
            obj = {"profile": "p1", "region": "cn-shanghai"}
        profile, region = ctx_cfg(FakeCtx())
        assert profile == "p1"
        assert region == "cn-shanghai"

    def test_ctx_cfg_no_obj(self):
        class FakeCtx:
            obj = None
        profile, region = ctx_cfg(FakeCtx())
        assert profile is None
        assert region is None
