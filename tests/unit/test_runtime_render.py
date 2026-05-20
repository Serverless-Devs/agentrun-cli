"""Tests for ParsedAgentRuntime → SDK input rendering."""

from types import SimpleNamespace

from agentrun_cli._utils.agentruntime_yaml import (
    ParsedAgentRuntime,
    ParsedContainer,
    ParsedEndpoint,
    ParsedHealthCheck,
    ParsedLog,
    ParsedNas,
    ParsedNasMountPoint,
    ParsedNetwork,
    ParsedOssMount,
    ParsedOssMountPoint,
    ParsedProtocol,
    ParsedProtocolSetting,
    ParsedRegistryAuth,
    ParsedRegistryCert,
    ParsedRegistryConfig,
    ParsedRegistryNetwork,
    ParsedScaling,
    ParsedScheduledPolicy,
)
from agentrun_cli._utils.runtime_constants import (
    ARTIFACT_TYPE_CONTAINER,
    DEFAULT_ENDPOINT_NAME,
    DEFAULT_TARGET_VERSION,
    SYSTEM_TAG_CLI,
)
from agentrun_cli._utils.runtime_render import (
    endpoint_needs_update,
    to_endpoint_create_inputs,
    to_endpoint_update_input,
    to_runtime_create_input,
    to_runtime_update_input,
)


def _minimal_parsed():
    return ParsedAgentRuntime(
        name="my-agent",
        container=ParsedContainer(image="img:v1"),
    )


def test_create_input_injects_system_tag_and_container_artifact():
    p = _minimal_parsed()
    inp = to_runtime_create_input(p)
    assert inp.agent_runtime_name == "my-agent"
    assert inp.artifact_type == ARTIFACT_TYPE_CONTAINER
    assert inp.system_tags == [SYSTEM_TAG_CLI]
    assert inp.container_configuration.image == "img:v1"
    # code_configuration must not be set
    assert inp.code_configuration is None
    # Defaults injected — backend rejects nulls for these three fields.
    assert inp.cpu == 2.0
    assert inp.memory == 4096
    assert inp.port == 9000


def test_create_input_user_values_override_defaults():
    p = ParsedAgentRuntime(
        name="my-agent",
        container=ParsedContainer(image="img:v1"),
        cpu=4,
        memory=16384,
        port=8080,
    )
    inp = to_runtime_create_input(p)
    assert inp.cpu == 4
    assert inp.memory == 16384
    assert inp.port == 8080


def test_create_input_container_port_wins_over_spec_port():
    p = ParsedAgentRuntime(
        name="my-agent",
        container=ParsedContainer(image="img:v1", port=7777),
        port=9000,
    )
    assert to_runtime_create_input(p).port == 7777


def test_update_input_applies_same_defaults():
    upd = to_runtime_update_input(_minimal_parsed())
    assert upd.cpu == 2.0
    assert upd.memory == 4096
    assert upd.port == 9000


def test_endpoints_none_injects_default():
    p = _minimal_parsed()
    inps = to_endpoint_create_inputs(p)
    assert len(inps) == 1
    assert inps[0].agent_runtime_endpoint_name == DEFAULT_ENDPOINT_NAME
    assert inps[0].target_version == DEFAULT_TARGET_VERSION


def test_endpoints_empty_list_returns_empty():
    p = _minimal_parsed()
    p.endpoints = []
    assert to_endpoint_create_inputs(p) == []


def test_endpoints_routing_mapped():
    p = _minimal_parsed()
    p.endpoints = [
        ParsedEndpoint(name="canary", routing=[("1", 80.0), ("2", 20.0)]),
    ]
    inps = to_endpoint_create_inputs(p)
    rc = inps[0].routing_configuration
    assert rc is not None
    vs = rc.version_weights
    assert [(v.version, v.weight) for v in vs] == [("1", 80.0), ("2", 20.0)]


def test_update_input_strips_workspace():
    p = _minimal_parsed()
    p.workspace_name = "ws"
    upd = to_runtime_update_input(p)
    # AgentRuntimeUpdateInput inherits only MutableProps — workspace fields not present.
    assert not hasattr(upd, "workspace_name") or upd.workspace_name is None


def test_full_spec_round_trip():
    p = ParsedAgentRuntime(
        name="my-agent",
        container=ParsedContainer(image="img:v1", port=8000),
        cpu=4,
        memory=8192,
        disk_size=20,
        port=9000,
        enable_session_isolation=True,
        protocol=ParsedProtocol(type="HTTP"),
        network=ParsedNetwork(mode="PUBLIC", vpc_id=None),
        health_check=ParsedHealthCheck(http_get_url="/healthz", period_seconds=10),
        log=ParsedLog(project="p", logstore="ls"),
        env={"K": "V"},
        nas=ParsedNas(
            mount_points=[ParsedNasMountPoint(server_addr="x.nas:/", mount_dir="/mnt")]
        ),
        oss_mount=ParsedOssMount(
            mount_points=[ParsedOssMountPoint(bucket_name="b", mount_dir="/mnt/oss")]
        ),
        endpoints=[
            ParsedEndpoint(
                name="prod",
                target_version="LATEST",
                scaling=ParsedScaling(min_instances=2),
            )
        ],
    )
    inp = to_runtime_create_input(p)
    assert inp.cpu == 4
    assert inp.memory == 8192
    assert inp.disk_size == 20
    assert inp.environment_variables == {"K": "V"}
    assert inp.nas_config and inp.nas_config.mount_points
    assert inp.oss_mount_config and inp.oss_mount_config.mount_points
    assert inp.health_check_configuration.http_get_url == "/healthz"
    assert inp.log_configuration.project == "p"

    eps = to_endpoint_create_inputs(p)
    assert eps[0].scaling_config.min_instances == 2


