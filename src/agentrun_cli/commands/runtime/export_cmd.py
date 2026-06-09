"""``ar runtime export`` — dump an existing runtime as CLI YAML."""

from __future__ import annotations

from typing import Any

import click
import yaml

from agentrun_cli._utils.config import build_sdk_config
from agentrun_cli._utils.error import EXIT_BAD_INPUT, EXIT_NOT_FOUND, handle_errors
from agentrun_cli._utils.output import echo_error
from agentrun_cli._utils.runtime_reconciler import find_runtime_by_name
from agentrun_cli.commands.runtime._helpers import ctx_cfg

AgentRuntime: Any = None


class RuntimeExportError(ValueError):
    """Raised when a remote runtime cannot be represented as CLI YAML."""


def _lazy_sdk() -> Any:
    global AgentRuntime
    if AgentRuntime is None:
        from agentrun.agent_runtime import AgentRuntime as _AR

        AgentRuntime = _AR
    return AgentRuntime


@click.command(
    "export",
    help="Export an existing Agent Runtime as ar runtime apply YAML.",
)
@click.argument("name")
@click.option(
    "-f",
    "--file",
    "file_path",
    default=None,
    type=click.Path(dir_okay=False, writable=True),
    help="Write YAML to a file instead of stdout.",
)
@click.option(
    "--include-secrets",
    is_flag=True,
    help="Include sensitive registry authentication fields in exported YAML.",
)
@click.pass_context
@handle_errors
def export_cmd(ctx, name, file_path, include_secrets):
    rt_cls = _lazy_sdk()
    profile, region = ctx_cfg(ctx)
    build_sdk_config(profile_name=profile, region=region)
    runtime = find_runtime_by_name(rt_cls, name)
    if runtime is None:
        echo_error("ResourceNotFound", f"AgentRuntime {name!r} not found.")
        raise SystemExit(EXIT_NOT_FOUND)
    try:
        data = runtime_to_yaml_doc(runtime, include_secrets=include_secrets)
    except RuntimeExportError as exc:
        echo_error("UnsupportedRuntime", str(exc))
        raise SystemExit(EXIT_BAD_INPUT) from exc

    text = yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
    if file_path:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)
        return
    click.echo(text, nl=False)


def runtime_to_yaml_doc(
    runtime: Any, *, include_secrets: bool = False
) -> dict[str, Any]:
    artifact_type = _enum_value(_get(runtime, "artifact_type", "artifactType"))
    if artifact_type and artifact_type != "Container":
        raise RuntimeExportError(
            f"AgentRuntime {_get(runtime, 'agent_runtime_name', 'agentRuntimeName')!r} "
            f"uses artifact_type={artifact_type!r}; CLI YAML supports only Container."
        )

    container = _get(runtime, "container_configuration", "containerConfiguration")
    image = _get(container, "image")
    if not image:
        raise RuntimeExportError("Remote runtime has no container image to export.")

    metadata: dict[str, Any] = {
        "name": _get(runtime, "agent_runtime_name", "agentRuntimeName")
    }
    _set_if_present(metadata, "description", _get(runtime, "description"))
    workspace_id = _get(runtime, "workspace_id", "workspaceId")
    if workspace_id:
        metadata["workspaceId"] = workspace_id
    else:
        _set_if_present(
            metadata, "workspace", _get(runtime, "workspace_name", "workspaceName")
        )

    spec: dict[str, Any] = {
        "container": _export_container(container, include_secrets=include_secrets)
    }
    for yaml_key, attr in [
        ("cpu", "cpu"),
        ("memory", "memory"),
        ("port", "port"),
        ("diskSize", "disk_size"),
        ("enableSessionIsolation", "enable_session_isolation"),
        ("credentialName", "credential_name"),
        ("executionRoleArn", "execution_role_arn"),
        (
            "sessionConcurrencyLimitPerInstance",
            "session_concurrency_limit_per_instance",
        ),
        ("sessionIdleTimeoutSeconds", "session_idle_timeout_seconds"),
    ]:
        _set_if_present(spec, yaml_key, _get(runtime, attr, _camel(attr)))

    _set_if_present(
        spec,
        "protocol",
        _export_protocol(
            _get(runtime, "protocol_configuration", "protocolConfiguration")
        ),
    )
    _set_if_present(
        spec,
        "network",
        _export_network(_get(runtime, "network_configuration", "networkConfiguration")),
    )
    _set_if_present(
        spec,
        "healthCheck",
        _export_health(
            _get(runtime, "health_check_configuration", "healthCheckConfiguration")
        ),
    )
    _set_if_present(
        spec,
        "log",
        _export_log(_get(runtime, "log_configuration", "logConfiguration")),
    )
    _set_if_present(
        spec,
        "env",
        _get(runtime, "environment_variables", "environmentVariables"),
    )
    _set_if_present(spec, "nas", _export_nas(_get(runtime, "nas_config", "nasConfig")))
    _set_if_present(
        spec,
        "ossMount",
        _export_oss_mount(_get(runtime, "oss_mount_config", "ossMountConfig")),
    )

    if hasattr(runtime, "list_endpoints"):
        endpoints = [_export_endpoint(ep) for ep in runtime.list_endpoints()]
        if endpoints:
            spec["endpoints"] = endpoints

    return {
        "apiVersion": "agentrun/v1",
        "kind": "AgentRuntime",
        "metadata": metadata,
        "spec": spec,
    }


