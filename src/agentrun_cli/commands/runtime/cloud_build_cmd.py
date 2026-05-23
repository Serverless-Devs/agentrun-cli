"""Build Agent Runtime images in the cloud from YAML."""

from __future__ import annotations

import sys

import click

from agentrun_cli._utils.agentruntime_yaml import (
    YamlSchemaError,
    parse_yaml_file,
)
from agentrun_cli._utils.cloud_build import (
    build_runtime_image,
    load_dotenv,
    serialize_cloud_build_result,
)
from agentrun_cli._utils.config import build_sdk_config
from agentrun_cli._utils.error import EXIT_BAD_INPUT, handle_errors
from agentrun_cli._utils.output import echo_error, format_output
from agentrun_cli.commands.runtime._helpers import ctx_cfg


def _parse_file(path: str):
    """Parse a runtime YAML file.

    Args:
        path: YAML file path.
    """
    try:
        return parse_yaml_file(path)
    except YamlSchemaError as exc:
        echo_error("InvalidYaml", str(exc))
        raise SystemExit(EXIT_BAD_INPUT) from exc


@click.command(
    "cloud-build",
    help="Build Agent Runtime images in the cloud from YAML.",
)
@click.option(
    "-f",
    "--file",
    "file_path",
    required=True,
    help="YAML file path (supports multi-document).",
)
@click.pass_context
@handle_errors
def cloud_build_cmd(ctx, file_path):
    load_dotenv()
    profile, region = ctx_cfg(ctx)
    cfg = build_sdk_config(profile_name=profile, region=region)
    docs = _parse_file(file_path)

    results = []
    for parsed in docs:
        if parsed.container.cloud_build is None:
            echo_error(
                "InvalidYaml",
                f"runtime {parsed.name!r} does not define spec.container.cloudBuild.",
            )
            raise SystemExit(EXIT_BAD_INPUT)
        result = build_runtime_image(parsed, cfg)
        if result is None:
            continue
        results.append(serialize_cloud_build_result(result))

    if not results:
        echo_error("InvalidYaml", "No spec.container.cloudBuild blocks found.")
        raise SystemExit(EXIT_BAD_INPUT)

    if sys.stderr.isatty():
        for item in results:
            sys.stderr.write(
                f"[runtime {item['name']}] cloudBuild={item['buildStatus']} "
                f"image={item['image']}\n"
            )
    format_output(ctx, results, quiet_field="image")


__all__ = ["cloud_build_cmd"]
