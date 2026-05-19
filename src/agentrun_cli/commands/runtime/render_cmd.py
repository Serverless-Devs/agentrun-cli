"""``ar runtime render`` — validate YAML and dump the SDK input that would be sent."""

import click

from agentrun_cli._utils.agentruntime_yaml import (
    YamlSchemaError,
    parse_yaml_file,
)
from agentrun_cli._utils.error import EXIT_BAD_INPUT, handle_errors
from agentrun_cli._utils.output import echo_error, format_output

# Re-exported for tests/monkeypatching:
from agentrun_cli._utils.runtime_render import (
    to_endpoint_create_inputs,
    to_runtime_create_input,
)

__all__ = ["render_cmd", "to_runtime_create_input", "to_endpoint_create_inputs"]


def _parse_file(path):
    try:
        return parse_yaml_file(path)
    except YamlSchemaError as exc:
        echo_error("InvalidYaml", str(exc))
        raise SystemExit(EXIT_BAD_INPUT) from exc


@click.command(
    "render",
    help=(
        "Validate a YAML file and print the SDK create-input that would be "
        "sent — no server calls."
    ),
)
@click.option(
    "-f", "--file", "file_path", required=True,
    help="YAML file path (supports multi-document).",
)
@click.pass_context
@handle_errors
def render_cmd(ctx, file_path):
    docs = _parse_file(file_path)
    results = []
    for parsed in docs:
        rt_input = to_runtime_create_input(parsed)
        ep_inputs = to_endpoint_create_inputs(parsed)
        results.append({
            "kind": "AgentRuntime",
            "name": parsed.name,
            "renderedCreateInput": (
                rt_input.model_dump() if hasattr(rt_input, "model_dump") else rt_input
            ),
            "renderedEndpoints": [
                ei.model_dump() if hasattr(ei, "model_dump") else ei
                for ei in ep_inputs
            ],
        })
    format_output(ctx, results)
