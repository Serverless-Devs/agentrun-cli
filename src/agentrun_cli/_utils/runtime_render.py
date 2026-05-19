"""Render ParsedAgentRuntime → SDK 0.0.200 create/update inputs.

This module owns all "CLI auto-injection" logic:
- ``system_tags`` always includes ``x-agentrun-cli``
- ``artifact_type`` is forced to ``Container``
- If user omitted ``spec.endpoints`` entirely, a single default endpoint is
  injected (name=``default``, target_version=``LATEST``)
"""

from __future__ import annotations

from agentrun_cli._utils.agentruntime_yaml import (
    ParsedAgentRuntime,
    ParsedContainer,
    ParsedEndpoint,
    ParsedScaling,
)
from agentrun_cli._utils.runtime_constants import (
    ARTIFACT_TYPE_CONTAINER,
    DEFAULT_ENDPOINT_NAME,
    DEFAULT_TARGET_VERSION,
    SYSTEM_TAG_CLI,
)


def _sdk_models():
    """Lazy import of SDK models so import is cheap."""
    from agentrun.agent_runtime.model import (
        AgentRuntimeContainer,
        AgentRuntimeCreateInput,
        AgentRuntimeEndpointCreateInput,
        AgentRuntimeEndpointRoutingConfig,
        AgentRuntimeEndpointRoutingWeight,
        AgentRuntimeEndpointUpdateInput,
        AgentRuntimeHealthCheckConfig,
        AgentRuntimeLogConfig,
        AgentRuntimeProtocolConfig,
        AgentRuntimeProtocolType,
        AgentRuntimeUpdateInput,
        NASConfig,
        NASMountConfig,
        OSSMountConfig,
        OSSMountPoint,
        ProtocolSettings,
        RegistryAuthConfig,
        RegistryCertConfig,
        RegistryConfig,
        RegistryNetworkConfig,
        ScalingConfig,
        ScheduledPolicy,
    )
    from agentrun.utils.model import NetworkConfig, NetworkMode

    return {
        "container": AgentRuntimeContainer,
        "create_input": AgentRuntimeCreateInput,
        "update_input": AgentRuntimeUpdateInput,
        "endpoint_create": AgentRuntimeEndpointCreateInput,
        "endpoint_update": AgentRuntimeEndpointUpdateInput,
        "routing_cfg": AgentRuntimeEndpointRoutingConfig,
        "routing_weight": AgentRuntimeEndpointRoutingWeight,
        "health": AgentRuntimeHealthCheckConfig,
        "log": AgentRuntimeLogConfig,
        "protocol_cfg": AgentRuntimeProtocolConfig,
        "protocol_type": AgentRuntimeProtocolType,
        "nas": NASConfig,
        "nas_mount": NASMountConfig,
        "oss": OSSMountConfig,
        "oss_mount": OSSMountPoint,
        "protocol_settings": ProtocolSettings,
        "registry_auth": RegistryAuthConfig,
        "registry_cert": RegistryCertConfig,
        "registry": RegistryConfig,
        "registry_net": RegistryNetworkConfig,
        "scaling": ScalingConfig,
        "scheduled_policy": ScheduledPolicy,
        "net_cfg": NetworkConfig,
        "net_mode": NetworkMode,
    }


def _build_container(p: ParsedContainer, m):
    rc = None
    if p.registry_config:
        rc = m["registry"](
            auth_config=(
                m["registry_auth"](
                    user_name=p.registry_config.auth.user_name,
                    password=p.registry_config.auth.password,
                )
                if p.registry_config.auth
                else None
            ),
            cert_config=(
                m["registry_cert"](
                    insecure=p.registry_config.cert.insecure,
                    root_ca_cert_base_64=p.registry_config.cert.root_ca_cert_base_64,
                )
                if p.registry_config.cert
                else None
            ),
            network_config=(
                m["registry_net"](
                    vpc_id=p.registry_config.network.vpc_id,
                    v_switch_id=p.registry_config.network.v_switch_id,
                    security_group_id=p.registry_config.network.security_group_id,
                )
                if p.registry_config.network
                else None
            ),
        )
    return m["container"](
        image=p.image,
        command=p.command,
        port=p.port,
        image_registry_type=p.image_registry_type,
        acr_instance_id=p.acr_instance_id,
        registry_config=rc,
    )


