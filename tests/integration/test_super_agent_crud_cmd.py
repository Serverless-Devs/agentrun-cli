"""Integration tests for ``ar super-agent`` CRUD commands."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from agentrun_cli.main import cli

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_agent(**overrides):
    defaults = {
        "name": "my-agent",
        "description": None,
        "prompt": "You are helpful",
        "agents": [],
        "tools": [],
        "skills": [],
        "sandboxes": [],
        "workspaces": [],
        "model_service_name": "svc-tongyi",
        "model_name": "qwen-max",
        "agent_runtime_id": "ar-xxx",
        "arn": "acs:agentrun:...",
        "status": "READY",
        "external_endpoint": "https://...",
        "created_at": "2026-04-16T00:00:00Z",
        "last_updated_at": "2026-04-16T00:00:00Z",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _patch_client():
    client = MagicMock()
    return client, patch(
        "agentrun_cli.commands.super_agent.crud_cmd.SuperAgentClient",
        return_value=client,
    )


def _patch_sdk_cfg():
    return patch(
        "agentrun_cli.commands.super_agent.crud_cmd.build_sdk_config",
        return_value=MagicMock(),
    )


# ---------------------------------------------------------------------------
# Help-text
# ---------------------------------------------------------------------------


class TestSuperAgentHelp:
    def test_super_agent_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["super-agent", "--help"])
        assert result.exit_code == 0
        assert "Manage super agents" in result.output

    def test_super_agent_alias_sa(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["sa", "--help"])
        assert result.exit_code == 0
        assert "Manage super agents" in result.output


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


class TestSuperAgentCreate:
    def test_create_minimal(self):
        client, patcher = _patch_client()
        client.create.return_value = _make_agent(name="new-agent")
        with _patch_sdk_cfg(), patcher:
            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "sa",
                    "create",
                    "--name",
                    "new-agent",
                    "--prompt",
                    "You are helpful",
                    "--model-service",
                    "svc-tongyi",
                    "--model",
                    "qwen-max",
                ],
            )
        assert result.exit_code == 0, result.output
        out = json.loads(result.output)
        assert out["name"] == "new-agent"
        kwargs = client.create.call_args.kwargs
        assert kwargs["name"] == "new-agent"
        assert kwargs["prompt"] == "You are helpful"
        assert kwargs["model_service_name"] == "svc-tongyi"
        assert kwargs["model_name"] == "qwen-max"

    def test_create_with_tools_and_skills(self):
        client, patcher = _patch_client()
        client.create.return_value = _make_agent(
            name="researcher",
            tools=["web-search", "calc"],
            skills=["data-analyzer"],
        )
        with _patch_sdk_cfg(), patcher:
            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "sa",
                    "create",
                    "--name",
                    "researcher",
                    "--tool",
                    "web-search",
                    "--tool",
                    "calc",
                    "--skill",
                    "data-analyzer",
                ],
            )
        assert result.exit_code == 0, result.output
        kwargs = client.create.call_args.kwargs
        assert kwargs["tools"] == ["web-search", "calc"]
        assert kwargs["skills"] == ["data-analyzer"]

    def test_create_with_description(self):
        client, patcher = _patch_client()
        client.create.return_value = _make_agent(
            name="x",
            description="desc",
        )
        with _patch_sdk_cfg(), patcher:
            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "sa",
                    "create",
                    "--name",
                    "x",
                    "--description",
                    "desc",
                ],
            )
        assert result.exit_code == 0, result.output
        kwargs = client.create.call_args.kwargs
        assert kwargs["description"] == "desc"


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------


class TestSuperAgentGet:
    def test_get_existing(self):
        client, patcher = _patch_client()
        client.get.return_value = _make_agent(name="my-agent", status="READY")
        with _patch_sdk_cfg(), patcher:
            runner = CliRunner()
            result = runner.invoke(cli, ["sa", "get", "my-agent"])
        assert result.exit_code == 0, result.output
        out = json.loads(result.output)
        assert out["name"] == "my-agent"
        assert out["status"] == "READY"
        client.get.assert_called_once_with("my-agent")

    def test_get_not_found(self):
        client, patcher = _patch_client()
        client.get.side_effect = ValueError("Super agent 'nope' not found")
        with _patch_sdk_cfg(), patcher:
            runner = CliRunner()
            result = runner.invoke(cli, ["sa", "get", "nope"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


class TestSuperAgentList:
    def test_list_default(self):
        client, patcher = _patch_client()
        client.list.return_value = [
            _make_agent(name="a1"),
            _make_agent(name="a2"),
        ]
        with _patch_sdk_cfg(), patcher:
            runner = CliRunner()
            result = runner.invoke(cli, ["sa", "list"])
        assert result.exit_code == 0, result.output
        out = json.loads(result.output)
        assert len(out) == 2
        assert out[0]["name"] == "a1"
        client.list.assert_called_once()

    def test_list_all(self):
        client, patcher = _patch_client()
        client.list_all.return_value = [_make_agent(name="a1")]
        with _patch_sdk_cfg(), patcher:
            runner = CliRunner()
            result = runner.invoke(cli, ["sa", "list", "--all"])
        assert result.exit_code == 0, result.output
        out = json.loads(result.output)
        assert len(out) == 1
        client.list_all.assert_called_once()

    def test_list_pagination(self):
        client, patcher = _patch_client()
        client.list.return_value = []
        with _patch_sdk_cfg(), patcher:
            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "sa",
                    "list",
                    "--page",
                    "2",
                    "--page-size",
                    "5",
                ],
            )
        assert result.exit_code == 0
        kwargs = client.list.call_args.kwargs
        assert kwargs["page_number"] == 2
        assert kwargs["page_size"] == 5


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


class TestSuperAgentUpdate:
    def test_update_prompt(self):
        client, patcher = _patch_client()
        client.update.return_value = _make_agent(
            name="my-agent",
            prompt="new prompt",
        )
        with _patch_sdk_cfg(), patcher:
            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "sa",
                    "update",
                    "my-agent",
                    "--prompt",
                    "new prompt",
                ],
            )
        assert result.exit_code == 0, result.output
        kwargs = client.update.call_args.kwargs
        assert kwargs["prompt"] == "new prompt"
        assert "tools" not in kwargs

    def test_update_replace_tools(self):
        client, patcher = _patch_client()
        client.update.return_value = _make_agent(
            name="my-agent",
            tools=["a", "b"],
        )
        with _patch_sdk_cfg(), patcher:
            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "sa",
                    "update",
                    "my-agent",
                    "--tool",
                    "a",
                    "--tool",
                    "b",
                ],
            )
        assert result.exit_code == 0, result.output
        kwargs = client.update.call_args.kwargs
        assert kwargs["tools"] == ["a", "b"]

    def test_update_clear_tools(self):
        client, patcher = _patch_client()
        client.update.return_value = _make_agent(
            name="my-agent",
            tools=[],
        )
        with _patch_sdk_cfg(), patcher:
            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "sa",
                    "update",
                    "my-agent",
                    "--clear-tools",
                ],
            )
        assert result.exit_code == 0, result.output
        kwargs = client.update.call_args.kwargs
        assert kwargs["tools"] == []

    def test_update_clear_all_list_fields(self):
        client, patcher = _patch_client()
        client.update.return_value = _make_agent(name="my-agent")
        with _patch_sdk_cfg(), patcher:
            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "sa",
                    "update",
                    "my-agent",
                    "--clear-tools",
                    "--clear-skills",
                    "--clear-sandboxes",
                    "--clear-workspaces",
                    "--clear-sub-agents",
                ],
            )
        assert result.exit_code == 0, result.output
        kwargs = client.update.call_args.kwargs
        assert kwargs["tools"] == []
        assert kwargs["skills"] == []
        assert kwargs["sandboxes"] == []
        assert kwargs["workspaces"] == []
        assert kwargs["agents"] == []

    def test_update_conflict_tool_and_clear(self):
        client, patcher = _patch_client()
        with _patch_sdk_cfg(), patcher:
            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "sa",
                    "update",
                    "my-agent",
                    "--tool",
                    "a",
                    "--clear-tools",
                ],
            )
        assert result.exit_code != 0
        combined = result.output
        assert "cannot" in combined.lower() or "conflict" in combined.lower()

    def test_update_model(self):
        client, patcher = _patch_client()
        client.update.return_value = _make_agent(name="my-agent")
        with _patch_sdk_cfg(), patcher:
            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "sa",
                    "update",
                    "my-agent",
                    "--model-service",
                    "svc-b",
                    "--model",
                    "mb",
                ],
            )
        assert result.exit_code == 0, result.output
        kwargs = client.update.call_args.kwargs
        assert kwargs["model_service_name"] == "svc-b"
        assert kwargs["model_name"] == "mb"


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


class TestSuperAgentDelete:
    def test_delete(self):
        client, patcher = _patch_client()
        client.delete.return_value = None
        with _patch_sdk_cfg(), patcher:
            runner = CliRunner()
            result = runner.invoke(cli, ["sa", "delete", "my-agent"])
        assert result.exit_code == 0, result.output
        out = json.loads(result.output)
        assert out["name"] == "my-agent"
        assert out["deleted"] is True
        client.delete.assert_called_once_with("my-agent")
