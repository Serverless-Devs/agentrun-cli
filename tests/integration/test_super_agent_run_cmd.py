"""Integration tests for ``ar sa run``."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from click.testing import CliRunner

from agentrun_cli.main import cli


def _ev(event, data):
    return SimpleNamespace(event=event, data=data, id=None, retry=None)


def _make_agent(name="super-agent-tmp-xxx"):
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
            except StopIteration:
                raise StopAsyncIteration

        async def aclose(self):
            pass

    agent = MagicMock()
    agent.name = name
    agent.agent_runtime_id = "ar-xxx"
    agent.invoke_async = AsyncMock(return_value=Stream())
    return agent


def _patch_all(agent):
    client = MagicMock()
    client.create.return_value = agent
    return (
        patch("agentrun_cli.commands.super_agent.run_cmd.SuperAgentClient",
              return_value=client),
        patch("agentrun_cli.commands.super_agent.run_cmd.build_sdk_config",
              return_value=MagicMock()),
    ), client


class TestRunNonInteractive:

    def test_run_with_all_flags(self, tmp_path):
        agent = _make_agent()
        (client_p, cfg_p), client = _patch_all(agent)
        state_file = tmp_path / "state.json"
        with client_p, cfg_p, \
             patch("agentrun_cli._utils.super_agent_state.STATE_FILE", state_file):
            runner = CliRunner()
            result = runner.invoke(
                cli,
                ["sa", "run",
                 "--prompt", "hi",
                 "--model-service", "svc-tongyi",
                 "--model", "qwen-max",
                 "-m", "ping", "--raw"],
                input="/exit\n",
            )
        assert result.exit_code == 0, result.output
        client.create.assert_called_once()
        kwargs = client.create.call_args.kwargs
        assert kwargs["model_service_name"] == "svc-tongyi"
        assert kwargs["model_name"] == "qwen-max"

    def test_run_missing_model_no_input(self):
        agent = _make_agent()
        (client_p, cfg_p), client = _patch_all(agent)
        with client_p, cfg_p:
            runner = CliRunner()
            result = runner.invoke(
                cli, ["sa", "run", "--prompt", "hi", "--no-input"],
            )
        assert result.exit_code != 0

    def test_run_auto_name_generated(self, tmp_path):
        agent = _make_agent()
        (client_p, cfg_p), client = _patch_all(agent)
        state_file = tmp_path / "state.json"
        with client_p, cfg_p, \
             patch("agentrun_cli._utils.super_agent_state.STATE_FILE", state_file):
            runner = CliRunner()
            result = runner.invoke(
                cli,
                ["sa", "run",
                 "--prompt", "hi",
                 "--model-service", "svc", "--model", "m",
                 "--raw"],
                input="/exit\n",
            )
        assert result.exit_code == 0, result.output
        kwargs = client.create.call_args.kwargs
        assert kwargs["name"].startswith("super-agent-tmp-")

    def test_run_explicit_name(self, tmp_path):
        agent = _make_agent()
        (client_p, cfg_p), client = _patch_all(agent)
        state_file = tmp_path / "state.json"
        with client_p, cfg_p, \
             patch("agentrun_cli._utils.super_agent_state.STATE_FILE", state_file):
            runner = CliRunner()
            result = runner.invoke(
                cli,
                ["sa", "run",
                 "--name", "my-custom",
                 "--prompt", "hi",
                 "--model-service", "svc", "--model", "m",
                 "--raw"],
                input="/exit\n",
            )
        assert result.exit_code == 0, result.output
        kwargs = client.create.call_args.kwargs
        assert kwargs["name"] == "my-custom"

    def test_run_with_tools(self, tmp_path):
        agent = _make_agent()
        (client_p, cfg_p), client = _patch_all(agent)
        state_file = tmp_path / "state.json"
        with client_p, cfg_p, \
             patch("agentrun_cli._utils.super_agent_state.STATE_FILE", state_file):
            runner = CliRunner()
            result = runner.invoke(
                cli,
                ["sa", "run",
                 "--prompt", "x",
                 "--model-service", "svc", "--model", "m",
                 "--tool", "t1", "--tool", "t2",
                 "--raw"],
                input="/exit\n",
            )
        assert result.exit_code == 0, result.output
        kwargs = client.create.call_args.kwargs
        assert kwargs["tools"] == ["t1", "t2"]
