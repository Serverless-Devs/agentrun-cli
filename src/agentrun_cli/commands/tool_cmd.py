"""``ar tool`` — manage MCP and FunctionCall tools.

Examples::

    ar tool create --name weather-mcp --tool-type MCP \\
        --create-method MCP_REMOTE \\
        --protocol-spec '{"mcpServers":{"w":{"url":"https://example.com/sse"}}}'

    ar tool list
    ar tool get --name weather-mcp
    ar tool list-tools --name weather-mcp
    ar tool invoke --name weather-mcp --sub-tool get_weather \\
        --arguments '{"city": "杭州"}'
    ar tool delete --name weather-mcp
"""

import json
from typing import Optional

import click

from agentrun_cli._utils.config import build_sdk_config
from agentrun_cli._utils.error import handle_errors
from agentrun_cli._utils.inner_client import get_agentrun_client
from agentrun_cli._utils.output import format_output


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ctx_cfg(ctx):
    return (ctx.obj or {}).get("profile"), (ctx.obj or {}).get("region")


def _serialize_tool(t) -> dict:
    """Convert an inner SDK Tool object to a plain dict."""
    return {
        k: v for k, v in {
            "tool_id": getattr(t, "tool_id", None),
            "tool_name": getattr(t, "tool_name", None) or getattr(t, "name", None),
            "tool_type": getattr(t, "tool_type", None),
            "create_method": getattr(t, "create_method", None),
            "status": getattr(t, "status", None),
            "description": getattr(t, "description", None),
            "created_at": getattr(t, "created_at", None) or getattr(t, "created_time", None),
            "updated_at": getattr(t, "updated_at", None) or getattr(t, "last_updated_at", None) or getattr(t, "last_modified_time", None),
        }.items() if v is not None
    }


def _serialize_tool_detail(t) -> dict:
    """Convert an inner SDK Tool object to a detailed dict."""
    base = _serialize_tool(t)
    extras = {}
    for field in ("protocol_spec", "memory", "timeout", "credential_name",
                  "environment_variables", "data_endpoint"):
        val = getattr(t, field, None)
        if val is not None:
            extras[field] = val
    mcp_config = getattr(t, "mcp_config", None)
    if mcp_config:
        if isinstance(mcp_config, dict):
            extras["mcp_config"] = mcp_config
        elif hasattr(mcp_config, "to_map"):
            extras["mcp_config"] = mcp_config.to_map()
        elif hasattr(mcp_config, "model_dump"):
            extras["mcp_config"] = mcp_config.model_dump()
        else:
            extras["mcp_config"] = str(mcp_config)
    base.update(extras)
    return base


def _load_json_option(raw: Optional[str]) -> Optional[dict]:
    if raw is None:
        return None
    if not raw.strip().startswith("{"):
        with open(raw, "r", encoding="utf-8") as f:
            return json.load(f)
    return json.loads(raw)


def _serialize_tool_info(ti) -> dict:
    """Convert a ToolInfo to a plain dict."""
    d = {"name": ti.name, "description": ti.description}
    if ti.parameters:
        d["parameters"] = ti.parameters.to_json_schema() if hasattr(ti.parameters, "to_json_schema") else str(ti.parameters)
    return d


# ---------------------------------------------------------------------------
# Top-level group
# ---------------------------------------------------------------------------

@click.group("tool", help="Manage MCP and FunctionCall tools.")
def tool_group():
    pass


# ===========================================================================
# CRUD
# ===========================================================================

