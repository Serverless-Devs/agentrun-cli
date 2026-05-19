"""YAML schema parsing for ``ar runtime apply / render``.

Schema (k8s-style, single document, ``kind: AgentRuntime``)::

    apiVersion: agentrun/v1
    kind: AgentRuntime
    metadata:
      name: <str, required>
      description: <str>
      workspace: <str>      # XOR workspaceId
      workspaceId: <str>
    spec:
      container:            # required (Container mode only)
        image: <str>        # required
        command: [<str>, ...]
        port: <int>
        imageRegistryType: <ACR|ACREE|CUSTOM>
        acrInstanceId: <str>
        registryConfig: ...
      cpu / memory / port / diskSize
      enableSessionIsolation
      protocol: {type, settings}
      network: {mode, vpcId, vswitchIds, securityGroupId}
      healthCheck / log / env
      credentialName / executionRoleArn
      sessionConcurrencyLimitPerInstance / sessionIdleTimeoutSeconds
      nas / ossMount
      endpoints: [...]      # None → inject default; [] → no endpoints

See ``projects/agent-infra-build-runit/design/runtime-cli-design.md`` §2 for the
complete field list.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import yaml

SUPPORTED_API_VERSION = "agentrun/v1"
SUPPORTED_KIND = "AgentRuntime"

_NAME_RE = re.compile(r"^[a-z0-9-]{1,63}$")


class YamlSchemaError(ValueError):
    """Raised when a document fails schema validation."""


@dataclass
class ParsedRegistryAuth:
    user_name: str | None = None
    password: str | None = field(default=None, repr=False)


@dataclass
class ParsedRegistryCert:
    insecure: bool | None = None
    root_ca_cert_base_64: str | None = None


@dataclass
class ParsedRegistryNetwork:
    vpc_id: str | None = None
    v_switch_id: str | None = None
    security_group_id: str | None = None


@dataclass
class ParsedRegistryConfig:
    auth: ParsedRegistryAuth | None = None
    cert: ParsedRegistryCert | None = None
    network: ParsedRegistryNetwork | None = None


@dataclass
class ParsedContainer:
    image: str
    command: list[str] | None = None
    port: int | None = None
    image_registry_type: str | None = None
    acr_instance_id: str | None = None
    registry_config: ParsedRegistryConfig | None = None


@dataclass
class ParsedProtocolSetting:
    type: str | None = None
    name: str | None = None
    path: str | None = None
    path_prefix: str | None = None
    method: str | None = None
    request_content_type: str | None = None
    response_content_type: str | None = None
    headers: str | None = None
    input_body_json_schema: str | None = None
    output_body_json_schema: str | None = None
    a2a_agent_card: str | None = None
    a2a_agent_card_url: str | None = None
    config: str | None = None


@dataclass
class ParsedProtocol:
    type: str | None = None
    settings: list[ParsedProtocolSetting] | None = None


@dataclass
class ParsedNetwork:
    mode: str | None = None
    vpc_id: str | None = None
    vswitch_ids: list[str] | None = None
    security_group_id: str | None = None


@dataclass
class ParsedHealthCheck:
    http_get_url: str | None = None
    initial_delay_seconds: int | None = None
    period_seconds: int | None = None
    timeout_seconds: int | None = None
    failure_threshold: int | None = None
    success_threshold: int | None = None


@dataclass
class ParsedLog:
    project: str
    logstore: str


@dataclass
class ParsedNasMountPoint:
    server_addr: str
    mount_dir: str
    enable_tls: bool | None = None


@dataclass
class ParsedNas:
    user_id: int | None = None
    group_id: int | None = None
    mount_points: list[ParsedNasMountPoint] = field(default_factory=list)


@dataclass
class ParsedOssMountPoint:
    bucket_name: str
    mount_dir: str
    bucket_path: str | None = None
    endpoint: str | None = None
    read_only: bool | None = None


@dataclass
class ParsedOssMount:
    mount_points: list[ParsedOssMountPoint] = field(default_factory=list)


@dataclass
class ParsedScheduledPolicy:
    name: str | None = None
    schedule_expression: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    target: int | None = None
    time_zone: str | None = None


@dataclass
class ParsedScaling:
    min_instances: int | None = None
    scheduled_policies: list[ParsedScheduledPolicy] = field(default_factory=list)


@dataclass
class ParsedEndpoint:
    name: str
    description: str | None = None
    target_version: str | None = None
    routing: list[tuple[str, float]] | None = None
    disable_public_network_access: bool | None = None
    scaling: ParsedScaling | None = None


@dataclass
class ParsedAgentRuntime:
    name: str
    container: ParsedContainer
    description: str | None = None
    workspace_name: str | None = None
    workspace_id: str | None = None
    cpu: float | None = None
    memory: int | None = None
    port: int | None = None
    disk_size: int | None = None
    enable_session_isolation: bool | None = None
    protocol: ParsedProtocol | None = None
    network: ParsedNetwork | None = None
    health_check: ParsedHealthCheck | None = None
    log: ParsedLog | None = None
    env: dict[str, str] | None = None
    credential_name: str | None = None
    execution_role_arn: str | None = None
    session_concurrency_limit_per_instance: int | None = None
    session_idle_timeout_seconds: int | None = None
    nas: ParsedNas | None = None
    oss_mount: ParsedOssMount | None = None
    endpoints: list[ParsedEndpoint] | None = None


def parse_yaml_text(text: str) -> list[ParsedAgentRuntime]:
    """Parse multi-doc YAML; return list of parsed runtimes."""
    try:
        raw_docs = list(yaml.safe_load_all(text))
    except yaml.YAMLError as e:
        raise YamlSchemaError(f"Invalid YAML: {e}") from e

    raw_docs = [d for d in raw_docs if d is not None]
    if not raw_docs:
        raise YamlSchemaError("No documents found in YAML input.")

    results: list[ParsedAgentRuntime] = []
    for idx, doc in enumerate(raw_docs):
        try:
            results.append(_validate_doc(doc))
        except YamlSchemaError as e:
            raise YamlSchemaError(f"Document #{idx + 1}: {e}") from e
    return results


def _require_mapping(value: Any, where: str) -> dict:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise YamlSchemaError(f"{where} must be a mapping.")
    return value


def _parse_container(raw: dict) -> ParsedContainer:
    image = raw.get("image")
    if not isinstance(image, str) or not image:
        raise YamlSchemaError("spec.container.image is required and must be a string.")
    image_registry_type = raw.get("imageRegistryType")
    if image_registry_type is not None and image_registry_type not in (
        "ACR", "ACREE", "CUSTOM",
    ):
        raise YamlSchemaError(
            f"spec.container.imageRegistryType {image_registry_type!r} must be "
            "one of ACR|ACREE|CUSTOM."
        )
    registry_config = None
    if image_registry_type == "CUSTOM":
        rc_raw = raw.get("registryConfig")
        if not isinstance(rc_raw, dict):
            raise YamlSchemaError(
                "spec.container.registryConfig is required when "
                "imageRegistryType=CUSTOM."
            )
        registry_config = _parse_registry_config(rc_raw)
    elif raw.get("registryConfig") is not None:
        # Allow but parse if present even for ACR/ACREE
        registry_config = _parse_registry_config(raw["registryConfig"])
    return ParsedContainer(
        image=image,
        command=list(raw["command"]) if raw.get("command") else None,
        port=raw.get("port"),
        image_registry_type=image_registry_type,
        acr_instance_id=raw.get("acrInstanceId"),
        registry_config=registry_config,
    )


def _parse_registry_config(raw: dict) -> ParsedRegistryConfig:
    auth_raw = raw.get("auth")
    cert_raw = raw.get("cert")
    net_raw = raw.get("network")
    auth = None
    if isinstance(auth_raw, dict):
        auth = ParsedRegistryAuth(
            user_name=auth_raw.get("userName"),
            password=auth_raw.get("password"),
        )
    cert = None
    if isinstance(cert_raw, dict):
        cert = ParsedRegistryCert(
            insecure=cert_raw.get("insecure"),
            root_ca_cert_base_64=cert_raw.get("rootCaCertBase64"),
        )
    network = None
    if isinstance(net_raw, dict):
        network = ParsedRegistryNetwork(
            vpc_id=net_raw.get("vpcId"),
            v_switch_id=net_raw.get("vSwitchId"),
            security_group_id=net_raw.get("securityGroupId"),
        )
    return ParsedRegistryConfig(auth=auth, cert=cert, network=network)


def _parse_protocol(raw) -> ParsedProtocol | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise YamlSchemaError("spec.protocol must be a mapping.")
    settings_raw = raw.get("settings")
    settings = None
    if settings_raw is not None:
        if not isinstance(settings_raw, list):
            raise YamlSchemaError("spec.protocol.settings must be a list.")
        settings = [
            ParsedProtocolSetting(
                type=s.get("type"),
                name=s.get("name"),
                path=s.get("path"),
                path_prefix=s.get("pathPrefix"),
                method=s.get("method"),
                request_content_type=s.get("requestContentType"),
                response_content_type=s.get("responseContentType"),
                headers=s.get("headers"),
                input_body_json_schema=s.get("inputBodyJsonSchema"),
                output_body_json_schema=s.get("outputBodyJsonSchema"),
                a2a_agent_card=s.get("a2aAgentCard"),
                a2a_agent_card_url=s.get("a2aAgentCardUrl"),
                config=s.get("config"),
            )
            for s in settings_raw
            if isinstance(s, dict)
        ]
    return ParsedProtocol(type=raw.get("type"), settings=settings)


def _parse_network(raw) -> ParsedNetwork | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise YamlSchemaError("spec.network must be a mapping.")
    mode = raw.get("mode")
    vpc_id = raw.get("vpcId")
    if mode in ("PRIVATE", "PUBLIC_AND_PRIVATE") and not vpc_id:
        raise YamlSchemaError(
            "spec.network.vpcId is required when mode is PRIVATE or PUBLIC_AND_PRIVATE."
        )
    return ParsedNetwork(
        mode=mode,
        vpc_id=vpc_id,
        vswitch_ids=list(raw["vswitchIds"]) if raw.get("vswitchIds") else None,
        security_group_id=raw.get("securityGroupId"),
    )


def _parse_health_check(raw) -> ParsedHealthCheck | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise YamlSchemaError("spec.healthCheck must be a mapping.")
    return ParsedHealthCheck(
        http_get_url=raw.get("httpGetUrl"),
        initial_delay_seconds=raw.get("initialDelaySeconds"),
        period_seconds=raw.get("periodSeconds"),
        timeout_seconds=raw.get("timeoutSeconds"),
        failure_threshold=raw.get("failureThreshold"),
        success_threshold=raw.get("successThreshold"),
    )


def _parse_log(raw) -> ParsedLog | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise YamlSchemaError("spec.log must be a mapping.")
    project = raw.get("project")
    logstore = raw.get("logstore")
    if bool(project) != bool(logstore):
        raise YamlSchemaError(
            "spec.log.project and spec.log.logstore must be set together."
        )
    if project is None:
        return None
    return ParsedLog(project=project, logstore=logstore)


def _parse_env(raw) -> dict[str, str] | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise YamlSchemaError("spec.env must be a mapping of str→str.")
    out = {}
    for k, v in raw.items():
        if not isinstance(k, str):
            raise YamlSchemaError("spec.env keys must be strings.")
        out[k] = str(v)
    return out


def _parse_nas(raw) -> ParsedNas | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise YamlSchemaError("spec.nas must be a mapping.")
    points = []
    for mp in raw.get("mountPoints", []) or []:
        if not isinstance(mp, dict):
            raise YamlSchemaError("spec.nas.mountPoints[*] must be a mapping.")
        sa = mp.get("serverAddr")
        md = mp.get("mountDir")
        if not sa or not md:
            raise YamlSchemaError(
                "spec.nas.mountPoints[*] requires serverAddr and mountDir."
            )
        points.append(
            ParsedNasMountPoint(
                server_addr=sa, mount_dir=md, enable_tls=mp.get("enableTLS")
            )
        )
    return ParsedNas(
        user_id=raw.get("userId"), group_id=raw.get("groupId"), mount_points=points
    )


def _parse_oss(raw) -> ParsedOssMount | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise YamlSchemaError("spec.ossMount must be a mapping.")
    points = []
    for mp in raw.get("mountPoints", []) or []:
        if not isinstance(mp, dict):
            raise YamlSchemaError("spec.ossMount.mountPoints[*] must be a mapping.")
        bn = mp.get("bucketName")
        md = mp.get("mountDir")
        if not bn or not md:
            raise YamlSchemaError(
                "spec.ossMount.mountPoints[*] requires bucketName and mountDir."
            )
        points.append(
            ParsedOssMountPoint(
                bucket_name=bn,
                mount_dir=md,
                bucket_path=mp.get("bucketPath"),
                endpoint=mp.get("endpoint"),
                read_only=mp.get("readOnly"),
            )
        )
    return ParsedOssMount(mount_points=points)


def _parse_endpoints(raw) -> list[ParsedEndpoint] | None:
    """Return None if key absent; [] if explicitly empty; else parsed list."""
    if raw is None:
        return None
    if not isinstance(raw, list):
        raise YamlSchemaError("spec.endpoints must be a list.")
    if not raw:
        return []
    seen: set[str] = set()
    out: list[ParsedEndpoint] = []
    for ep_raw in raw:
        if not isinstance(ep_raw, dict):
            raise YamlSchemaError("spec.endpoints[*] must be a mapping.")
        name = ep_raw.get("name")
        if not isinstance(name, str) or not name:
            raise YamlSchemaError("spec.endpoints[*].name is required.")
        if name in seen:
            raise YamlSchemaError(f"spec.endpoints[*] duplicate name: {name!r}.")
        seen.add(name)
        target_version = ep_raw.get("targetVersion")
        routing_raw = ep_raw.get("routing")
        if target_version is not None and routing_raw is not None:
            raise YamlSchemaError(
                f"endpoint {name!r}: targetVersion and routing are mutually exclusive."
            )
        routing = None
        if routing_raw is not None:
            if not isinstance(routing_raw, list) or not routing_raw:
                raise YamlSchemaError(
                    f"endpoint {name!r}: routing must be a non-empty list."
                )
            routing = []
            total = 0.0
            for r in routing_raw:
                if not isinstance(r, dict):
                    raise YamlSchemaError(
                        f"endpoint {name!r}: routing[*] must be a mapping."
                    )
                v = r.get("version")
                w = r.get("weight")
                if v is None or w is None:
                    raise YamlSchemaError(
                        f"endpoint {name!r}: routing[*] requires version and weight."
                    )
                try:
                    weight_f = float(w)
                except (TypeError, ValueError):
                    raise YamlSchemaError(
                        f"endpoint {name!r}: routing[*].weight must be a number, "
                        f"got {w!r}."
                    ) from None
                routing.append((str(v), weight_f))
                total += weight_f
            if abs(total - 100.0) > 1e-6:
                raise YamlSchemaError(
                    f"endpoint {name!r}: routing weights must sum to 100 (got {total})."
                )
        scaling = _parse_scaling(ep_raw.get("scaling"), name)
        out.append(
            ParsedEndpoint(
                name=name,
                description=ep_raw.get("description"),
                target_version=target_version,
                routing=routing,
                disable_public_network_access=ep_raw.get("disablePublicNetworkAccess"),
                scaling=scaling,
            )
        )
    return out


def _parse_scaling(raw, ep_name: str) -> ParsedScaling | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise YamlSchemaError(f"endpoint {ep_name!r}: scaling must be a mapping.")
    min_instances = raw.get("minInstances")
    policies = []
    for p in raw.get("scheduledPolicies", []) or []:
        if not isinstance(p, dict):
            raise YamlSchemaError(
                f"endpoint {ep_name!r}: scheduledPolicies[*] must be a mapping."
            )
        target = p.get("target")
        if min_instances is not None and target is not None and target < min_instances:
            raise YamlSchemaError(
                f"endpoint {ep_name!r}: scheduledPolicies[*].target ({target}) "
                f"is less than minInstances ({min_instances})."
            )
        policies.append(
            ParsedScheduledPolicy(
                name=p.get("name"),
                schedule_expression=p.get("scheduleExpression"),
                start_time=p.get("startTime"),
                end_time=p.get("endTime"),
                target=target,
                time_zone=p.get("timeZone"),
            )
        )
    return ParsedScaling(min_instances=min_instances, scheduled_policies=policies)


def _validate_doc(doc: Any) -> ParsedAgentRuntime:
    if not isinstance(doc, dict):
        raise YamlSchemaError("Top level must be a mapping.")

    api_version = doc.get("apiVersion")
    if api_version != SUPPORTED_API_VERSION:
        raise YamlSchemaError(
            f"Unsupported apiVersion {api_version!r}; "
            f"expected {SUPPORTED_API_VERSION!r}."
        )
    kind = doc.get("kind")
    if kind != SUPPORTED_KIND:
        raise YamlSchemaError(
            f"Unsupported kind {kind!r}; expected {SUPPORTED_KIND!r}."
        )

    metadata = _require_mapping(doc.get("metadata"), "metadata")
    name = metadata.get("name")
    if not isinstance(name, str) or not name:
        raise YamlSchemaError("metadata.name is required and must be a string.")
    if not _NAME_RE.match(name):
        raise YamlSchemaError(
            f"metadata.name {name!r} is invalid; must match [a-z0-9-]{{1,63}}."
        )

    spec = _require_mapping(doc.get("spec"), "spec")

    if "code" in spec:
        raise YamlSchemaError(
            "spec.code is not supported; this CLI only supports Container mode."
        )
    if "tags" in metadata:
        raise YamlSchemaError(
            "metadata.tags is not supported; SDK 0.0.200 removed the tags field."
        )
    if "systemTags" in metadata:
        raise YamlSchemaError(
            "metadata.systemTags is reserved; system_tags is managed by the CLI."
        )
    workspace = metadata.get("workspace")
    workspace_id = metadata.get("workspaceId")
    if workspace is not None and workspace_id is not None:
        raise YamlSchemaError(
            "metadata.workspace and metadata.workspaceId are mutually exclusive."
        )

    container_raw = spec.get("container")
    if not isinstance(container_raw, dict):
        raise YamlSchemaError("spec.container is required and must be a mapping.")
    container = _parse_container(container_raw)

    protocol = _parse_protocol(spec.get("protocol"))
    network = _parse_network(spec.get("network"))
    health_check = _parse_health_check(spec.get("healthCheck"))
    log = _parse_log(spec.get("log"))
    env = _parse_env(spec.get("env"))
    nas = _parse_nas(spec.get("nas"))
    oss_mount = _parse_oss(spec.get("ossMount"))
    endpoints = _parse_endpoints(spec.get("endpoints"))

    return ParsedAgentRuntime(
        name=name,
        description=metadata.get("description"),
        workspace_name=workspace,
        workspace_id=workspace_id,
        container=container,
        cpu=spec.get("cpu"),
        memory=spec.get("memory"),
        port=spec.get("port"),
        disk_size=spec.get("diskSize"),
        enable_session_isolation=spec.get("enableSessionIsolation"),
        protocol=protocol,
        network=network,
        health_check=health_check,
        log=log,
        env=env,
        credential_name=spec.get("credentialName"),
        execution_role_arn=spec.get("executionRoleArn"),
        session_concurrency_limit_per_instance=spec.get(
            "sessionConcurrencyLimitPerInstance"
        ),
        session_idle_timeout_seconds=spec.get("sessionIdleTimeoutSeconds"),
        nas=nas,
        oss_mount=oss_mount,
        endpoints=endpoints,
    )


def parse_yaml_file(path: str) -> list[ParsedAgentRuntime]:
    with open(path, encoding="utf-8") as f:
        return parse_yaml_text(f.read())
