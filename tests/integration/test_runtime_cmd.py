"""Integration tests for the ``ar runtime`` command group.

PR4 covers ``apply`` and ``render``. PR5 adds ``get / list / delete / status``.
PR6 adds an end-to-end happy path that exercises everything in one invocation.

The group is exercised through its own root via a private helper so PR4 can
land before ``main.py`` is wired up in PR6.
"""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import click
from click.testing import CliRunner

from agentrun_cli._utils.cloud_build import CloudBuildError, CloudBuildResult
from agentrun_cli.commands.runtime import runtime_group


def _root():
    """Build a root CLI that mounts only ``runtime`` — keeps the test
    independent of PR6's main.py wiring."""

    @click.group()
    @click.option("--profile", default=None)
    @click.option("--region", default=None)
    @click.option("--output", default="json")
    @click.pass_context
    def root(ctx, profile, region, output):
        ctx.ensure_object(dict)
        ctx.obj["profile"] = profile
        ctx.obj["region"] = region
        ctx.obj["output"] = output

    root.add_command(runtime_group)
    return root


def test_runtime_group_registered():
    result = CliRunner().invoke(_root(), ["runtime", "--help"])
    assert result.exit_code == 0
    assert "apply" in result.output
    assert "cloud-build" in result.output
    assert "render" in result.output


VALID_YAML = """
apiVersion: agentrun/v1
kind: AgentRuntime
metadata:
  name: my-agent
spec:
  container:
    image: img:v1
"""

CLOUD_BUILD_YAML = """
apiVersion: agentrun/v1
kind: AgentRuntime
metadata:
  name: my-agent
spec:
  container:
    image: registry.example.com/ns/app:v1
    cloudBuild:
      dir: .
      setupScript: ""
      baseContainerConfig:
        image: registry.example.com/ns/worker:tag
"""

MULTI_DOC_PARTIAL_CLOUD_BUILD_YAML = (
    CLOUD_BUILD_YAML
    + """
---
apiVersion: agentrun/v1
kind: AgentRuntime
metadata:
  name: plain-agent
spec:
  container:
    image: registry.example.com/ns/plain:v1
"""
)


def test_render_outputs_rendered_input():
    fake_input = MagicMock()
    fake_input.model_dump.return_value = {
        "agentRuntimeName": "my-agent",
        "artifactType": "Container",
        "systemTags": ["x-agentrun-cli"],
    }
    fake_eps = [MagicMock()]
    fake_eps[0].model_dump.return_value = {
        "agentRuntimeEndpointName": "default",
        "targetVersion": "LATEST",
    }
    with (
        patch(
            "agentrun_cli.commands.runtime.render_cmd.to_runtime_create_input",
            return_value=fake_input,
        ),
        patch(
            "agentrun_cli.commands.runtime.render_cmd.to_endpoint_create_inputs",
            return_value=fake_eps,
        ),
    ):
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("rt.yaml", "w") as f:
                f.write(VALID_YAML)
            result = runner.invoke(_root(), ["runtime", "render", "-f", "rt.yaml"])
    assert result.exit_code == 0, result.output
    out = json.loads(result.output)
    assert out[0]["kind"] == "AgentRuntime"
    assert out[0]["name"] == "my-agent"
    assert out[0]["renderedCreateInput"]["systemTags"] == ["x-agentrun-cli"]
    assert out[0]["renderedEndpoints"][0]["agentRuntimeEndpointName"] == "default"
    assert out[0]["cloudBuildPlan"] is None


def test_render_outputs_cloud_build_plan():
    fake_input = MagicMock()
    fake_input.model_dump.return_value = {"agentRuntimeName": "my-agent"}
    with (
        patch(
            "agentrun_cli.commands.runtime.render_cmd.to_runtime_create_input",
            return_value=fake_input,
        ),
        patch(
            "agentrun_cli.commands.runtime.render_cmd.to_endpoint_create_inputs",
            return_value=[],
        ),
    ):
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("rt.yaml", "w") as f:
                f.write(CLOUD_BUILD_YAML)
            result = runner.invoke(_root(), ["runtime", "render", "-f", "rt.yaml"])
    assert result.exit_code == 0, result.output
    out = json.loads(result.output)
    assert out[0]["cloudBuildPlan"]["image"] == "registry.example.com/ns/app:v1"
    assert out[0]["cloudBuildPlan"]["setupScript"] == ""
    assert (
        out[0]["cloudBuildPlan"]["baseContainerConfig"]["image"]
        == "registry.example.com/ns/worker:tag"
    )


