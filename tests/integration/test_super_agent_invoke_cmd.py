"""Integration tests for ``ar sa invoke``."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from click.testing import CliRunner

from agentrun_cli.main import cli


def _make_stream(events, conv_id="conv-xxx"):
    class FakeStream:
        def __init__(self):
            self.conversation_id = conv_id
            self.session_id = "sess-xxx"
            self._iter = iter(events)

        def __aiter__(self):
            return self

        async def __anext__(self):
            try:
                return next(self._iter)
            except StopIteration as exc:
                raise StopAsyncIteration from exc

        async def aclose(self):
            pass

    return FakeStream()


def _make_agent_mock(events, conv_id="conv-xxx"):
    agent = MagicMock()
    agent.invoke_async = AsyncMock(return_value=_make_stream(events, conv_id=conv_id))
    return agent


def _ev(event, data):
    return SimpleNamespace(event=event, data=data, id=None, retry=None)


def _patch_client_get(agent):
    client = MagicMock()
    client.get.return_value = agent
    return client, patch(
        "agentrun_cli.commands.super_agent.invoke_cmd.SuperAgentClient",
        return_value=client,
    )


def _patch_sdk_cfg():
    return patch(
        "agentrun_cli.commands.super_agent.invoke_cmd.build_sdk_config",
        return_value=MagicMock(),
    )


class TestInvokeRaw:
    def test_raw_output_per_event(self):
        events = [
            _ev("RUN_STARTED", '{"threadId":"t","runId":"r"}'),
            _ev("TEXT_MESSAGE_CONTENT", '{"delta":"hi"}'),
            _ev("RUN_FINISHED", "{}"),
        ]
        agent = _make_agent_mock(events)
        client, patcher = _patch_client_get(agent)
        with _patch_sdk_cfg(), patcher:
            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "sa",
                    "invoke",
                    "my-agent",
                    "-m",
                    "hello",
                    "--raw",
                ],
            )
        assert result.exit_code == 0, result.output
        lines = result.output.strip().splitlines()
        # 3 events + 1 envelope
        assert len(lines) == 4
        first = json.loads(lines[0])
        assert first["event"] == "RUN_STARTED"
        envelope = json.loads(lines[-1])
        assert envelope["_meta"] == "envelope"
        assert envelope["conversation_id"] == "conv-xxx"


class TestInvokeTextOnly:
    def test_text_only_output(self):
        events = [
            _ev("RUN_STARTED", "{}"),
            _ev("TEXT_MESSAGE_CONTENT", '{"delta":"Hello "}'),
            _ev("TEXT_MESSAGE_CONTENT", '{"delta":"world"}'),
            _ev("RUN_FINISHED", "{}"),
        ]
        agent = _make_agent_mock(events)
        client, patcher = _patch_client_get(agent)
        with _patch_sdk_cfg(), patcher:
            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "sa",
                    "invoke",
                    "my-agent",
                    "-m",
                    "hi",
                    "--text-only",
                ],
            )
        assert result.exit_code == 0, result.output
        assert "Hello world" in result.output
        assert "_meta" not in result.output


class TestInvokeContinueConversation:
    def test_continue_passes_conversation_id(self):
        events = [_ev("RUN_FINISHED", "{}")]
        agent = _make_agent_mock(events)
        client, patcher = _patch_client_get(agent)
        with _patch_sdk_cfg(), patcher:
            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "sa",
                    "invoke",
                    "my-agent",
                    "-m",
                    "hi",
                    "-c",
                    "conv-prev-xxx",
                    "--raw",
                ],
            )
        assert result.exit_code == 0, result.output
        call_kwargs = agent.invoke_async.await_args.kwargs
        assert call_kwargs["conversation_id"] == "conv-prev-xxx"


class TestInvokeValidation:
    def test_message_and_messages_conflict(self):
        agent = _make_agent_mock([])
        client, patcher = _patch_client_get(agent)
        with _patch_sdk_cfg(), patcher:
            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "sa",
                    "invoke",
                    "my-agent",
                    "-m",
                    "hi",
                    "--messages",
                    '[{"role":"user","content":"x"}]',
                ],
            )
        assert result.exit_code != 0

    def test_neither_message_nor_messages(self):
        agent = _make_agent_mock([])
        client, patcher = _patch_client_get(agent)
        with _patch_sdk_cfg(), patcher:
            runner = CliRunner()
            result = runner.invoke(cli, ["sa", "invoke", "my-agent"])
        assert result.exit_code != 0

    def test_invalid_messages_json(self):
        agent = _make_agent_mock([])
        client, patcher = _patch_client_get(agent)
        with _patch_sdk_cfg(), patcher:
            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "sa",
                    "invoke",
                    "my-agent",
                    "--messages",
                    "not json",
                ],
            )
        assert result.exit_code != 0

    def test_messages_not_array(self):
        agent = _make_agent_mock([])
        client, patcher = _patch_client_get(agent)
        with _patch_sdk_cfg(), patcher:
            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "sa",
                    "invoke",
                    "my-agent",
                    "--messages",
                    '{"role":"user"}',
                ],
            )
        assert result.exit_code != 0

    def test_raw_and_text_only_conflict(self):
        agent = _make_agent_mock([])
        client, patcher = _patch_client_get(agent)
        with _patch_sdk_cfg(), patcher:
            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "sa",
                    "invoke",
                    "my-agent",
                    "-m",
                    "hi",
                    "--raw",
                    "--text-only",
                ],
            )
        assert result.exit_code != 0


class TestInvokeMessagesArray:
    def test_messages_json_array_parsed(self):
        events = [_ev("RUN_FINISHED", "{}")]
        agent = _make_agent_mock(events)
        client, patcher = _patch_client_get(agent)
        with _patch_sdk_cfg(), patcher:
            runner = CliRunner()
            msgs = '[{"role":"user","content":"hi"},{"role":"user","content":"ok"}]'
            result = runner.invoke(
                cli,
                [
                    "sa",
                    "invoke",
                    "my-agent",
                    "--messages",
                    msgs,
                    "--raw",
                ],
            )
        assert result.exit_code == 0, result.output
        call_kwargs = agent.invoke_async.await_args.kwargs
        assert len(call_kwargs["messages"]) == 2
        assert call_kwargs["messages"][0]["content"] == "hi"


class TestInvokeSaveConv:
    def test_save_conv_writes_state(self, tmp_path):
        events = [_ev("RUN_FINISHED", "{}")]
        agent = _make_agent_mock(events)
        client, patcher = _patch_client_get(agent)
        state_file = tmp_path / "state.json"
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
                    "invoke",
                    "my-agent",
                    "-m",
                    "hi",
                    "--save-conv",
                    "--raw",
                ],
            )
        assert result.exit_code == 0, result.output
        saved = json.loads(state_file.read_text())
        assert saved["agents"]["my-agent"]["last_conversation_id"] == "conv-xxx"

    def test_no_save_conv_no_write(self, tmp_path):
        events = [_ev("RUN_FINISHED", "{}")]
        agent = _make_agent_mock(events)
        client, patcher = _patch_client_get(agent)
        state_file = tmp_path / "state.json"
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
                    "invoke",
                    "my-agent",
                    "-m",
                    "hi",
                    "--raw",
                ],
            )
        assert result.exit_code == 0, result.output
        assert not state_file.exists()