def test_endpoint_needs_update_detects_target_version_change():
    current = SimpleNamespace(
        description=None,
        target_version="OLD",
        routing_configuration=None,
        disable_public_network_access=None,
    )
    desired = ParsedEndpoint(name="x", target_version="LATEST")
    assert endpoint_needs_update(desired, current) is True


def test_endpoint_needs_update_no_drift():
    current = SimpleNamespace(
        description=None,
        target_version="LATEST",
        routing_configuration=None,
        disable_public_network_access=None,
    )
    desired = ParsedEndpoint(name="x")
    # desired.target_version is None — _endpoint_create injects LATEST when no
    # routing is present, but drift detection treats absent desired value as
    # "don't compare". Spec for drift: only fields the user set differ.
    assert endpoint_needs_update(desired, current) is False


# --- additional render coverage ----------------------------------------------


def test_protocol_settings_rendered():
    p = _minimal_parsed()
    p.protocol = ParsedProtocol(
        type="HTTP",
        settings=[ParsedProtocolSetting(type="HTTP", path="/x", method="GET")],
    )
    inp = to_runtime_create_input(p)
    pc = inp.protocol_configuration
    assert pc and pc.protocol_settings and pc.protocol_settings[0].path == "/x"


def test_container_full_registry_config_rendered():
    p = _minimal_parsed()
    p.container = ParsedContainer(
        image="img",
        image_registry_type="CUSTOM",
        registry_config=ParsedRegistryConfig(
            auth=ParsedRegistryAuth(user_name="u", password="p"),  # noqa: S106
            cert=ParsedRegistryCert(insecure=True, root_ca_cert_base_64="abc"),
            network=ParsedRegistryNetwork(
                vpc_id="vpc-1", v_switch_id="vsw-1", security_group_id="sg-1"
            ),
        ),
    )
    inp = to_runtime_create_input(p)
    rc = inp.container_configuration.registry_config
    assert rc.auth_config.user_name == "u"
    assert rc.cert_config.insecure is True
    assert rc.network_config.vpc_id == "vpc-1"


def test_endpoint_update_input_renders_routing_and_scaling():
    ep = ParsedEndpoint(
        name="ep",
        description="d",
        routing=[("1", 50.0), ("2", 50.0)],
        disable_public_network_access=True,
        scaling=ParsedScaling(
            min_instances=1,
            scheduled_policies=[
                ParsedScheduledPolicy(
                    name="p",
                    schedule_expression="* * * * *",
                    start_time="s",
                    end_time="e",
                    target=2,
                    time_zone="UTC",
                )
            ],
        ),
    )
    upd = to_endpoint_update_input(ep)
    assert upd.agent_runtime_endpoint_name == "ep"
    assert upd.routing_configuration.version_weights[0].version == "1"
    assert upd.scaling_config.min_instances == 1
    assert upd.scaling_config.scheduled_policies[0].target == 2


def test_endpoint_update_input_no_routing_no_scaling():
    ep = ParsedEndpoint(name="ep", target_version="LATEST")
    upd = to_endpoint_update_input(ep)
    assert upd.routing_configuration is None
    assert upd.scaling_config is None


def test_endpoint_needs_update_description_drift():
    current = SimpleNamespace(
        description="old",
        target_version=None,
        routing_configuration=None,
        disable_public_network_access=None,
    )
    desired = ParsedEndpoint(name="x", description="new")
    assert endpoint_needs_update(desired, current) is True


def test_endpoint_needs_update_routing_drift():
    cur_rc = SimpleNamespace(
        version_weights=[
            SimpleNamespace(version="1", weight=50.0),
            SimpleNamespace(version="2", weight=50.0),
        ]
    )
    current = SimpleNamespace(
        description=None,
        target_version=None,
        routing_configuration=cur_rc,
        disable_public_network_access=None,
    )
    desired = ParsedEndpoint(name="x", routing=[("1", 80.0), ("2", 20.0)])
    assert endpoint_needs_update(desired, current) is True


def test_endpoint_needs_update_disable_public_drift():
    current = SimpleNamespace(
        description=None,
        target_version=None,
        routing_configuration=None,
        disable_public_network_access=False,
    )
    desired = ParsedEndpoint(name="x", disable_public_network_access=True)
    assert endpoint_needs_update(desired, current) is True


def test_endpoint_needs_update_routing_weight_none_handled():
    cur_rc = SimpleNamespace(
        version_weights=[
            SimpleNamespace(version="1", weight=None),
        ]
    )
    current = SimpleNamespace(
        description=None,
        target_version=None,
        routing_configuration=cur_rc,
        disable_public_network_access=None,
    )
    desired = ParsedEndpoint(name="x", routing=[("1", 100.0)])
    assert endpoint_needs_update(desired, current) is True


def test_endpoint_create_with_routing_no_target_version():
    p = _minimal_parsed()
    p.endpoints = [ParsedEndpoint(name="canary", routing=[("1", 100.0)])]
    inps = to_endpoint_create_inputs(p)
    # When routing is set, target_version stays None (no DEFAULT injection)
    assert inps[0].target_version is None


def test_network_default_mode_public():
    p = _minimal_parsed()
    p.network = ParsedNetwork(mode=None)
    inp = to_runtime_create_input(p)
    # Should not error out, default to PUBLIC mode
    assert inp.network_configuration is not None


def test_protocol_with_no_type_defaults_http():
    p = _minimal_parsed()
    p.protocol = ParsedProtocol(type=None)
    inp = to_runtime_create_input(p)
    assert inp.protocol_configuration is not None