def test_cloud_build_command_success():
    result_obj = CloudBuildResult(
        name="my-agent",
        image="registry.example.com/ns/app:v1",
        build_status="completed",
        elapsed_seconds=0.1,
    )
    with (
        patch(
            "agentrun_cli.commands.runtime.cloud_build_cmd.build_sdk_config",
            return_value=MagicMock(),
        ),
        patch(
            "agentrun_cli.commands.runtime.cloud_build_cmd.build_runtime_image",
            return_value=result_obj,
        ) as build_mock,
    ):
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("rt.yaml", "w") as f:
                f.write(CLOUD_BUILD_YAML)
            result = runner.invoke(_root(), ["runtime", "cloud-build", "-f", "rt.yaml"])
    assert result.exit_code == 0, result.output
    out = json.loads(result.output)
    assert out[0]["buildStatus"] == "completed"
    build_mock.assert_called_once()


def test_cloud_build_command_requires_cloud_build_block():
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("rt.yaml", "w") as f:
            f.write(VALID_YAML)
        result = runner.invoke(_root(), ["runtime", "cloud-build", "-f", "rt.yaml"])
    assert result.exit_code == 2


def test_cloud_build_command_prescans_all_docs_before_building():
    result_obj = CloudBuildResult(
        name="my-agent",
        image="registry.example.com/ns/app:v1",
        build_status="completed",
        elapsed_seconds=0.1,
    )
    with (
        patch(
            "agentrun_cli.commands.runtime.cloud_build_cmd.build_sdk_config",
            return_value=MagicMock(),
        ) as cfg_mock,
        patch(
            "agentrun_cli.commands.runtime.cloud_build_cmd.build_runtime_image",
            return_value=result_obj,
        ) as build_mock,
    ):
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("rt.yaml", "w") as f:
                f.write(MULTI_DOC_PARTIAL_CLOUD_BUILD_YAML)
            result = runner.invoke(_root(), ["runtime", "cloud-build", "-f", "rt.yaml"])
    assert result.exit_code == 2
    assert "plain-agent" in result.output
    cfg_mock.assert_not_called()
    build_mock.assert_not_called()


def test_cloud_build_command_no_results_exit_code_2():
    with (
        patch(
            "agentrun_cli.commands.runtime.cloud_build_cmd.build_sdk_config",
            return_value=MagicMock(),
        ),
        patch(
            "agentrun_cli.commands.runtime.cloud_build_cmd.build_runtime_image",
            return_value=None,
        ),
    ):
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("rt.yaml", "w") as f:
                f.write(CLOUD_BUILD_YAML)
            result = runner.invoke(_root(), ["runtime", "cloud-build", "-f", "rt.yaml"])
    assert result.exit_code == 2


def test_cloud_build_invalid_yaml_exit_code_2():
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("bad.yaml", "w") as f:
            f.write(
                "apiVersion: wrong/v1\nkind: AgentRuntime\nmetadata: {name: x}\n"
                "spec: {container: {image: i}}\n"
            )
        result = runner.invoke(_root(), ["runtime", "cloud-build", "-f", "bad.yaml"])
    assert result.exit_code == 2


def test_render_invalid_yaml_exit_code_2():
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("bad.yaml", "w") as f:
            f.write(
                "apiVersion: wrong/v1\nkind: AgentRuntime\nmetadata: {name: x}\n"
                "spec: {container: {image: i}}\n"
            )
        result = runner.invoke(_root(), ["runtime", "render", "-f", "bad.yaml"])
    assert result.exit_code == 2


def _make_runtime(name="my-agent", status="READY", rid="ar-1"):
    return SimpleNamespace(
        agent_runtime_name=name,
        agent_runtime_id=rid,
        agent_runtime_arn=f"acs:{rid}",
        agent_runtime_version="1",
        status=status,
        status_reason=None,
        created_at="t0",
        last_updated_at="t1",
    )


