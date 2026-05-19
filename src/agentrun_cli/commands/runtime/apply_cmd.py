"""``ar runtime apply`` — declarative create-or-update."""

from __future__ import annotations

import sys
import time

import click

from agentrun_cli._utils.agentruntime_yaml import (
    YamlSchemaError,
    parse_yaml_file,
)
from agentrun_cli._utils.config import build_sdk_config
from agentrun_cli._utils.error import EXIT_BAD_INPUT, handle_errors
from agentrun_cli._utils.output import echo_error, format_output
from agentrun_cli._utils.runtime_constants import (
    DEFAULT_APPLY_TIMEOUT_SECONDS,
    ENDPOINT_POLL_CONCURRENCY,
)
from agentrun_cli._utils.runtime_reconciler import (
    reconcile_endpoints,
    reconcile_runtime,
)
from agentrun_cli._utils.runtime_state import (
    PollConfig,
    poll_many_parallel,
    poll_until_final,
)
from agentrun_cli.commands.runtime._helpers import (
    ctx_cfg,
    parse_duration,
    serialize_endpoint,
    serialize_runtime,
)

# Re-exported for monkeypatching in integration tests:
AgentRuntime = None


def _lazy_sdk():
    """Import the SDK only when the command actually runs."""
    global AgentRuntime
    if AgentRuntime is None:
        from agentrun.agent_runtime import AgentRuntime as _AR
        AgentRuntime = _AR
    return AgentRuntime


def _parse(path):
    try:
        return parse_yaml_file(path)
    except YamlSchemaError as exc:
        echo_error("InvalidYaml", str(exc))
        raise SystemExit(EXIT_BAD_INPUT) from exc


def _progress(stream, parsed, runtime, elapsed):
    """Best-effort stderr progress; silent when stderr is not a TTY."""
    if not stream.isatty():
        return
    stream.write(
        f"[runtime {parsed.name}] status={getattr(runtime, 'status', None)} "
        f"({elapsed:.1f}s)\n"
    )


@click.command(
    "apply",
    help=(
        "Create or update an Agent Runtime declaratively from YAML. "
        "By default waits until the runtime (and its endpoints) reach a "
        "terminal status."
    ),
)
@click.option(
    "-f", "--file", "file_path", required=True,
    help="YAML file path (supports multi-document).",
)
@click.option(
    "--wait/--no-wait", default=True, show_default=True,
    help="Poll until the runtime + endpoints reach a final status.",
)
@click.option(
    "--timeout", default="10m", show_default=True,
    help="Polling timeout (e.g. 600s, 10m, 1h).",
)
@click.option(
    "--prune-endpoints/--no-prune-endpoints", default=True, show_default=True,
    help="Delete endpoints that exist remotely but are absent from the YAML.",
)
@click.pass_context
@handle_errors
def apply_cmd(ctx, file_path, wait, timeout, prune_endpoints):
    runtime_cls = _lazy_sdk()
    profile, region = ctx_cfg(ctx)
    build_sdk_config(profile_name=profile, region=region)

    docs = _parse(file_path)
    timeout_seconds = parse_duration(timeout) or DEFAULT_APPLY_TIMEOUT_SECONDS
    poll_cfg = PollConfig(timeout=float(timeout_seconds))

    results = []
    for parsed in docs:
        started = time.monotonic()
        rt_res = reconcile_runtime(parsed, client=runtime_cls)
        runtime = rt_res.runtime

        if wait:
            poll_until_final(
                runtime, resource_kind="AgentRuntime", cfg=poll_cfg,
                on_tick=lambda r, e, p=parsed: _progress(sys.stderr, p, r, e),
            )

        ep_actions = reconcile_endpoints(
            runtime, desired=parsed.endpoints, prune=prune_endpoints,
        )

        if wait:
            in_flight = [
                a.endpoint for a in ep_actions
                if a.action in ("create", "update") and a.endpoint is not None
            ]
            poll_many_parallel(
                in_flight, resource_kind="AgentRuntimeEndpoint",
                cfg=poll_cfg, concurrency=ENDPOINT_POLL_CONCURRENCY,
                on_tick=lambda r, e, p=parsed: _progress(sys.stderr, p, r, e),
            )

        results.append({
            "action": rt_res.action,
            "runtime": serialize_runtime(runtime),
            "endpoints": [
                {**serialize_endpoint(a.endpoint or _empty_ep(a.name)),
                 "action": a.action}
                for a in ep_actions
            ],
            "elapsedSeconds": round(time.monotonic() - started, 3),
        })

    format_output(ctx, results, quiet_field="name")


def _empty_ep(name):
    class _E:
        agent_runtime_endpoint_name = name
        agent_runtime_endpoint_id = None
        status = None
        status_reason = None
        endpoint_public_url = None
        target_version = None
    return _E()
