"""Unit tests for super_agent REPL core."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from agentrun_cli._utils.super_agent_render import RenderMode
from agentrun_cli._utils.super_agent_repl import (
    ReplConfig,
    SlashResult,
    handle_slash,
    run_repl,
)


def _ev(event, data):
    return SimpleNamespace(event=event, data=data, id=None, retry=None)


def _make_agent(events_per_turn):
    """Agent whose invoke_async returns a fresh stream per call."""

    def make_stream(events, conv_id="conv-xxx"):
        class S:
            def __init__(self):
                self.conversation_id = conv_id
                self.session_id = "s"
                self._it = iter(events)

            def __aiter__(self):
                return self

            async def __anext__(self):
                try:
                    return next(self._it)
                except StopIteration as exc:
                    raise StopAsyncIteration from exc

            async def aclose(self):
                pass

        return S()

    async def invoke(messages, conversation_id=None):
        if not events_per_turn:
            raise AssertionError("no more turns available")
        evs = events_per_turn.pop(0)
        return make_stream(evs)

    agent = MagicMock()
    agent.invoke_async = AsyncMock(side_effect=invoke)
    return agent


class TestHandleSlash:
    def test_exit(self):
        assert handle_slash("/exit") == SlashResult.EXIT

    def test_quit(self):
        assert handle_slash("/quit") == SlashResult.EXIT

    def test_new(self):
        assert handle_slash("/new") == SlashResult.NEW_CONV

    def test_conv(self):
        assert handle_slash("/conv") == SlashResult.PRINT_CONV

    def test_raw(self):
        assert handle_slash("/raw") == SlashResult.TOGGLE_RAW

    def test_help(self):
        assert handle_slash("/help") == SlashResult.HELP

    def test_unknown_slash(self):
        assert handle_slash("/nope") == SlashResult.UNKNOWN

    def test_non_slash(self):
        assert handle_slash("hello") == SlashResult.NOT_SLASH

    def test_empty_line(self):
        assert handle_slash("") == SlashResult.NOT_SLASH

    def test_slash_with_args(self):
        assert handle_slash("/exit now") == SlashResult.EXIT


class TestRunReplSingleTurn:
    def test_single_message_prints_reply(self):
        events = [
            [
                _ev("RUN_STARTED", "{}"),
                _ev("TEXT_MESSAGE_CONTENT", '{"delta":"hi"}'),
                _ev("RUN_FINISHED", "{}"),
            ]
        ]
        agent = _make_agent(events)
        cfg = ReplConfig(
            agent_name="my-agent",
            render_mode=RenderMode.PRETTY,
            initial_conv_id=None,
            input_fn=MagicMock(side_effect=["/exit"]),
            initial_message="hello",
        )
        with patch(
            "agentrun_cli._utils.super_agent_repl.STATE_FILE_WRITER"
        ) as state_writer:
            run_repl(agent, cfg)
        assert agent.invoke_async.await_count == 1
        state_writer.assert_called_with("my-agent", "conv-xxx")

    def test_initial_message_then_user_input(self):
        events = [
            [_ev("RUN_FINISHED", "{}")],
            [_ev("RUN_FINISHED", "{}")],
        ]
        agent = _make_agent(events)
        cfg = ReplConfig(
            agent_name="x",
            render_mode=RenderMode.RAW,
            initial_conv_id=None,
            input_fn=MagicMock(side_effect=["next message", "/exit"]),
            initial_message="first",
        )
        with patch("agentrun_cli._utils.super_agent_repl.STATE_FILE_WRITER"):
            run_repl(agent, cfg)
        assert agent.invoke_async.await_count == 2

    def test_eof_exits(self):
        agent = _make_agent([])
        cfg = ReplConfig(
            agent_name="x",
            render_mode=RenderMode.RAW,
            input_fn=MagicMock(side_effect=EOFError()),
        )
        with patch("agentrun_cli._utils.super_agent_repl.STATE_FILE_WRITER"):
            final = run_repl(agent, cfg)
        assert final is None


class TestRunReplSlashCommands:
    def test_new_resets_conversation(self):
        events = [
            [_ev("RUN_FINISHED", "{}")],
            [_ev("RUN_FINISHED", "{}")],
        ]
        agent = _make_agent(events)
        cfg = ReplConfig(
            agent_name="x",
            render_mode=RenderMode.RAW,
            initial_conv_id="conv-old",
            input_fn=MagicMock(side_effect=["first", "/new", "second", "/exit"]),
        )
        with patch("agentrun_cli._utils.super_agent_repl.STATE_FILE_WRITER"):
            run_repl(agent, cfg)
        calls = agent.invoke_async.await_args_list
        assert calls[0].kwargs["conversation_id"] == "conv-old"
        # After /new, the conv_id got reset. But /new will be BEFORE the write
        # from turn 1 updates it. Actually: the first turn returns new conv-xxx,
        # which overwrites state. Then /new resets to None, so turn 2 uses None.
        assert calls[1].kwargs["conversation_id"] is None

    def test_conv_prints_current_id(self, capsys):
        events = [[_ev("RUN_FINISHED", "{}")]]
        agent = _make_agent(events)
        cfg = ReplConfig(
            agent_name="x",
            render_mode=RenderMode.RAW,
            initial_conv_id="conv-known",
            input_fn=MagicMock(side_effect=["/conv", "/exit"]),
        )
        with patch("agentrun_cli._utils.super_agent_repl.STATE_FILE_WRITER"):
            run_repl(agent, cfg)
        out = capsys.readouterr().out
        assert "conv-known" in out

    def test_help_prints_help_text(self, capsys):
        events = [[_ev("RUN_FINISHED", "{}")]]
        agent = _make_agent(events)
        cfg = ReplConfig(
            agent_name="x",
            render_mode=RenderMode.RAW,
            input_fn=MagicMock(side_effect=["/help", "/exit"]),
        )
        with patch("agentrun_cli._utils.super_agent_repl.STATE_FILE_WRITER"):
            run_repl(agent, cfg)
        out = capsys.readouterr().out
        assert "/exit" in out
        assert "/new" in out

    def test_toggle_raw(self, capsys):
        events = [[_ev("RUN_FINISHED", "{}")]]
        agent = _make_agent(events)
        cfg = ReplConfig(
            agent_name="x",
            render_mode=RenderMode.PRETTY,
            input_fn=MagicMock(side_effect=["/raw", "/exit"]),
        )
        with patch("agentrun_cli._utils.super_agent_repl.STATE_FILE_WRITER"):
            run_repl(agent, cfg)
        out = capsys.readouterr().out
        assert "raw" in out.lower()

    def test_unknown_slash(self, capsys):
        events = [[_ev("RUN_FINISHED", "{}")]]
        agent = _make_agent(events)
        cfg = ReplConfig(
            agent_name="x",
            render_mode=RenderMode.RAW,
            input_fn=MagicMock(side_effect=["/foobar", "/exit"]),
        )
        with patch("agentrun_cli._utils.super_agent_repl.STATE_FILE_WRITER"):
            run_repl(agent, cfg)
        out = capsys.readouterr().out
        assert "unknown" in out.lower()


class TestReplEmptyInput:
    def test_empty_line_ignored(self):
        """Empty input line should not trigger invoke call."""
        agent = _make_agent([])
        cfg = ReplConfig(
            agent_name="x",
            render_mode=RenderMode.RAW,
            input_fn=MagicMock(side_effect=["", "  ", "/exit"]),
        )
        with patch("agentrun_cli._utils.super_agent_repl.STATE_FILE_WRITER"):
            run_repl(agent, cfg)
        assert agent.invoke_async.await_count == 0


class TestReplStateWriteFailure:
    def test_state_writer_exception_warns_but_does_not_crash(self, capsys):
        """STATE_FILE_WRITER error prints warning, does not crash."""
        events = [[_ev("RUN_FINISHED", "{}")]]
        agent = _make_agent(events)
        cfg = ReplConfig(
            agent_name="x",
            render_mode=RenderMode.RAW,
            input_fn=MagicMock(side_effect=["hello", "/exit"]),
        )
        with patch(
            "agentrun_cli._utils.super_agent_repl.STATE_FILE_WRITER",
            side_effect=OSError("disk full"),
        ):
            final = run_repl(agent, cfg)
        # Conversation id from the stream still propagates (state set before write).
        assert final == "conv-xxx"
        captured = capsys.readouterr()
        assert "failed to persist" in captured.err
        assert "disk full" in captured.err