def _export_container(container: Any, *, include_secrets: bool) -> dict[str, Any]:
    out: dict[str, Any] = {"image": _get(container, "image")}
    command = _get(container, "command")
    if command:
        out["command"] = command
    _set_if_present(out, "port", _get(container, "port"))
    _set_if_present(
        out,
        "imageRegistryType",
        _enum_value(_get(container, "image_registry_type", "imageRegistryType")),
    )
    _set_if_present(
        out, "acrInstanceId", _get(container, "acr_instance_id", "acrInstanceId")
    )
    _set_if_present(
        out,
        "registryConfig",
        _export_registry(
            _get(container, "registry_config", "registryConfig"),
            include_secrets=include_secrets,
        ),
    )
    return out


def _export_registry(registry: Any, *, include_secrets: bool) -> dict[str, Any] | None:
    if registry is None:
        return None
    out: dict[str, Any] = {}
    auth = _get(registry, "auth_config", "authConfig", "auth")
    auth_out: dict[str, Any] = {}
    _set_if_present(auth_out, "userName", _get(auth, "user_name", "userName"))
    if include_secrets:
        _set_if_present(auth_out, "password", _get(auth, "password"))
    _set_if_present(out, "auth", auth_out)

    cert = _get(registry, "cert_config", "certConfig", "cert")
    cert_out: dict[str, Any] = {}
    _set_if_present(cert_out, "insecure", _get(cert, "insecure"))
    _set_if_present(
        cert_out,
        "rootCaCertBase64",
        _get(cert, "root_ca_cert_base_64", "rootCaCertBase64"),
    )
    _set_if_present(out, "cert", cert_out)

    network = _get(registry, "network_config", "networkConfig", "network")
    net_out: dict[str, Any] = {}
    _set_if_present(net_out, "vpcId", _get(network, "vpc_id", "vpcId"))
    _set_if_present(net_out, "vSwitchId", _get(network, "v_switch_id", "vSwitchId"))
    _set_if_present(
        net_out,
        "securityGroupId",
        _get(network, "security_group_id", "securityGroupId"),
    )
    _set_if_present(out, "network", net_out)
    return out or None


def _export_protocol(protocol: Any) -> dict[str, Any] | None:
    if protocol is None:
        return None
    out: dict[str, Any] = {}
    _set_if_present(out, "type", _enum_value(_get(protocol, "type")))
    settings = _get(protocol, "protocol_settings", "protocolSettings", "settings")
    if settings:
        exported: list[dict[str, Any]] = []
        for setting in settings:
            item: dict[str, Any] = {}
            for key, attr in [
                ("type", "type"),
                ("name", "name"),
                ("path", "path"),
                ("pathPrefix", "path_prefix"),
                ("method", "method"),
                ("requestContentType", "request_content_type"),
                ("responseContentType", "response_content_type"),
                ("headers", "headers"),
                ("inputBodyJsonSchema", "input_body_json_schema"),
                ("outputBodyJsonSchema", "output_body_json_schema"),
                ("a2aAgentCard", "a2a_agent_card"),
                ("a2aAgentCardUrl", "a2a_agent_card_url"),
                ("config", "config"),
            ]:
                value = _get(setting, attr, _camel(attr))
                if key == "type":
                    value = _enum_value(value)
                _set_if_present(item, key, value)
            if item:
                exported.append(item)
        if exported:
            out["settings"] = exported
    return out or None


def _export_network(network: Any) -> dict[str, Any] | None:
    if network is None:
        return None
    out: dict[str, Any] = {}
    _set_if_present(
        out,
        "mode",
        _enum_value(_get(network, "network_mode", "networkMode", "mode")),
    )
    _set_if_present(out, "vpcId", _get(network, "vpc_id", "vpcId"))
    _set_if_present(out, "vswitchIds", _get(network, "vswitch_ids", "vswitchIds"))
    _set_if_present(
        out,
        "securityGroupId",
        _get(network, "security_group_id", "securityGroupId"),
    )
    return out or None


