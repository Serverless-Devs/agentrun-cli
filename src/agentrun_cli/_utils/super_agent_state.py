"""Local state file for super agents.

Tracks ``<agent-name> → last_conversation_id`` so ``ar sa chat`` can resume
the most recent conversation without the user remembering the id.

File path: ``~/.agentrun/super-agent-state.json``

Schema::

    {
      "agents": {
        "<agent-name>": {
          "last_conversation_id": "<conv-id>",
          "last_used_at": "<iso-8601>"
        }
      }
    }
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Optional

from agentrun_cli._utils.config import CONFIG_DIR

STATE_FILE = CONFIG_DIR / "super-agent-state.json"


def read_state() -> dict:
    """Load the state file. Missing or corrupt → empty-state fallback."""
    path = STATE_FILE
    if not path.exists():
        return {"agents": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        _warn(f"super-agent state file corrupt, ignoring: {e}")
        return {"agents": {}}
    if not isinstance(data, dict):
        return {"agents": {}}
    data.setdefault("agents", {})
    return data


def write_state(state: dict) -> None:
    """Persist state. On write failure, log a warning and continue."""
    path = STATE_FILE
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
            f.write("\n")
    except OSError as e:
        _warn(f"failed to write super-agent state: {e}")


def get_last_conv_id(agent_name: str) -> Optional[str]:
    state = read_state()
    entry = state.get("agents", {}).get(agent_name, {})
    return entry.get("last_conversation_id") or None


def set_last_conv_id(agent_name: str, conv_id: str) -> None:
    state = read_state()
    agents = state.setdefault("agents", {})
    agents[agent_name] = {
        "last_conversation_id": conv_id,
        "last_used_at": datetime.now(timezone.utc).isoformat(),
    }
    write_state(state)


def clear_conv_if_matches(agent_name: str, conv_id: str) -> None:
    """If the stored conv_id matches *conv_id*, remove it (no-op otherwise)."""
    state = read_state()
    entry = state.get("agents", {}).get(agent_name)
    if not entry:
        return
    if entry.get("last_conversation_id") == conv_id:
        state["agents"].pop(agent_name, None)
        write_state(state)


def _warn(msg: str) -> None:
    print(f"[warn] {msg}", file=sys.stderr)
