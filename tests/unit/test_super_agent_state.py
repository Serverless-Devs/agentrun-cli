"""Unit tests for super_agent_state local file."""

import json
from unittest.mock import patch


class TestSuperAgentState:

    def test_read_empty_when_missing(self, tmp_path):
        state_file = tmp_path / "state.json"
        with patch(
            "agentrun_cli._utils.super_agent_state.STATE_FILE", state_file
        ):
            from agentrun_cli._utils.super_agent_state import read_state
            assert read_state() == {"agents": {}}

    def test_write_and_read(self, tmp_path):
        state_file = tmp_path / "state.json"
        with patch(
            "agentrun_cli._utils.super_agent_state.STATE_FILE", state_file
        ):
            from agentrun_cli._utils.super_agent_state import (
                read_state,
                write_state,
            )
            write_state({"agents": {"a": {"last_conversation_id": "c1"}}})
            got = read_state()
            assert got["agents"]["a"]["last_conversation_id"] == "c1"

    def test_get_last_conv_missing(self, tmp_path):
        state_file = tmp_path / "state.json"
        with patch(
            "agentrun_cli._utils.super_agent_state.STATE_FILE", state_file
        ):
            from agentrun_cli._utils.super_agent_state import get_last_conv_id
            assert get_last_conv_id("nope") is None

    def test_set_last_conv_then_get(self, tmp_path):
        state_file = tmp_path / "state.json"
        with patch(
            "agentrun_cli._utils.super_agent_state.STATE_FILE", state_file
        ):
            from agentrun_cli._utils.super_agent_state import (
                get_last_conv_id,
                set_last_conv_id,
            )
            set_last_conv_id("my-agent", "conv-xxx")
            assert get_last_conv_id("my-agent") == "conv-xxx"

    def test_clear_conv_if_matches(self, tmp_path):
        state_file = tmp_path / "state.json"
        with patch(
            "agentrun_cli._utils.super_agent_state.STATE_FILE", state_file
        ):
            from agentrun_cli._utils.super_agent_state import (
                clear_conv_if_matches,
                get_last_conv_id,
                set_last_conv_id,
            )
            set_last_conv_id("my-agent", "conv-xxx")
            clear_conv_if_matches("my-agent", "conv-other")
            assert get_last_conv_id("my-agent") == "conv-xxx"
            clear_conv_if_matches("my-agent", "conv-xxx")
            assert get_last_conv_id("my-agent") is None

    def test_clear_conv_no_entry(self, tmp_path):
        state_file = tmp_path / "state.json"
        with patch(
            "agentrun_cli._utils.super_agent_state.STATE_FILE", state_file
        ):
            from agentrun_cli._utils.super_agent_state import (
                clear_conv_if_matches,
            )
            # Should not raise
            clear_conv_if_matches("never-saved", "any-conv")

    def test_corrupt_file_tolerated(self, tmp_path, capsys):
        state_file = tmp_path / "state.json"
        state_file.write_text("not json")
        with patch(
            "agentrun_cli._utils.super_agent_state.STATE_FILE", state_file
        ):
            from agentrun_cli._utils.super_agent_state import read_state
            got = read_state()
            assert got == {"agents": {}}
            err = capsys.readouterr().err
            assert "warn" in err.lower() or "corrupt" in err.lower()

    def test_non_dict_json_tolerated(self, tmp_path):
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps(["not a dict"]))
        with patch(
            "agentrun_cli._utils.super_agent_state.STATE_FILE", state_file
        ):
            from agentrun_cli._utils.super_agent_state import read_state
            assert read_state() == {"agents": {}}