def to_runtime_create_input(p: ParsedAgentRuntime):
    m = _sdk_models()
    return m["create_input"](
        agent_runtime_name=p.name,
        description=p.description,
        workspace_name=p.workspace_name,
        workspace_id=p.workspace_id,
        artifact_type=ARTIFACT_TYPE_CONTAINER,
        system_tags=[SYSTEM_TAG_CLI],
        container_configuration=_build_container(p.container, m),
        cpu=p.cpu,
        memory=p.memory,
        port=p.port,
        disk_size=p.disk_size,
        enable_session_isolation=p.enable_session_isolation,
        protocol_configuration=_build_protocol(p.protocol, m),
        network_configuration=_build_network(p.network, m),
        health_check_configuration=_build_health(p.health_check, m),
        log_configuration=_build_log(p.log, m),
        environment_variables=p.env,
        credential_name=p.credential_name,
        execution_role_arn=p.execution_role_arn,
        session_concurrency_limit_per_instance=p.session_concurrency_limit_per_instance,
        session_idle_timeout_seconds=p.session_idle_timeout_seconds,
        nas_config=_build_nas(p.nas, m),
        oss_mount_config=_build_oss(p.oss_mount, m),
    )


def to_runtime_update_input(p: ParsedAgentRuntime):
    """Same as create input but workspace is immutable so we strip it."""
    m = _sdk_models()
    return m["update_input"](
        agent_runtime_name=p.name,
        description=p.description,
        artifact_type=ARTIFACT_TYPE_CONTAINER,
        system_tags=[SYSTEM_TAG_CLI],
        container_configuration=_build_container(p.container, m),
        cpu=p.cpu,
        memory=p.memory,
        port=p.port,
        disk_size=p.disk_size,
        enable_session_isolation=p.enable_session_isolation,
        protocol_configuration=_build_protocol(p.protocol, m),
        network_configuration=_build_network(p.network, m),
        health_check_configuration=_build_health(p.health_check, m),
        log_configuration=_build_log(p.log, m),
        environment_variables=p.env,
        credential_name=p.credential_name,
        execution_role_arn=p.execution_role_arn,
        session_concurrency_limit_per_instance=p.session_concurrency_limit_per_instance,
        session_idle_timeout_seconds=p.session_idle_timeout_seconds,
        nas_config=_build_nas(p.nas, m),
        oss_mount_config=_build_oss(p.oss_mount, m),
    )


def _build_protocol(p, m):
    if p is None:
        return None
    settings = None
    if p.settings:
        settings = [
            m["protocol_settings"](
                type=s.type,
                name=s.name,
                path=s.path,
                path_prefix=s.path_prefix,
                method=s.method,
                request_content_type=s.request_content_type,
                response_content_type=s.response_content_type,
                headers=s.headers,
                input_body_json_schema=s.input_body_json_schema,
                output_body_json_schema=s.output_body_json_schema,
                a2a_agent_card=s.a2a_agent_card,
                a2a_agent_card_url=s.a2a_agent_card_url,
                config=s.config,
            )
            for s in p.settings
        ]
    ptype = m["protocol_type"](p.type) if p.type else m["protocol_type"].HTTP
    return m["protocol_cfg"](type=ptype, protocol_settings=settings)


def _build_network(p, m):
    if p is None:
        return None
    mode = m["net_mode"](p.mode) if p.mode else m["net_mode"].PUBLIC
    return m["net_cfg"](
        network_mode=mode,
        vpc_id=p.vpc_id,
        vswitch_ids=p.vswitch_ids,
        security_group_id=p.security_group_id,
    )


def _build_health(p, m):
    if p is None:
        return None
    return m["health"](
        http_get_url=p.http_get_url,
        initial_delay_seconds=p.initial_delay_seconds,
        period_seconds=p.period_seconds,
        timeout_seconds=p.timeout_seconds,
        failure_threshold=p.failure_threshold,
        success_threshold=p.success_threshold,
    )