def _make_endpoint(name="default", status="READY", eid="ep-1", url="https://x/"):
    e = SimpleNamespace(
        agent_runtime_endpoint_name=name,
        agent_runtime_endpoint_id=eid,
        status=status,
        status_reason=None,
        endpoint_public_url=url,
        target_version="LATEST",
        description=None,
        routing_configuration=None,
        disable_public_network_access=None,
    )
    e.refresh = lambda *a, **k: e
    return e


def test_apply_create_happy_path(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    # Build a fake SDK Runtime class with the methods the reconciler / state
    # machine touch.
    fake_runtime_cls = MagicMock()
    created = _make_runtime(status="CREATING")
    # After create, ``refresh`` flips to READY on first call:
    refresh_states = iter(["CREATING", "READY"])

    def _refresh(self=None, *a, **k):
        created.status = next(refresh_states, "READY")
        return created

    created.refresh = _refresh

    fake_runtime_cls.list_all.return_value = []
    fake_runtime_cls.create.return_value = created

    created.list_endpoints = MagicMock(return_value=[])
    created.create_endpoint = MagicMock(return_value=_make_endpoint())

    with (
        patch(
            "agentrun_cli.commands.runtime.apply_cmd.build_sdk_config",
            return_value=MagicMock(),
        ),
        patch(
            "agentrun_cli.commands.runtime.apply_cmd.AgentRuntime",
            fake_runtime_cls,
        ),
    ):
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("rt.yaml", "w") as f:
                f.write(VALID_YAML)
            result = runner.invoke(
                _root(),
                ["runtime", "apply", "-f", "rt.yaml", "--no-wait"],
            )
    assert result.exit_code == 0, result.output
    out = json.loads(result.output)
    assert out[0]["action"] == "create"
    assert out[0]["runtime"]["name"] == "my-agent"
    fake_runtime_cls.create.assert_called_once()
    # --no-wait must not touch endpoints — the backend rejects endpoint
    # create while the runtime is CREATING/UPDATING.
    created.create_endpoint.assert_not_called()
    assert out[0]["endpoints"] == []


def test_apply_cloud_build_before_runtime_submit(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    events = []
    fake_runtime_cls = MagicMock()
    created = _make_runtime(status="CREATING")
    created.refresh = lambda *a, **k: created
    created.list_endpoints = MagicMock(return_value=[])
    created.create_endpoint = MagicMock(return_value=_make_endpoint())

    def fake_create(*_args, **_kwargs):
        events.append("runtime")
        return created

    def fake_build(*_args, **_kwargs):
        events.append("build")
        return CloudBuildResult(
            name="my-agent",
            image="registry.example.com/ns/app:v1",
            build_status="completed",
            elapsed_seconds=0.1,
        )

    fake_runtime_cls.list_all.return_value = []
    fake_runtime_cls.create.side_effect = fake_create

    with (
        patch(
            "agentrun_cli.commands.runtime.apply_cmd.build_sdk_config",
            return_value=MagicMock(),
        ),
        patch(
            "agentrun_cli.commands.runtime.apply_cmd.build_runtime_image",
            fake_build,
        ),
        patch(
            "agentrun_cli.commands.runtime.apply_cmd.AgentRuntime",
            fake_runtime_cls,
        ),
    ):
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("rt.yaml", "w") as f:
                f.write(CLOUD_BUILD_YAML)
            result = runner.invoke(
                _root(),
                ["runtime", "apply", "-f", "rt.yaml", "--no-wait"],
            )
    assert result.exit_code == 0, result.output
    assert events == ["build", "runtime"]
    out = json.loads(result.output)
    assert out[0]["cloudBuild"]["buildStatus"] == "completed"


def test_apply_cloud_build_failure_skips_runtime():
    fake_runtime_cls = MagicMock()
    fake_runtime_cls.list_all.return_value = []

    with (
        patch(
            "agentrun_cli.commands.runtime.apply_cmd.build_sdk_config",
            return_value=MagicMock(),
        ),
        patch(
            "agentrun_cli.commands.runtime.apply_cmd.build_runtime_image",
            side_effect=CloudBuildError("build failed"),
        ),
        patch("agentrun_cli.commands.runtime.apply_cmd.AgentRuntime", fake_runtime_cls),
    ):
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("rt.yaml", "w") as f:
                f.write(CLOUD_BUILD_YAML)
            result = runner.invoke(_root(), ["runtime", "apply", "-f", "rt.yaml"])
    assert result.exit_code == 4
    fake_runtime_cls.list_all.assert_not_called()
    fake_runtime_cls.create.assert_not_called()


def test_apply_update_path(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    existing = _make_runtime(status="UPDATING")
    refresh_states = iter(["UPDATING", "READY"])
    existing.refresh = lambda *a, **k: (
        setattr(existing, "status", next(refresh_states, "READY")) or existing
    )
    existing.list_endpoints = MagicMock(return_value=[])
    existing.create_endpoint = MagicMock(return_value=_make_endpoint())

    rt_cls = MagicMock()
    rt_cls.list_all.return_value = [existing]
    rt_cls.update_by_id.return_value = existing

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
            result = runner.invoke(_root(), ["runtime", "apply", "-f", "rt.yaml"])
    assert result.exit_code == 0, result.output
    out = json.loads(result.output)
    assert out[0]["action"] == "update"
    # Default --wait path reconciles endpoints after runtime reaches READY.
    existing.create_endpoint.assert_called_once()


def test_apply_runtime_failed_exits_5(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    rt = _make_runtime(status="CREATE_FAILED")
    rt.status_reason = "image pull backoff"
    rt.refresh = lambda *a, **k: rt
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
            result = runner.invoke(_root(), ["runtime", "apply", "-f", "rt.yaml"])
    assert result.exit_code == 5


def test_apply_timeout_exits_6(monkeypatch):
    import itertools

    monkeypatch.setattr("time.sleep", lambda *_: None)
    rt = _make_runtime(status="CREATING")
    rt.refresh = lambda *a, **k: rt  # never advances
    # apply_cmd.started uses 1 tick; poll_until_final uses 1 for start +
    # >=2 for elapsed checks (first under timeout, second exceeds). Provide
    # an unbounded chain so any extra calls keep returning the timeout value.
    fake_clock = itertools.chain([0.0, 0.0, 0.5, 999.0], itertools.repeat(999.0))
    monkeypatch.setattr("time.monotonic", lambda: next(fake_clock))

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
            result = runner.invoke(
                _root(),
                ["runtime", "apply", "-f", "rt.yaml", "--timeout", "1s"],
            )
    assert result.exit_code == 6


def test_get_runtime():
    rt = _make_runtime()
    rt_cls = MagicMock()
    rt_cls.list_all.return_value = [rt]
    with (
        patch(
            "agentrun_cli.commands.runtime.crud_cmd.build_sdk_config",
            return_value=MagicMock(),
        ),
        patch("agentrun_cli.commands.runtime.crud_cmd.AgentRuntime", rt_cls),
    ):
        result = CliRunner().invoke(_root(), ["runtime", "get", "my-agent"])
    assert result.exit_code == 0, result.output
    out = json.loads(result.output)
    assert out["name"] == "my-agent" and out["status"] == "READY"


def test_get_runtime_not_found_exit_1():
    rt_cls = MagicMock()
    rt_cls.list_all.return_value = []
    with (
        patch(
            "agentrun_cli.commands.runtime.crud_cmd.build_sdk_config",
            return_value=MagicMock(),
        ),
        patch("agentrun_cli.commands.runtime.crud_cmd.AgentRuntime", rt_cls),
    ):
        result = CliRunner().invoke(_root(), ["runtime", "get", "missing"])
    assert result.exit_code == 1


def test_list_runtimes():
    rt_cls = MagicMock()
    rt_cls.list_all.return_value = [
        _make_runtime("a", "READY", "ar-a"),
        _make_runtime("b", "CREATING", "ar-b"),
    ]
    with (
        patch(
            "agentrun_cli.commands.runtime.crud_cmd.build_sdk_config",
            return_value=MagicMock(),
        ),
        patch("agentrun_cli.commands.runtime.crud_cmd.AgentRuntime", rt_cls),
    ):
        result = CliRunner().invoke(_root(), ["runtime", "list"])
    assert result.exit_code == 0
    out = json.loads(result.output)
    assert {r["name"] for r in out} == {"a", "b"}


def test_list_runtimes_created_by_cli_filter():
    """``--created-by-cli`` must filter remote list by SYSTEM_TAG_CLI."""
    rt_cls = MagicMock()
    cli_runtime = _make_runtime("cli-one", "READY", "ar-cli")
    cli_runtime.system_tags = ["x-agentrun-cli"]
    other = _make_runtime("manual", "READY", "ar-m")
    other.system_tags = ["something-else"]
    rt_cls.list_all.return_value = [cli_runtime, other]
    with (
        patch(
            "agentrun_cli.commands.runtime.crud_cmd.build_sdk_config",
            return_value=MagicMock(),
        ),
        patch("agentrun_cli.commands.runtime.crud_cmd.AgentRuntime", rt_cls),
    ):
        result = CliRunner().invoke(
            _root(),
            ["runtime", "list", "--created-by-cli"],
        )
    assert result.exit_code == 0
    out = json.loads(result.output)
    assert {r["name"] for r in out} == {"cli-one"}


def test_delete_idempotent_when_missing():
    rt_cls = MagicMock()
    rt_cls.list_all.return_value = []
    with (
        patch(
            "agentrun_cli.commands.runtime.delete_cmd.build_sdk_config",
            return_value=MagicMock(),
        ),
        patch("agentrun_cli.commands.runtime.delete_cmd.AgentRuntime", rt_cls),
    ):
        result = CliRunner().invoke(
            _root(),
            ["runtime", "delete", "missing", "--yes"],
        )
    assert result.exit_code == 1  # ResourceNotFound


def test_delete_happy_path(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    rt = _make_runtime(status="DELETING")
    states = iter([Exception("simulated NotFound")])

    def _refresh(*a, **k):
        try:
            raise next(states)
        except StopIteration:
            return rt

    rt.refresh = _refresh
    rt.delete = MagicMock()

    rt_cls = MagicMock()
    rt_cls.list_all.return_value = [rt]

    # The SystemExit module needs an is_not_found predicate. The integration
    # test points the predicate at the simulated exception's message.
    with (
        patch(
            "agentrun_cli.commands.runtime.delete_cmd.build_sdk_config",
            return_value=MagicMock(),
        ),
        patch("agentrun_cli.commands.runtime.delete_cmd.AgentRuntime", rt_cls),
        patch(
            "agentrun_cli.commands.runtime.delete_cmd._is_not_found",
            lambda e: "NotFound" in str(e),
        ),
    ):
        result = CliRunner().invoke(
            _root(),
            ["runtime", "delete", "my-agent", "--yes"],
        )
    assert result.exit_code == 0, result.output
    rt.delete.assert_called_once()


def test_status_no_wait_returns_current():
    rt = _make_runtime(status="CREATING")
    rt_cls = MagicMock()
    rt_cls.list_all.return_value = [rt]
    with (
        patch(
            "agentrun_cli.commands.runtime.status_cmd.build_sdk_config",
            return_value=MagicMock(),
        ),
        patch("agentrun_cli.commands.runtime.status_cmd.AgentRuntime", rt_cls),
    ):
        result = CliRunner().invoke(_root(), ["runtime", "status", "my-agent"])
    assert result.exit_code == 0
    out = json.loads(result.output)
    assert out["status"] == "CREATING"


def test_status_wait_until_ready(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    rt = _make_runtime(status="CREATING")
    states = iter(["CREATING", "READY"])
    rt.refresh = lambda *a, **k: setattr(rt, "status", next(states, "READY")) or rt
    rt_cls = MagicMock()
    rt_cls.list_all.return_value = [rt]
    with (
        patch(
            "agentrun_cli.commands.runtime.status_cmd.build_sdk_config",
            return_value=MagicMock(),
        ),
        patch("agentrun_cli.commands.runtime.status_cmd.AgentRuntime", rt_cls),
    ):
        result = CliRunner().invoke(
            _root(),
            ["runtime", "status", "my-agent", "--wait"],
        )
    assert result.exit_code == 0
    out = json.loads(result.output)
    assert out["status"] == "READY"


from agentrun_cli.main import cli as real_cli  # noqa: E402


def test_real_cli_exposes_runtime_group():
    result = CliRunner().invoke(real_cli, ["runtime", "--help"])
    assert result.exit_code == 0
    assert "apply" in result.output
    assert "cloud-build" in result.output


def test_real_cli_exposes_rt_alias():
    result = CliRunner().invoke(real_cli, ["rt", "--help"])
    assert result.exit_code == 0
    assert "apply" in result.output
