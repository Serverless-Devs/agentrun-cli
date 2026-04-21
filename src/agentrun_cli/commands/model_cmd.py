"""``ar model`` — manage model services.

Model services register external LLM providers (DashScope, OpenAI, etc.)
into the AgentRun platform.

Examples::

    # Register a DashScope model service
    ar model create --name qwen-max \\
        --provider tongyi --model-type llm \\
        --model-names qwen-max,qwen-plus

    # List all model services
    ar model list

    # Get details of a specific service
    ar model get --name qwen-max

    # Delete a service
    ar model delete --name qwen-max
"""

import json
from typing import Optional

import click

from agentrun_cli._utils.config import build_sdk_config
from agentrun_cli._utils.error import handle_errors
from agentrun_cli._utils.output import format_output


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _serialize_model_service(svc) -> dict:
    """Convert a ModelService SDK object to a plain dict for output."""
    return {
        "model_service_name": svc.model_service_name,
        "provider": svc.provider,
        "model_type": str(svc.model_type) if svc.model_type else None,
        "description": svc.description,
        "status": str(svc.status) if svc.status else None,
        "provider_settings": svc.provider_settings.model_dump() if svc.provider_settings else None,
        "model_info_configs": (
            [c.model_dump() for c in svc.model_info_configs]
            if svc.model_info_configs
            else None
        ),
        "credential_name": svc.credential_name,
        "created_at": svc.created_at,
        "last_updated_at": svc.last_updated_at,
    }


def _load_json_option(raw: Optional[str]) -> Optional[dict]:
    """Parse a --from-file path or inline JSON string into a dict."""
    if raw is None:
        return None
    # If it looks like a file path, read the file
    if not raw.strip().startswith("{"):
        with open(raw, "r", encoding="utf-8") as f:
            return json.load(f)
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Top-level group
# ---------------------------------------------------------------------------

@click.group("model", help="Manage model services.")
def model_group():
    pass


# ===========================================================================
# ar model create / get / list / update / delete
# ===========================================================================

@model_group.command("create")
@click.option("--name", "service_name", required=True, help="Unique name for the model service.")
@click.option("--provider", required=True, help="Provider identifier (e.g. tongyi, openai, deepseek, anthropic).")
@click.option("--model-type", "model_type", default="llm", help="Model type: llm, text-embedding, rerank, speech2text, tts, moderation.")
@click.option("--model-names", default=None, help="Comma-separated list of model names exposed by this service.")
@click.option("--base-url", default=None, help="Custom base URL for the provider API.")
@click.option("--api-key", default=None, help="API key for the provider (prefer using credentials instead).")
@click.option("--credential", "credential_name", default=None, help="Name of an AgentRun credential to use for authentication.")
@click.option("--description", default=None, help="Human-readable description.")
@click.option("--from-file", "from_file", default=None, help="Path to a JSON file with full ModelServiceCreateInput.")
@click.pass_context
@handle_errors
def model_create(ctx, service_name, provider, model_type, model_names, base_url, api_key, credential_name, description, from_file):
    """Register a new model service."""
    from agentrun.model import (
        ModelService,
        ModelServiceCreateInput,
        ModelType,
        ProviderSettings,
    )

    cfg = build_sdk_config(
        profile_name=(ctx.obj or {}).get("profile"),
        region=(ctx.obj or {}).get("region"),
    )

    if from_file:
        payload = _load_json_option(from_file)
        inp = ModelServiceCreateInput(**payload)
    else:
        provider_settings = None
        if api_key or base_url or model_names:
            provider_settings = ProviderSettings(
                api_key=api_key,
                base_url=base_url,
                model_names=model_names.split(",") if model_names else None,
            )

        inp = ModelServiceCreateInput(
            model_service_name=service_name,
            provider=provider,
            model_type=ModelType(model_type) if model_type else None,
            provider_settings=provider_settings,
            credential_name=credential_name,
            description=description,
        )

    svc = ModelService.create(inp, config=cfg)
    format_output(ctx, _serialize_model_service(svc), quiet_field="model_service_name")


@model_group.command("get")
@click.option("--name", "service_name", required=True, help="Name of the model service to retrieve.")
@click.pass_context
@handle_errors
def model_get(ctx, service_name):
    """Get details of a model service."""
    from agentrun.model import ModelService

    cfg = build_sdk_config(
        profile_name=(ctx.obj or {}).get("profile"),
        region=(ctx.obj or {}).get("region"),
    )
    svc = ModelService.get_by_name(service_name, config=cfg)
    format_output(ctx, _serialize_model_service(svc), quiet_field="model_service_name")


@model_group.command("list")
@click.option("--provider", default=None, help="Filter by provider name.")
@click.option("--model-type", "model_type", default="llm", help="Model type: llm, text-embedding, rerank, speech2text, tts, moderation (default: llm).")
@click.pass_context
@handle_errors
def model_list(ctx, provider, model_type):
    """List all model services."""
    from agentrun.model import ModelService, ModelType

    cfg = build_sdk_config(
        profile_name=(ctx.obj or {}).get("profile"),
        region=(ctx.obj or {}).get("region"),
    )
    mt = ModelType(model_type)
    services = ModelService.list_all(model_type=mt, provider=provider, config=cfg)
    rows = [_serialize_model_service(s) for s in services]
    format_output(ctx, rows)


@model_group.command("update")
@click.option("--name", "service_name", required=True, help="Name of the model service to update.")
@click.option("--description", default=None, help="New description.")
@click.option("--api-key", default=None, help="New API key.")
@click.option("--base-url", default=None, help="New base URL.")
@click.option("--credential", "credential_name", default=None, help="New credential name.")
@click.option("--from-file", "from_file", default=None, help="Path to a JSON file with ModelServiceUpdateInput fields.")
@click.pass_context
@handle_errors
def model_update(ctx, service_name, description, api_key, base_url, credential_name, from_file):
    """Update an existing model service."""
    from agentrun.model import ModelService, ModelServiceUpdateInput, ProviderSettings

    cfg = build_sdk_config(
        profile_name=(ctx.obj or {}).get("profile"),
        region=(ctx.obj or {}).get("region"),
    )

    if from_file:
        payload = _load_json_option(from_file)
        inp = ModelServiceUpdateInput(**payload)
    else:
        provider_settings = None
        if api_key or base_url:
            provider_settings = ProviderSettings(api_key=api_key, base_url=base_url)

        inp = ModelServiceUpdateInput(
            description=description,
            provider_settings=provider_settings,
            credential_name=credential_name,
        )

    svc = ModelService.update_by_name(service_name, inp, config=cfg)
    format_output(ctx, _serialize_model_service(svc), quiet_field="model_service_name")


@model_group.command("delete")
@click.option("--name", "service_name", required=True, help="Name of the model service to delete.")
@click.pass_context
@handle_errors
def model_delete(ctx, service_name):
    """Delete a model service."""
    from agentrun.model import ModelService

    cfg = build_sdk_config(
        profile_name=(ctx.obj or {}).get("profile"),
        region=(ctx.obj or {}).get("region"),
    )
    ModelService.delete_by_name(service_name, config=cfg)
    format_output(ctx, {"deleted": service_name}, quiet_field="deleted")