def _build_log(p, m):
    if p is None:
        return None
    return m["log"](project=p.project, logstore=p.logstore)


def _build_nas(p, m):
    if p is None:
        return None
    return m["nas"](
        user_id=p.user_id,
        group_id=p.group_id,
        mount_points=[
            m["nas_mount"](
                server_addr=mp.server_addr,
                mount_dir=mp.mount_dir,
                enable_tls=mp.enable_tls,
            )
            for mp in p.mount_points
        ]
        or None,
    )


def _build_oss(p, m):
    if p is None:
        return None
    return m["oss"](
        mount_points=[
            m["oss_mount"](
                bucket_name=mp.bucket_name,
                mount_dir=mp.mount_dir,
                bucket_path=mp.bucket_path,
                endpoint=mp.endpoint,
                read_only=mp.read_only,
            )
            for mp in p.mount_points
        ]
        or None
    )


def to_endpoint_create_inputs(p: ParsedAgentRuntime):
    """Return SDK endpoint create inputs.

    Rules:
        p.endpoints is None  → inject a single ``default`` endpoint
        p.endpoints == []    → return []
        otherwise            → map each parsed endpoint
    """
    m = _sdk_models()
    if p.endpoints is None:
        return [
            m["endpoint_create"](
                agent_runtime_endpoint_name=DEFAULT_ENDPOINT_NAME,
                target_version=DEFAULT_TARGET_VERSION,
            )
        ]
    return [_endpoint_create(ep, m) for ep in p.endpoints]


def _endpoint_create(ep: ParsedEndpoint, m):
    routing_cfg = None
    if ep.routing is not None:
        routing_cfg = m["routing_cfg"](
            version_weights=[
                m["routing_weight"](version=v, weight=w) for v, w in ep.routing
            ]
        )
    scaling_cfg = _build_scaling(ep.scaling, m)
    target_version = ep.target_version or (
        None if ep.routing else DEFAULT_TARGET_VERSION
    )
    return m["endpoint_create"](
        agent_runtime_endpoint_name=ep.name,
        description=ep.description,
        target_version=target_version,
        routing_configuration=routing_cfg,
        disable_public_network_access=ep.disable_public_network_access,
        scaling_config=scaling_cfg,
    )


def to_endpoint_update_input(ep: ParsedEndpoint):
    m = _sdk_models()
    routing_cfg = None
    if ep.routing is not None:
        routing_cfg = m["routing_cfg"](
            version_weights=[
                m["routing_weight"](version=v, weight=w) for v, w in ep.routing
            ]
        )
    return m["endpoint_update"](
        agent_runtime_endpoint_name=ep.name,
        description=ep.description,
        target_version=ep.target_version,
        routing_configuration=routing_cfg,
        disable_public_network_access=ep.disable_public_network_access,
        scaling_config=_build_scaling(ep.scaling, m),
    )


def _build_scaling(s: ParsedScaling | None, m):
    if s is None:
        return None
    policies = [
        m["scheduled_policy"](
            name=p.name,
            schedule_expression=p.schedule_expression,
            start_time=p.start_time,
            end_time=p.end_time,
            target=p.target,
            time_zone=p.time_zone,
        )
        for p in s.scheduled_policies
    ] or None
    return m["scaling"](min_instances=s.min_instances, scheduled_policies=policies)


def endpoint_needs_update(desired: ParsedEndpoint, current) -> bool:
    """Return True if a drift exists between the parsed endpoint and a remote one."""
    if getattr(current, "description", None) != desired.description:
        return True
    if (getattr(current, "target_version", None) or None) != desired.target_version:
        if desired.target_version is not None:
            return True
    cur_rc = getattr(current, "routing_configuration", None)
    cur_pairs = None
    if cur_rc and getattr(cur_rc, "version_weights", None):
        cur_pairs = [
            (w.version, float(w.weight) if w.weight is not None else None)
            for w in cur_rc.version_weights
        ]
    if cur_pairs != desired.routing:
        return True
    cur_disable = getattr(current, "disable_public_network_access", None)
    if cur_disable != desired.disable_public_network_access:
        return True
    return False
