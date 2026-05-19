"""Unit tests for ``agentrun_cli.commands.runtime._helpers``."""

from types import SimpleNamespace

import pytest

from agentrun_cli.commands.runtime._helpers import (
    _coerce_status,
    ctx_cfg,
    parse_duration,
    serialize_endpoint,
    serialize_runtime,
)


class TestParseDuration:
    def test_int_passthrough(self):
        assert parse_duration(42) == 42

    def test_none_returns_zero(self):
        assert parse_duration(None) == 0

    def test_seconds_default(self):
        assert parse_duration("30") == 30

    def test_explicit_seconds(self):
        assert parse_duration("90s") == 90
        assert parse_duration("90sec") == 90

    def test_minutes(self):
        assert parse_duration("10m") == 600
        assert parse_duration("5min") == 300

    def test_hours(self):
        assert parse_duration("2h") == 7200
        assert parse_duration("1hr") == 3600
        assert parse_duration("3hour") == 10800

    def test_case_insensitive_and_whitespace(self):
        assert parse_duration(" 10 M ") == 600

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            parse_duration("ten minutes")


class TestCtxCfg:
    def test_no_obj(self):
        ctx = SimpleNamespace(obj=None)
        assert ctx_cfg(ctx) == (None, None)

    def test_with_obj(self):
        ctx = SimpleNamespace(obj={"profile": "staging", "region": "cn-hangzhou"})
        assert ctx_cfg(ctx) == ("staging", "cn-hangzhou")

    def test_missing_attr(self):
        ctx = SimpleNamespace()
        assert ctx_cfg(ctx) == (None, None)


class TestCoerceStatus:
    def test_none(self):
        assert _coerce_status(None) is None

    def test_enum_like(self):
        class StatusLike:
            value = "READY"
        assert _coerce_status(StatusLike()) == "READY"

    def test_plain_string(self):
        assert _coerce_status("CREATING") == "CREATING"


class TestSerializeRuntime:
    def test_full_object(self):
        rt = SimpleNamespace(
            agent_runtime_name="my-agent",
            agent_runtime_id="ar-1",
            agent_runtime_arn="acs:ar-1",
            agent_runtime_version="1",
            status="READY",
            status_reason=None,
            created_at="t0",
            last_updated_at="t1",
        )
        out = serialize_runtime(rt)
        assert out["name"] == "my-agent"
        assert out["id"] == "ar-1"
        assert out["arn"] == "acs:ar-1"
        assert out["status"] == "READY"

    def test_minimal_object(self):
        rt = SimpleNamespace()
        out = serialize_runtime(rt)
        assert all(v is None for v in out.values())


class TestSerializeEndpoint:
    def test_full_object(self):
        ep = SimpleNamespace(
            agent_runtime_endpoint_name="default",
            agent_runtime_endpoint_id="ep-1",
            status="READY",
            status_reason=None,
            endpoint_public_url="https://x/",
            target_version="LATEST",
        )
        out = serialize_endpoint(ep)
        assert out["name"] == "default"
        assert out["publicUrl"] == "https://x/"

    def test_minimal(self):
        ep = SimpleNamespace()
        out = serialize_endpoint(ep)
        assert all(v is None for v in out.values())
