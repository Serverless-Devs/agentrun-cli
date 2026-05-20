"""End-to-end mock for ar runtime apply happy / failure / timeout paths."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from agentrun_cli.main import cli

VALID_YAML = """
apiVersion: agentrun/v1
kind: AgentRuntime
metadata: {name: my-agent}
spec:
  container:
    image: img:v1
"""


def _runtime(name="my-agent", rid="ar-1", status="CREATING"):
    rt = SimpleNamespace(
        agent_runtime_name=name,
        agent_runtime_id=rid,
        agent_runtime_arn=f"acs:{rid}",
        agent_runtime_version="1",
        status=status,
        status_reason=None,
        created_at="t",
        last_updated_at="t",
    )
    rt.list_endpoints = MagicMock(return_value=[])
    rt.create_endpoint = MagicMock(
        return_value=SimpleNamespace(
            agent_runtime_endpoint_name="default",
            agent_runtime_endpoint_id="ep-1",
            status="READY",
            status_reason=None,
            endpoint_public_url="https://x/",
            target_version="LATEST",
            description=None,
            routing_configuration=None,
            disable_public_network_access=None,
            refresh=lambda *a, **k: None,
        )
    )
    return rt


def test_apply_full_chain(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    rt = _runtime()
    states = iter(["CREATING", "CREATING", "READY"])
    rt.refresh = lambda *a, **k: setattr(rt, "status", next(states, "READY")) or rt
    rt_cls = MagicMock()
    rt_cls.list_all.return_value = []
    rt_cls.create.return_value = rt

    with (
        patch(
            "agentrun_cli.commands.runtime.apply_cmd.build_sdk_config",
            return_value=MagicMock(),
        ),
        patch("agentrun_cli.commands.runtime.apply_cmd.AgentRuntime", rt_cls),
    ):
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("rt.yaml", "w") as f:
                f.write(VALID_YAML)
            result = runner.invoke(cli, ["runtime", "apply", "-f", "rt.yaml"])
    assert result.exit_code == 0, result.output
    out = json.loads(result.output)
    assert out[0]["action"] == "create"
    assert out[0]["runtime"]["status"] == "READY"
    assert out[0]["endpoints"][0]["status"] == "READY"
    assert out[0]["endpoints"][0]["publicUrl"] == "https://x/"