@tool_group.command("create")
@click.option("--name", "tool_name", required=True, help="Unique tool name.")
@click.option("--tool-type", "tool_type", required=True, help="Tool type: MCP or FUNCTIONCALL.")
@click.option("--create-method", "create_method", required=True, help="MCP_REMOTE / MCP_BUNDLE / CODE_PACKAGE / OPENAPI_IMPORT.")
@click.option("--description", default=None, help="Tool description.")
@click.option("--protocol-spec", "protocol_spec", default=None, help="Protocol spec JSON string or file path.")
@click.option("--proxy-enabled/--no-proxy-enabled", "proxy_enabled", default=None, help="Enable MCP proxy (MCP_REMOTE only).")
@click.option("--session-affinity", default=None, help="Session affinity: MCP_SSE / MCP_STREAMABLE.")
@click.option("--image", default=None, help="Container image (MCP_BUNDLE / CODE_PACKAGE).")
@click.option("--port", type=int, default=None, help="Container port.")
@click.option("--command", default=None, help="Startup command.")
@click.option("--timeout", type=int, default=None, help="Timeout in seconds.")
@click.option("--memory", type=int, default=None, help="Memory in MB.")
@click.option("--cpu", type=float, default=None, help="CPU cores.")
@click.option("--credential", "credential_name", default=None, help="Credential name.")
@click.option("--env", multiple=True, help="Environment variable (key=value), repeatable.")
@click.option("--from-file", "from_file", default=None, help="JSON file with full CreateToolInputV2.")
@click.pass_context
@handle_errors
def tool_create(ctx, tool_name, tool_type, create_method, description, protocol_spec,
                proxy_enabled, session_affinity, image, port, command, timeout, memory,
                cpu, credential_name, env, from_file):
    """Create a new tool (MCP or FunctionCall)."""
    from alibabacloud_agentrun20250910 import models

    profile, region = _ctx_cfg(ctx)
    client, headers, runtime = get_agentrun_client(profile, region)

    if from_file:
        payload = _load_json_option(from_file)
        inp = models.CreateToolInputV2(**payload)
    else:
        # Parse protocol spec from file or inline
        spec_str = None
        if protocol_spec:
            raw = _load_json_option(protocol_spec)
            spec_str = json.dumps(raw) if isinstance(raw, dict) else protocol_spec

        # Container configuration
        container_cfg = None
        if image:
            cmd_list = command.split() if command else None
            container_cfg = models.ContainerConfiguration(
                image=image, port=port, command=cmd_list,
            )

        # MCP config
        mcp_cfg = None
        if proxy_enabled is not None or session_affinity:
            mcp_cfg = models.McpConfig(
                proxy_enabled=proxy_enabled,
                session_affinity=session_affinity,
            )

        # Environment variables
        env_vars = None
        if env:
            env_vars = {}
            for e in env:
                k, _, v = e.partition("=")
                env_vars[k] = v

        inp = models.CreateToolInputV2(
            tool_name=tool_name,
            tool_type=tool_type,
            create_method=create_method,
            description=description,
            protocol_spec=spec_str,
            container_configuration=container_cfg,
            mcp_config=mcp_cfg,
            timeout=timeout,
            memory=memory,
            cpu=cpu,
            credential_name=credential_name,
            environment_variables=env_vars,
        )

    request = models.CreateToolRequest(body=inp)
    resp = client.create_tool_with_options(request, headers, runtime)
    data = resp.body.data
    result = _serialize_tool(data) if data else {"tool_name": tool_name, "status": "created"}
    format_output(ctx, result, quiet_field="tool_name")


@tool_group.command("get")
@click.option("--name", "tool_name", required=True, help="Tool name.")
@click.pass_context
@handle_errors
def tool_get(ctx, tool_name):
    """Get tool details."""
    from agentrun.tool import Tool

    profile, region = _ctx_cfg(ctx)
    cfg = build_sdk_config(profile_name=profile, region=region)
    tool = Tool.get_by_name(tool_name, config=cfg)
    format_output(ctx, _serialize_tool_detail(tool), quiet_field="tool_name")


@tool_group.command("list")
@click.option("--tool-type", "tool_type", default=None, help="Filter: MCP / FUNCTIONCALL.")
@click.option("--page-number", type=int, default=None, help="Page number.")
@click.option("--page-size", type=int, default=None, help="Page size.")
@click.pass_context
@handle_errors
def tool_list(ctx, tool_type, page_number, page_size):
    """List tools."""
    from alibabacloud_agentrun20250910 import models

    profile, region = _ctx_cfg(ctx)
    client, headers, runtime = get_agentrun_client(profile, region)

    request = models.ListToolsRequest(
        tool_type=tool_type,
        page_number=page_number,
        page_size=page_size,
    )
    resp = client.list_tools_with_options(request, headers, runtime)
    items = resp.body.data.items or []
    rows = [_serialize_tool(t) for t in items]
    format_output(ctx, rows)


