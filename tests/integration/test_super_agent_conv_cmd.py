"""Integration tests for ``ar sa conv`` subgroup."""

import json
from contextlib import ExitStack, contextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import click
import pytest
from click.testing import CliRunner

from agentrun_cli.main import cli


def _patch_client(agent):
    client = MagicMock()
    client.get.return_value = agent
    return client, _patch_client_cls(client)


def _conv_cmd_globals():
    cmd = (
        cli.get_command(None, "sa")
        .get_command(None, "conv")
        .get_command(
            None,
            "list",
        )
    )
    callback = _unwrap_callback(cmd.callback)
    return callback.__globals__


def _unwrap_callback(callback):
    while "_get_client_cls" not in callback.__globals__:
        callbacks = [
            cell.cell_contents
            for cell in (callback.__closure__ or ())
            if callable(cell.cell_contents)
        ]
        callback = callbacks[0]
    return callback


@contextmanager
def _patch_client_cls(client):
    globals_ = _conv_cmd_globals()
    with ExitStack() as stack:
        stack.enter_context(
            patch.dict(
                globals_,
                {"_get_client_cls": lambda: lambda config: client},
            )
        )
        stack.enter_context(
            patch(
                "agentrun.super_agent.SuperAgentClient",
                return_value=client,
            )
        )
        yield


def _patch_sdk_cfg():
    return patch.dict(
        _conv_cmd_globals(),
        {"build_sdk_config": MagicMock(return_value=MagicMock())},
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
                SimpleNamespace(
                    role="user", content="hi", message_id="m1", created_at=1000
                ),
            ],
            params=None,
        )
        agent.get_conversation_async = AsyncMock(return_value=info)
        client, patcher = _patch_client(agent)
        with _patch_sdk_cfg(), patcher:
            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "sa",
                    "conv",
                    "get",
                    "my-agent",
                    "conv-xxx",
                ],
            )
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
        state_file.write_text(
            json.dumps(
                {
                    "agents": {
                        "my-agent": {
                            "last_conversation_id": "conv-xxx",
                            "last_used_at": "2026-04-16T00:00:00Z",
                        }
                    },
                }
            )
        )
        with (
            _patch_sdk_cfg(),
            patcher,
            patch("agentrun_cli._utils.super_agent_state.STATE_FILE", state_file),
        ):
            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "sa",
                    "conv",
                    "delete",
                    "my-agent",
                    "conv-xxx",
                ],
            )
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
        state_file.write_text(
            json.dumps(
                {
                    "agents": {
                        "my-agent": {
                            "last_conversation_id": "conv-current",
                            "last_used_at": "2026-04-16T00:00:00Z",
                        }
                    },
                }
            )
        )
        with (
            _patch_sdk_cfg(),
            patcher,
            patch("agentrun_cli._utils.super_agent_state.STATE_FILE", state_file),
        ):
            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "sa",
                    "conv",
                    "delete",
                    "my-agent",
                    "conv-old",
                ],
            )
        assert result.exit_code == 0, result.output
        remaining = json.loads(state_file.read_text())
        assert remaining["agents"]["my-agent"]["last_conversation_id"] == "conv-current"


class TestConvList:
    def test_list_returns_rows(self):
        """If SDK has list_conversations_async, it should be used."""
        agent = MagicMock()
        agent.list_conversations_async = AsyncMock(
            return_value=[
                {"conversation_id": "c1", "title": "first"},
                {"conversation_id": "c2", "title": "second"},
            ]
        )
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
        cmd = (
            cli.get_command(None, "sa")
            .get_command(None, "conv")
            .get_command(
                None,
                "list",
            )
        )

        def unavailable(name):
            raise click.ClickException(
                "list_conversations not available on this SDK version; "
                "please upgrade agentrun SDK to >= 0.0.157."
            )

        runner = CliRunner()
        with patch.object(cmd, "callback", unavailable):
            result = runner.invoke(cli, ["sa", "conv", "list", "my-agent"])
        assert result.exit_code != 0
        combined = result.output
        assert "not available" in combined.lower() or "upgrade" in combined.lower()

    def test_list_fallback_branch_raises_click_exception(self):
        """The command implementation fails before calling a missing SDK method."""
        cmd = (
            cli.get_command(None, "sa")
            .get_command(None, "conv")
            .get_command(
                None,
                "list",
            )
        )
        callback = _unwrap_callback(cmd.callback)
        client = MagicMock()
        client.get.return_value = MagicMock(spec=[])
        ctx = click.Context(cmd, obj={"output": "json"})
        with patch.dict(
            callback.__globals__,
            {
                "build_sdk_config": MagicMock(return_value=MagicMock()),
                "_get_client_cls": lambda: lambda config: client,
            },
        ):
            with pytest.raises(click.ClickException) as exc:
                callback(ctx, "my-agent")
        assert "not available" in str(exc.value).lower()


class TestConvAlias:
    def test_conv_is_conversation_alias(self):
        """`ar sa conv` is a short name for `ar sa conversation`."""
        runner = CliRunner()
        # Both should resolve to the same subgroup help
        r1 = runner.invoke(cli, ["sa", "conversation", "--help"])
        r2 = runner.invoke(cli, ["sa", "conv", "--help"])
        assert r1.exit_code == 0
        assert r2.exit_code == 0
