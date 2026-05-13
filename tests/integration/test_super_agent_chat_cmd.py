"""Integration tests for ``ar sa chat``."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from click.testing import CliRunner

from agentrun_cli.main import cli


def _ev(event, data):
    return SimpleNamespace(event=event, data=data, id=None, retry=None)


def _make_agent():
    class Stream:
        def __init__(self):
            self.conversation_id = "conv-new"
            self.session_id = "s"
            self._it = iter([_ev("RUN_FINISHED", "{}")])

        def __aiter__(self):
            return self

        async def __anext__(self):
            try:
                return next(self._it)
            except StopIteration as exc:
                raise StopAsyncIteration from exc

        async def aclose(self):
            pass

    agent = MagicMock()
    agent.invoke_async = AsyncMock(return_value=Stream())
    return agent


def _patch_stack(agent):
    client = MagicMock()
    client.get.return_value = agent
    return (
        patch(
            "agentrun_cli.commands.super_agent.chat_cmd.SuperAgentClient",
            return_value=client,
        ),
        patch(
            "agentrun_cli.commands.super_agent.chat_cmd.build_sdk_config",
            return_value=MagicMock(),
        ),
    )


class TestChatResumeFromState:
    def test_chat_reads_last_conv(self, tmp_path):
        state_file = tmp_path / "state.json"
        state_file.write_text(
            json.dumps(
                {
                    "agents": {
                        "my-agent": {
                            "last_conversation_id": "conv-prev",
                            "last_used_at": "2026-04-16T00:00:00Z",
                        }
                    },
                }
            )
        )
        agent = _make_agent()
        client_p, cfg_p = _patch_stack(agent)
        with (
            client_p,
            cfg_p,
            patch("agentrun_cli._utils.super_agent_state.STATE_FILE", state_file),
        ):
            runner = CliRunner()
            # Use -m to supply initial message, then input /exit to quit REPL
            result = runner.invoke(
                cli,
                ["sa", "chat", "my-agent", "-m", "hi", "--raw"],
                input="/exit\n",
            )
        assert result.exit_code == 0, result.output
        first_call = agent.invoke_async.await_args_list[0]
        assert first_call.kwargs["conversation_id"] == "conv-prev"


class TestChatNewFlag:
    def test_new_flag_clears_state(self, tmp_path):
        state_file = tmp_path / "state.json"
        state_file.write_text(
            json.dumps(
                {
                    "agents": {
                        "my-agent": {
                            "last_conversation_id": "conv-prev",
                            "last_used_at": "2026-04-16T00:00:00Z",
                        }
                    },
                }
            )
        )
        agent = _make_agent()
        client_p, cfg_p = _patch_stack(agent)
        with (
            client_p,
            cfg_p,
            patch("agentrun_cli._utils.super_agent_state.STATE_FILE", state_file),
        ):
            runner = CliRunner()
            result = runner.invoke(
                cli,
                ["sa", "chat", "my-agent", "--new", "-m", "hi", "--raw"],
                input="/exit\n",
            )
        assert result.exit_code == 0, result.output
        first_call = agent.invoke_async.await_args_list[0]
        assert first_call.kwargs["conversation_id"] is None


class TestChatExplicitConv:
    def test_explicit_conv_overrides_state(self, tmp_path):
        state_file = tmp_path / "state.json"
        state_file.write_text(
            json.dumps(
                {
                    "agents": {
                        "my-agent": {
                            "last_conversation_id": "conv-state",
                            "last_used_at": "2026-04-16T00:00:00Z",
                        }
                    },
                }
            )
        )
        agent = _make_agent()
        client_p, cfg_p = _patch_stack(agent)
        with (
            client_p,
            cfg_p,
            patch("agentrun_cli._utils.super_agent_state.STATE_FILE", state_file),
        ):
            runner = CliRunner()
            result = runner.invoke(
                cli,
                ["sa", "chat", "my-agent", "-c", "conv-explicit", "-m", "hi", "--raw"],
                input="/exit\n",
            )
        assert result.exit_code == 0, result.output
        first_call = agent.invoke_async.await_args_list[0]
        assert first_call.kwargs["conversation_id"] == "conv-explicit"


class TestChatRawTextOnlyConflict:
    def test_raw_and_text_only_both_fail(self):
        agent = _make_agent()
        client_p, cfg_p = _patch_stack(agent)
        with client_p, cfg_p:
            runner = CliRunner()
            result = runner.invoke(
                cli,
                ["sa", "chat", "x", "--raw", "--text-only"],
                input="/exit\n",
            )
        assert result.exit_code != 0