def _export_health(health: Any) -> dict[str, Any] | None:
    if health is None:
        return None
    out: dict[str, Any] = {}
    for key, attr in [
        ("httpGetUrl", "http_get_url"),
        ("initialDelaySeconds", "initial_delay_seconds"),
        ("periodSeconds", "period_seconds"),
        ("timeoutSeconds", "timeout_seconds"),
        ("failureThreshold", "failure_threshold"),
        ("successThreshold", "success_threshold"),
    ]:
        _set_if_present(out, key, _get(health, attr, _camel(attr)))
    return out or None


def _export_log(log: Any) -> dict[str, Any] | None:
    if log is None:
        return None
    out: dict[str, Any] = {}
    _set_if_present(out, "project", _get(log, "project"))
    _set_if_present(out, "logstore", _get(log, "logstore"))
    return out or None


def _export_nas(nas: Any) -> dict[str, Any] | None:
    if nas is None:
        return None
    out: dict[str, Any] = {}
    _set_if_present(out, "userId", _get(nas, "user_id", "userId"))
    _set_if_present(out, "groupId", _get(nas, "group_id", "groupId"))
    points: list[dict[str, Any]] = []
    for mp in _get(nas, "mount_points", "mountPoints") or []:
        item: dict[str, Any] = {}
        _set_if_present(item, "serverAddr", _get(mp, "server_addr", "serverAddr"))
        _set_if_present(item, "mountDir", _get(mp, "mount_dir", "mountDir"))
        _set_if_present(item, "enableTLS", _get(mp, "enable_tls", "enableTLS"))
        if item:
            points.append(item)
    if points:
        out["mountPoints"] = points
    return out or None


def _export_oss_mount(oss: Any) -> dict[str, Any] | None:
    if oss is None:
        return None
    points: list[dict[str, Any]] = []
    for mp in _get(oss, "mount_points", "mountPoints") or []:
        item: dict[str, Any] = {}
        for key, attr in [
            ("bucketName", "bucket_name"),
            ("mountDir", "mount_dir"),
            ("bucketPath", "bucket_path"),
            ("endpoint", "endpoint"),
            ("readOnly", "read_only"),
        ]:
            _set_if_present(item, key, _get(mp, attr, _camel(attr)))
        if item:
            points.append(item)
    return {"mountPoints": points} if points else None


def _export_endpoint(endpoint: Any) -> dict[str, Any]:
    out: dict[str, Any] = {
        "name": _get(
            endpoint, "agent_runtime_endpoint_name", "agentRuntimeEndpointName"
        )
    }
    _set_if_present(out, "description", _get(endpoint, "description"))
    routing = _export_routing(
        _get(endpoint, "routing_configuration", "routingConfiguration")
    )
    if routing:
        out["routing"] = routing
    else:
        _set_if_present(
            out, "targetVersion", _get(endpoint, "target_version", "targetVersion")
        )
    _set_if_present(
        out,
        "disablePublicNetworkAccess",
        _get(endpoint, "disable_public_network_access", "disablePublicNetworkAccess"),
    )
    _set_if_present(
        out,
        "scaling",
        _export_scaling(_get(endpoint, "scaling_config", "scalingConfig")),
    )
    return out


def _export_routing(routing: Any) -> list[dict[str, Any]] | None:
    weights = _get(routing, "version_weights", "versionWeights")
    if not weights:
        return None
    out: list[dict[str, Any]] = []
    for weight in weights:
        item: dict[str, Any] = {}
        _set_if_present(item, "version", _get(weight, "version"))
        _set_if_present(item, "weight", _get(weight, "weight"))
        if item:
            out.append(item)
    return out or None


def _export_scaling(scaling: Any) -> dict[str, Any] | None:
    if scaling is None:
        return None
    out: dict[str, Any] = {}
    _set_if_present(out, "minInstances", _get(scaling, "min_instances", "minInstances"))
    policies: list[dict[str, Any]] = []
    for policy in _get(scaling, "scheduled_policies", "scheduledPolicies") or []:
        item: dict[str, Any] = {}
        for key, attr in [
            ("name", "name"),
            ("scheduleExpression", "schedule_expression"),
            ("startTime", "start_time"),
            ("endTime", "end_time"),
            ("target", "target"),
            ("timeZone", "time_zone"),
        ]:
            _set_if_present(item, key, _get(policy, attr, _camel(attr)))
        if item:
            policies.append(item)
    if policies:
        out["scheduledPolicies"] = policies
    return out or None


def _set_if_present(target: dict[str, Any], key: str, value: Any) -> None:
    if value is None or value == {}:
        return
    target[key] = value


def _get(obj: Any, *names: str) -> Any | None:
    if obj is None:
        return None
    if isinstance(obj, dict):
        for name in names:
            if name in obj:
                return obj[name]
        return None
    for name in names:
        if hasattr(obj, name):
            return getattr(obj, name)
    return None


def _enum_value(value: Any) -> Any | None:
    if value is None:
        return None
    if hasattr(value, "value"):
        return value.value
    text = str(value)
    return text.rsplit(".", 1)[-1]


def _camel(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])
