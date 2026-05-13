"""CRUD commands for super agents: create / get / list / update / delete.

All methods use the synchronous SDK methods.
"""

import click

from agentrun_cli._utils.config import build_sdk_config
from agentrun_cli._utils.error import handle_errors
from agentrun_cli._utils.output import format_output
from agentrun_cli.commands.super_agent._helpers import (
    ctx_cfg,
    serialize_super_agent,
)

# Lazy import target; actual import happens inside each function.
# Kept as None at module level so tests can `patch` the symbol.
SuperAgentClient = None


def _get_client_cls():
    """Import SuperAgentClient lazily to keep CLI startup fast."""
    global SuperAgentClient
    if SuperAgentClient is None:
        from agentrun.super_agent import SuperAgentClient as _Cls

        SuperAgentClient = _Cls
    return SuperAgentClient


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


@click.command("create", help="Create a super agent.")
@click.option("--name", required=True, help="Super agent name (globally unique).")
@click.option("--description", default=None, help="Human-readable description.")
@click.option("--prompt", "-p", default=None, help="System prompt for the agent.")
@click.option("--model-service", default=None, help="Name of the ModelService to use.")
@click.option("--model", default=None, help="Model name within the ModelService.")
@click.option("--tool", "tools", multiple=True, help="Tool name (repeatable).")
@click.option("--skill", "skills", multiple=True, help="Skill name (repeatable).")
@click.option(
    "--sandbox", "sandboxes", multiple=True, help="Sandbox name (repeatable)."
)
@click.option(
    "--workspace", "workspaces", multiple=True, help="Workspace name (repeatable)."
)
@click.option(
    "--sub-agent", "sub_agents", multiple=True, help="Sub-agent name (repeatable)."
)
@click.pass_context
@handle_errors
def create_cmd(
    ctx,
    name,
    description,
    prompt,
    model_service,
    model,
    tools,
    skills,
    sandboxes,
    workspaces,
    sub_agents,
):
    """Create a super agent."""
    profile, region = ctx_cfg(ctx)
    cfg = build_sdk_config(profile_name=profile, region=region)
    client = _get_client_cls()(config=cfg)
    agent = client.create(
        name=name,
        description=description,
        prompt=prompt,
        model_service_name=model_service,
        model_name=model,
        tools=list(tools),
        skills=list(skills),
        sandboxes=list(sandboxes),
        workspaces=list(workspaces),
        agents=list(sub_agents),
    )
    format_output(ctx, serialize_super_agent(agent), quiet_field="name")


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------


@click.command("get", help="Get a super agent by name.")
@click.argument("name")
@click.pass_context
@handle_errors
def get_cmd(ctx, name):
    """Get a super agent by name."""
    profile, region = ctx_cfg(ctx)
    cfg = build_sdk_config(profile_name=profile, region=region)
    client = _get_client_cls()(config=cfg)
    agent = client.get(name)
    format_output(ctx, serialize_super_agent(agent), quiet_field="name")


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


@click.command("list", help="List super agents.")
@click.option("--page", type=int, default=1, help="Page number.")
@click.option("--page-size", type=int, default=20, help="Page size.")
@click.option(
    "--all",
    "all_pages",
    is_flag=True,
    default=False,
    help="Fetch all pages automatically.",
)
@click.pass_context
@handle_errors
def list_cmd(ctx, page, page_size, all_pages):
    """List super agents."""
    profile, region = ctx_cfg(ctx)
    cfg = build_sdk_config(profile_name=profile, region=region)
    client = _get_client_cls()(config=cfg)
    if all_pages:
        agents = client.list_all()
    else:
        agents = client.list(page_number=page, page_size=page_size)
    rows = [serialize_super_agent(a) for a in agents]
    format_output(ctx, rows)


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------

_LIST_FIELDS = [
    # (cli_kwarg, sdk_kwarg, clear_flag_name)
    ("tools", "tools", "--clear-tools"),
    ("skills", "skills", "--clear-skills"),
    ("sandboxes", "sandboxes", "--clear-sandboxes"),
    ("workspaces", "workspaces", "--clear-workspaces"),
    ("sub_agents", "agents", "--clear-sub-agents"),
]


@click.command("update", help="Update a super agent (partial update).")
@click.argument("name")
@click.option("--description", default=None)
@click.option("--prompt", "-p", default=None)
@click.option("--model-service", default=None)
@click.option("--model", default=None)
@click.option("--tool", "tools", multiple=True)
@click.option("--skill", "skills", multiple=True)
@click.option("--sandbox", "sandboxes", multiple=True)
@click.option("--workspace", "workspaces", multiple=True)
@click.option("--sub-agent", "sub_agents", multiple=True)
@click.option("--clear-tools", is_flag=True, default=False)
@click.option("--clear-skills", is_flag=True, default=False)
@click.option("--clear-sandboxes", is_flag=True, default=False)
@click.option("--clear-workspaces", is_flag=True, default=False)
@click.option("--clear-sub-agents", is_flag=True, default=False)
@click.pass_context
@handle_errors
def update_cmd(
    ctx,
    name,
    description,
    prompt,
    model_service,
    model,
    tools,
    skills,
    sandboxes,
    workspaces,
    sub_agents,
    clear_tools,
    clear_skills,
    clear_sandboxes,
    clear_workspaces,
    clear_sub_agents,
):
    """Update a super agent; only fields explicitly passed are changed."""
    clear_map = {
        "tools": clear_tools,
        "skills": clear_skills,
        "sandboxes": clear_sandboxes,
        "workspaces": clear_workspaces,
        "sub_agents": clear_sub_agents,
    }
    values_map = {
        "tools": tools,
        "skills": skills,
        "sandboxes": sandboxes,
        "workspaces": workspaces,
        "sub_agents": sub_agents,
    }

    kwargs: dict = {}
    if description is not None:
        kwargs["description"] = description
    if prompt is not None:
        kwargs["prompt"] = prompt
    if model_service is not None:
        kwargs["model_service_name"] = model_service
    if model is not None:
        kwargs["model_name"] = model

    for cli_field, sdk_field, clear_flag_name in _LIST_FIELDS:
        has_values = bool(values_map[cli_field])
        has_clear = clear_map[cli_field]
        if has_values and has_clear:
            raise click.UsageError(
                f"Cannot combine --{cli_field.replace('_', '-')} with {clear_flag_name}"
            )
        if has_clear:
            kwargs[sdk_field] = []
        elif has_values:
            kwargs[sdk_field] = list(values_map[cli_field])

    profile, region = ctx_cfg(ctx)
    cfg = build_sdk_config(profile_name=profile, region=region)
    client = _get_client_cls()(config=cfg)
    agent = client.update(name, **kwargs)
    format_output(ctx, serialize_super_agent(agent), quiet_field="name")


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


@click.command("delete", help="Delete a super agent.")
@click.argument("name")
@click.pass_context
@handle_errors
def delete_cmd(ctx, name):
    """Delete a super agent."""
    profile, region = ctx_cfg(ctx)
    cfg = build_sdk_config(profile_name=profile, region=region)
    client = _get_client_cls()(config=cfg)
    client.delete(name)
    format_output(ctx, {"name": name, "deleted": True}, quiet_field="name")
