"""Integration tests for ``ar sa conv`` subgroup."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from click.testing import CliRunner

from agentrun_cli.main import cli


def _patch_client(agent):
    client = MagicMock()
    client.get.return_value = agent
    return client, patch(
        "agentrun_cli.commands.super_agent.conv_cmd.SuperAgentClient",
        return_value=client,
    )


def _patch_sdk_cfg():
    return patch(
        "agentrun_cli.commands.super_agent.conv_cmd.build_sdk_config",
        return_value=MagicMock(),
    )


class TestConvGet:

    def test_get_conversation(self):
        agent = MagicMock()
        info = SimpleNamespace(
            conversation_id="conv-xxx",
            agent_id="ar-xxx",
            title="test",
            main_user_id="u1",
            sub_user_id=None,
            created_at=1000,
            updated_at=2000,
            error_message=None,
            invoke_info=None,
            messages=[
                SimpleNamespace(role="user", content="hi",
                                message_id="m1", created_at=1000),
            ],
            params=None,
        )
        agent.get_conversation_async = AsyncMock(return_value=info)
        client, patcher = _patch_client(agent)
        with _patch_sdk_cfg(), patcher:
            runner = CliRunner()
            result = runner.invoke(cli, [
                "sa", "conv", "get", "my-agent", "conv-xxx",
            ])
        assert result.exit_code == 0, result.output
        out = json.loads(result.output)
        assert out["conversation_id"] == "conv-xxx"
        assert len(out["messages"]) == 1
        assert out["messages"][0]["role"] == "user"


class TestConvDelete:

    def test_delete_clears_matching_state(self, tmp_path):
        agent = MagicMock()
        agent.delete_conversation_async = AsyncMock(return_value=None)
        client, patcher = _patch_client(agent)
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps({
            "agents": {"my-agent": {
                "last_conversation_id": "conv-xxx",
                "last_used_at": "2026-04-16T00:00:00Z",
            }},
        }))
        with _patch_sdk_cfg(), patcher, \
             patch("agentrun_cli._utils.super_agent_state.STATE_FILE", state_file):
            runner = CliRunner()
            result = runner.invoke(cli, [
                "sa", "conv", "delete", "my-agent", "conv-xxx",
            ])
        assert result.exit_code == 0, result.output
        out = json.loads(result.output)
        assert out["deleted"] is True
        remaining = json.loads(state_file.read_text())
        assert "my-agent" not in remaining["agents"]

    def test_delete_non_matching_keeps_state(self, tmp_path):
        agent = MagicMock()
        agent.delete_conversation_async = AsyncMock(return_value=None)
        client, patcher = _patch_client(agent)
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps({
            "agents": {"my-agent": {
                "last_conversation_id": "conv-current",
                "last_used_at": "2026-04-16T00:00:00Z",
            }},
        }))
        with _patch_sdk_cfg(), patcher, \
             patch("agentrun_cli._utils.super_agent_state.STATE_FILE", state_file):
            runner = CliRunner()
            result = runner.invoke(cli, [
                "sa", "conv", "delete", "my-agent", "conv-old",
            ])
        assert result.exit_code == 0, result.output
        remaining = json.loads(state_file.read_text())
        assert remaining["agents"]["my-agent"]["last_conversation_id"] == "conv-current"


class TestConvList:

    def test_list_returns_rows(self):
        """If SDK has list_conversations_async, it should be used."""
        agent = MagicMock()
        agent.list_conversations_async = AsyncMock(return_value=[
            {"conversation_id": "c1", "title": "first"},
            {"conversation_id": "c2", "title": "second"},
        ])
        client, patcher = _patch_client(agent)
        with _patch_sdk_cfg(), patcher:
            runner = CliRunner()
            result = runner.invoke(cli, ["sa", "conv", "list", "my-agent"])
        assert result.exit_code == 0, result.output
        out = json.loads(result.output)
        assert len(out) == 2
        assert out[0]["conversation_id"] == "c1"

    def test_list_not_implemented_fallback(self):
        """If SDK does not have list_conversations_async, return error."""
        agent = MagicMock(spec=[])  # empty spec: no methods
        client, patcher = _patch_client(agent)
        with _patch_sdk_cfg(), patcher:
            runner = CliRunner()
            result = runner.invoke(cli, ["sa", "conv", "list", "my-agent"])
        assert result.exit_code != 0
        combined = result.output + (result.stderr or "")
        assert "not available" in combined.lower() or "upgrade" in combined.lower()


class TestConvAlias:

    def test_conv_is_conversation_alias(self):
        """`ar sa conv` is a short name for `ar sa conversation`."""
        runner = CliRunner()
        # Both should resolve to the same subgroup help
        r1 = runner.invoke(cli, ["sa", "conversation", "--help"])
        r2 = runner.invoke(cli, ["sa", "conv", "--help"])
        assert r1.exit_code == 0
        assert r2.exit_code == 0
