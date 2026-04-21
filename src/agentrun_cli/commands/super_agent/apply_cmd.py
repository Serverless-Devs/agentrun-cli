"""``ar sa apply`` and ``ar sa render`` — declarative deployment."""

import click

from agentrun_cli._utils.config import build_sdk_config
from agentrun_cli._utils.error import handle_errors
from agentrun_cli._utils.output import format_output
from agentrun_cli._utils.super_agent_yaml import (
    ParsedSuperAgent,
    YamlSchemaError,
    parse_yaml_file,
)
from agentrun_cli.commands.super_agent._helpers import ctx_cfg

SuperAgentClient = None
to_create_input = None


def _lazy_imports():
    global SuperAgentClient, to_create_input
    if SuperAgentClient is None:
        from agentrun.super_agent import SuperAgentClient as _Cls
        SuperAgentClient = _Cls
    if to_create_input is None:
        from agentrun.super_agent.api.control import (
            to_create_input as _tci,
        )
        to_create_input = _tci
    return SuperAgentClient, to_create_input


def _parse_file(path: str):
    try:
        return parse_yaml_file(path)
    except YamlSchemaError as e:
        raise click.UsageError(str(e))


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------

@click.command(
    "render",
    help="Render a YAML file to the input that would be sent to the server "
         "(no API call).",
)
@click.option("-f", "--file", "file_path", required=True,
              help="YAML file path (supports multi-document).")
@click.pass_context
@handle_errors
def render_cmd(ctx, file_path):
    _, tci = _lazy_imports()
    profile, region = ctx_cfg(ctx)
    cfg = build_sdk_config(profile_name=profile, region=region)

    docs = _parse_file(file_path)
    results = []
    for d in docs:
        rt_input = tci(
            d.name,
            description=d.description,
            prompt=d.prompt,
            agents=d.sub_agents,
            tools=d.tools,
            skills=d.skills,
            sandboxes=d.sandboxes,
            workspaces=d.workspaces,
            model_service_name=d.model_service_name,
            model_name=d.model_name,
            cfg=cfg,
        )
        rendered = (
            rt_input.model_dump()
            if hasattr(rt_input, "model_dump")
            else rt_input
        )
        results.append({
            "kind": "SuperAgent",
            "name": d.name,
            "rendered_create_input": rendered,
        })
    format_output(ctx, results)


# ---------------------------------------------------------------------------
# apply
# ---------------------------------------------------------------------------

def _agent_exists(client, name: str) -> bool:
    try:
        client.get(name)
        return True
    except Exception:
        return False


def _apply_one(client, doc: ParsedSuperAgent) -> dict:
    kwargs = dict(
        description=doc.description,
        prompt=doc.prompt,
        agents=doc.sub_agents,
        tools=doc.tools,
        skills=doc.skills,
        sandboxes=doc.sandboxes,
        workspaces=doc.workspaces,
        model_service_name=doc.model_service_name,
        model_name=doc.model_name,
    )
    if _agent_exists(client, doc.name):
        agent = client.update(doc.name, **kwargs)
        return {
            "kind": "SuperAgent",
            "name": doc.name,
            "action": "updated",
            "status": getattr(agent, "status", ""),
            "agent_runtime_id": getattr(agent, "agent_runtime_id", ""),
        }
    agent = client.create(name=doc.name, **kwargs)
    return {
        "kind": "SuperAgent",
        "name": doc.name,
        "action": "created",
        "status": getattr(agent, "status", ""),
        "agent_runtime_id": getattr(agent, "agent_runtime_id", ""),
    }


@click.command(
    "apply",
    help="Create or update super agents declaratively from YAML.",
)
@click.option("-f", "--file", "file_path", required=True,
              help="YAML file path (supports multi-document).")
@click.option("--dry-run", is_flag=True, default=False,
              help="Validate and render without calling the server.")
@click.pass_context
@handle_errors
def apply_cmd(ctx, file_path, dry_run):
    SAClient, tci = _lazy_imports()
    profile, region = ctx_cfg(ctx)
    cfg = build_sdk_config(profile_name=profile, region=region)

    docs = _parse_file(file_path)

    if dry_run:
        results = []
        for d in docs:
            rt_input = tci(
                d.name,
                description=d.description,
                prompt=d.prompt,
                agents=d.sub_agents,
                tools=d.tools,
                skills=d.skills,
                sandboxes=d.sandboxes,
                workspaces=d.workspaces,
                model_service_name=d.model_service_name,
                model_name=d.model_name,
                cfg=cfg,
            )
            rendered = (
                rt_input.model_dump()
                if hasattr(rt_input, "model_dump")
                else rt_input
            )
            results.append({
                "kind": "SuperAgent",
                "name": d.name,
                "action": "dry-run",
                "rendered_create_input": rendered,
            })
        format_output(ctx, results)
        return

    client = SAClient(config=cfg)
    results = [_apply_one(client, d) for d in docs]
    format_output(ctx, results)
