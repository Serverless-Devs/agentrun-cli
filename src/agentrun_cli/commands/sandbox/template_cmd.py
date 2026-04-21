"""``ar sandbox template`` — manage sandbox templates."""

from typing import Optional

import click

from agentrun_cli._utils.error import handle_errors
from agentrun_cli._utils.output import format_output

from ._helpers import _build_cfg, _load_json_option


@click.group("template", help="Manage sandbox templates.")
def template_group():
    pass


@template_group.command("create")
@click.option("--type", "tpl_type", required=True, help="Template type: CodeInterpreter / Browser / AllInOne / CustomImage.")
@click.option("--name", "tpl_name", default=None, help="Template name (auto-generated if omitted).")
@click.option("--cpu", type=float, default=None, help="CPU cores.")
@click.option("--memory", type=int, default=None, help="Memory in MB.")
@click.option("--disk-size", type=int, default=None, help="Disk size in MB.")
@click.option("--idle-timeout", type=int, default=None, help="Sandbox idle timeout (seconds).")
@click.option("--ttl", type=int, default=None, help="Sandbox max TTL (seconds).")
@click.option("--concurrency", type=int, default=None, help="Max concurrency per sandbox.")
@click.option("--description", default=None, help="Template description.")
@click.option("--env", multiple=True, help="Environment variable (KEY=VALUE), repeatable.")
@click.option("--network-mode", default=None, help="Network mode: PUBLIC / PRIVATE / PUBLIC_AND_PRIVATE.")
@click.option("--credential-name", default=None, help="Credential name.")
@click.option("--container-image", default=None, help="Container image (CustomImage type).")
@click.option("--container-port", type=int, default=None, help="Container port (CustomImage type).")
@click.option("--from-file", "from_file", default=None, help="Path to JSON file with full TemplateInput.")
@click.pass_context
@handle_errors
def template_create(ctx, tpl_type, tpl_name, cpu, memory, disk_size,
                    idle_timeout, ttl, concurrency, description, env,
                    network_mode, credential_name, container_image,
                    container_port, from_file):
    """Create a sandbox template."""
    from agentrun.sandbox import (
        Sandbox,
        TemplateContainerConfiguration,
        TemplateCredentialConfiguration,
        TemplateInput,
        TemplateNetworkConfiguration,
        TemplateType,
    )

    cfg = _build_cfg(ctx)

    if from_file:
        payload = _load_json_option(from_file)
        inp = TemplateInput(**payload)
    else:
        env_vars = dict(e.split("=", 1) for e in env) if env else None

        net_cfg = None
        if network_mode:
            net_cfg = TemplateNetworkConfiguration(network_mode=network_mode)

        cred_cfg = None
        if credential_name:
            cred_cfg = TemplateCredentialConfiguration(credential_name=credential_name)

        container_cfg = None
        if container_image:
            container_cfg = TemplateContainerConfiguration(
                image=container_image,
                port=container_port,
            )

        kwargs = {"template_type": TemplateType(tpl_type)}
        if tpl_name is not None:
            kwargs["template_name"] = tpl_name
        if cpu is not None:
            kwargs["cpu"] = cpu
        if memory is not None:
            kwargs["memory"] = memory
        if disk_size is not None:
            kwargs["disk_size"] = disk_size
        if idle_timeout is not None:
            kwargs["sandbox_idle_timeout_in_seconds"] = idle_timeout
        if ttl is not None:
            kwargs["sandboxTTLInSeconds"] = ttl
        if concurrency is not None:
            kwargs["share_concurrency_limit_per_sandbox"] = concurrency
        if description is not None:
            kwargs["description"] = description
        if env_vars:
            kwargs["environment_variables"] = env_vars
        if net_cfg:
            kwargs["network_configuration"] = net_cfg
        if cred_cfg:
            kwargs["credential_configuration"] = cred_cfg
        if container_cfg:
            kwargs["container_configuration"] = container_cfg

        inp = TemplateInput(**kwargs)

    tpl = Sandbox.create_template(inp, config=cfg)
    format_output(ctx, tpl.model_dump(by_alias=False), quiet_field="template_name")


@template_group.command("get")
@click.argument("template_name")
@click.pass_context
@handle_errors
def template_get(ctx, template_name):
    """Get template details."""
    from agentrun.sandbox import Sandbox

    cfg = _build_cfg(ctx)
    tpl = Sandbox.get_template(template_name, config=cfg)
    format_output(ctx, tpl.model_dump(by_alias=False), quiet_field="template_name")


@template_group.command("list")
@click.option("--page", type=int, default=1, help="Page number.")
@click.option("--page-size", type=int, default=10, help="Page size.")
@click.option("--type", "tpl_type", default=None, help="Filter by template type.")
@click.pass_context
@handle_errors
def template_list(ctx, page, page_size, tpl_type):
    """List sandbox templates."""
    from agentrun.sandbox import PageableInput, Sandbox

    cfg = _build_cfg(ctx)
    inp = PageableInput(page_number=page, page_size=page_size)
    templates = Sandbox.list_templates(inp, config=cfg)
    rows = [t.model_dump(by_alias=False) for t in templates]
    format_output(ctx, rows)


@template_group.command("update")
@click.argument("template_name")
@click.option("--cpu", type=float, default=None, help="CPU cores.")
@click.option("--memory", type=int, default=None, help="Memory in MB.")
@click.option("--idle-timeout", type=int, default=None, help="Sandbox idle timeout (seconds).")
@click.option("--ttl", type=int, default=None, help="Sandbox max TTL (seconds).")
@click.option("--description", default=None, help="Template description.")
@click.option("--env", multiple=True, help="Environment variable (KEY=VALUE), repeatable.")
@click.option("--from-file", "from_file", default=None, help="Path to JSON file with update fields.")
@click.pass_context
@handle_errors
def template_update(ctx, template_name, cpu, memory, idle_timeout, ttl,
                    description, env, from_file):
    """Update a sandbox template."""
    from agentrun.sandbox import Sandbox, TemplateInput

    cfg = _build_cfg(ctx)

    if from_file:
        payload = _load_json_option(from_file)
        inp = TemplateInput(**payload)
    else:
        # Get existing template to preserve its type
        existing = Sandbox.get_template(template_name, config=cfg)
        kwargs = {"template_type": existing.template_type}
        if cpu is not None:
            kwargs["cpu"] = cpu
        if memory is not None:
            kwargs["memory"] = memory
        if idle_timeout is not None:
            kwargs["sandbox_idle_timeout_in_seconds"] = idle_timeout
        if ttl is not None:
            kwargs["sandboxTTLInSeconds"] = ttl
        if description is not None:
            kwargs["description"] = description
        if env:
            kwargs["environment_variables"] = dict(e.split("=", 1) for e in env)
        inp = TemplateInput(**kwargs)

    tpl = Sandbox.update_template(template_name, inp, config=cfg)
    format_output(ctx, tpl.model_dump(by_alias=False), quiet_field="template_name")


@template_group.command("delete")
@click.argument("template_name")
@click.pass_context
@handle_errors
def template_delete(ctx, template_name):
    """Delete a sandbox template."""
    from agentrun.sandbox import Sandbox

    cfg = _build_cfg(ctx)
    Sandbox.delete_template(template_name, config=cfg)
    format_output(ctx, {"template_name": template_name, "status": "DELETED"}, quiet_field="template_name")