@tool_group.command("update")
@click.option("--name", "tool_name", required=True, help="Tool name.")
@click.option("--description", default=None, help="New description.")
@click.option("--protocol-spec", "protocol_spec", default=None, help="New protocol spec.")
@click.option("--timeout", type=int, default=None, help="New timeout.")
@click.option("--memory", type=int, default=None, help="New memory (MB).")
@click.option("--cpu", type=float, default=None, help="New CPU cores.")
@click.option("--credential", "credential_name", default=None, help="New credential name.")
@click.option("--proxy-enabled/--no-proxy-enabled", "proxy_enabled", default=None, help="MCP proxy toggle.")
@click.option("--session-affinity", default=None, help="Session affinity.")
@click.option("--from-file", "from_file", default=None, help="JSON file with update fields.")
@click.pass_context
@handle_errors
def tool_update(ctx, tool_name, description, protocol_spec, timeout, memory, cpu,
                credential_name, proxy_enabled, session_affinity, from_file):
    """Update a tool."""
    from alibabacloud_agentrun20250910 import models

    profile, region = _ctx_cfg(ctx)
    client, headers, runtime = get_agentrun_client(profile, region)

    if from_file:
        payload = _load_json_option(from_file)
        inp = models.UpdateToolInputV2(**payload)
    else:
        spec_str = None
        if protocol_spec:
            raw = _load_json_option(protocol_spec)
            spec_str = json.dumps(raw) if isinstance(raw, dict) else protocol_spec

        mcp_cfg = None
        if proxy_enabled is not None or session_affinity:
            mcp_cfg = models.McpConfig(
                proxy_enabled=proxy_enabled,
                session_affinity=session_affinity,
            )

        inp = models.UpdateToolInputV2(
            description=description,
            protocol_spec=spec_str,
            timeout=timeout,
            memory=memory,
            cpu=cpu,
            credential_name=credential_name,
            mcp_config=mcp_cfg,
        )

    request = models.UpdateToolRequest(body=inp)
    resp = client.update_tool_with_options(tool_name, request, headers, runtime)
    data = resp.body.data
    result = _serialize_tool(data) if data else {"tool_name": tool_name, "status": "updated"}
    format_output(ctx, result, quiet_field="tool_name")


@tool_group.command("delete")
@click.option("--name", "tool_name", required=True, help="Tool name.")
@click.pass_context
@handle_errors
def tool_delete(ctx, tool_name):
    """Delete a tool."""
    profile, region = _ctx_cfg(ctx)
    client, headers, runtime = get_agentrun_client(profile, region)

    client.delete_tool_with_options(tool_name, headers, runtime)
    format_output(ctx, {"deleted": tool_name}, quiet_field="deleted")


# ===========================================================================
# Data-plane: list-tools / invoke
# ===========================================================================

@tool_group.command("list-tools")
@click.option("--name", "tool_name", required=True, help="Tool name.")
@click.pass_context
@handle_errors
def tool_list_tools(ctx, tool_name):
    """List sub-tools of a tool."""
    from agentrun.tool import Tool

    profile, region = _ctx_cfg(ctx)
    cfg = build_sdk_config(profile_name=profile, region=region)
    tool = Tool.get_by_name(tool_name, config=cfg)
    sub_tools = tool.list_tools(config=cfg)
    result = {
        "tool_name": tool_name,
        "tool_type": tool.tool_type,
        "sub_tools": [_serialize_tool_info(t) for t in sub_tools],
    }
    format_output(ctx, result)


@tool_group.command("invoke")
@click.option("--name", "tool_name", required=True, help="Tool name.")
@click.option("--sub-tool", required=True, help="Sub-tool name to call.")
@click.option("--arguments", default=None, help="Arguments JSON string.")
@click.option("--arguments-file", default=None, help="Arguments JSON file.")
@click.pass_context
@handle_errors
def tool_invoke(ctx, tool_name, sub_tool, arguments, arguments_file):
    """Invoke a sub-tool."""
    from agentrun.tool import Tool

    if arguments and arguments_file:
        raise click.UsageError("--arguments and --arguments-file are mutually exclusive.")

    args = None
    if arguments:
        args = json.loads(arguments)
    elif arguments_file:
        with open(arguments_file, "r", encoding="utf-8") as f:
            args = json.load(f)

    profile, region = _ctx_cfg(ctx)
    cfg = build_sdk_config(profile_name=profile, region=region)
    tool = Tool.get_by_name(tool_name, config=cfg)
    result = tool.call_tool(sub_tool, arguments=args, config=cfg)

    output = {
        "tool_name": tool_name,
        "sub_tool": sub_tool,
        "result": result,
    }
    format_output(ctx, output)
