"""Tests for the AgentRuntime YAML parser."""

import pytest

from agentrun_cli._utils.agentruntime_yaml import (
    ParsedAgentRuntime,
    ParsedContainer,
    ParsedEndpoint,
    YamlSchemaError,
    parse_yaml_text,
)


def test_dataclasses_exist_and_default():
    rt = ParsedAgentRuntime(
        name="x",
        container=ParsedContainer(image="img:1"),
    )
    assert rt.name == "x"
    assert rt.container.image == "img:1"
    assert rt.endpoints is None  # None means "inject default"

    ep = ParsedEndpoint(name="default")
    assert ep.target_version is None
    assert ep.routing is None


MINIMAL_YAML = """
apiVersion: agentrun/v1
kind: AgentRuntime
metadata:
  name: my-agent
spec:
  container:
    image: registry.example.com/my-agent:v1
"""


def test_parse_minimal_yaml():
    docs = parse_yaml_text(MINIMAL_YAML)
    assert len(docs) == 1
    rt = docs[0]
    assert rt.name == "my-agent"
    assert rt.container.image == "registry.example.com/my-agent:v1"
    assert rt.container.command is None
    assert rt.endpoints is None  # None means CLI must inject default later
    # Defaults that should NOT be set at parse time (render layer handles them):
    assert rt.cpu is None
    assert rt.memory is None
    assert rt.port is None


def _doc_with(**override):
    base = {
        "apiVersion": "agentrun/v1",
        "kind": "AgentRuntime",
        "metadata": {"name": "x"},
        "spec": {"container": {"image": "img"}},
    }
    base.update(override)
    import yaml as _y

    return _y.dump(base)


def test_wrong_api_version_rejected():
    with pytest.raises(YamlSchemaError, match="apiVersion"):
        parse_yaml_text(_doc_with(apiVersion="wrong/v1"))


def test_wrong_kind_rejected():
    with pytest.raises(YamlSchemaError, match="kind"):
        parse_yaml_text(_doc_with(kind="Something"))


def test_missing_name_rejected():
    with pytest.raises(YamlSchemaError, match="metadata.name"):
        parse_yaml_text(_doc_with(metadata={}))


def test_bad_name_pattern_rejected():
    with pytest.raises(YamlSchemaError, match="metadata.name"):
        parse_yaml_text(_doc_with(metadata={"name": "BadName!"}))


def test_missing_container_rejected():
    with pytest.raises(YamlSchemaError, match="spec.container"):
        parse_yaml_text(_doc_with(spec={}))


def test_missing_image_rejected():
    with pytest.raises(YamlSchemaError, match="image"):
        parse_yaml_text(_doc_with(spec={"container": {}}))


def test_empty_yaml_rejected():
    with pytest.raises(YamlSchemaError, match="No documents"):
        parse_yaml_text("")


def test_invalid_yaml_rejected():
    with pytest.raises(YamlSchemaError, match="Invalid YAML"):
        parse_yaml_text(":\n: invalid")


def test_reject_spec_code():
    with pytest.raises(YamlSchemaError, match="Container mode"):
        parse_yaml_text(
            _doc_with(
                spec={
                    "container": {"image": "img"},
                    "code": {"zipFile": "abc"},
                }
            )
        )


def test_reject_metadata_tags():
    with pytest.raises(YamlSchemaError, match="tags"):
        parse_yaml_text(_doc_with(metadata={"name": "x", "tags": ["t1"]}))


def test_reject_metadata_system_tags():
    with pytest.raises(YamlSchemaError, match="system_tags"):
        parse_yaml_text(_doc_with(metadata={"name": "x", "systemTags": ["x-foo"]}))


def test_workspace_xor_workspaceid():
    with pytest.raises(YamlSchemaError, match="workspace"):
        parse_yaml_text(
            _doc_with(metadata={"name": "x", "workspace": "a", "workspaceId": "ws-1"})
        )


def test_container_full_fields():
    text = _doc_with(
        spec={
            "container": {
                "image": "img:v1",
                "command": ["python", "app.py"],
                "port": 8080,
                "imageRegistryType": "ACREE",
                "acrInstanceId": "cri-xxx",
            }
        }
    )
    rt = parse_yaml_text(text)[0]
    assert rt.container.command == ["python", "app.py"]
    assert rt.container.port == 8080
    assert rt.container.image_registry_type == "ACREE"
    assert rt.container.acr_instance_id == "cri-xxx"


def test_cloud_build_defaults_parsed():
    text = _doc_with(
        spec={
            "container": {
                "image": "registry.example.com/ns/app:v1",
                "cloudBuild": {},
            }
        }
    )
    cloud_build = parse_yaml_text(text)[0].container.cloud_build
    assert cloud_build is not None
    assert cloud_build.dir == "."
    assert cloud_build.setup_script == "scripts/setup.sh"
    assert cloud_build.timeout_minutes == "20"
    assert cloud_build.cpu == "4"
    assert cloud_build.memory == "8192"


def test_cloud_build_registry_parsed():
    text = _doc_with(
        spec={
            "container": {
                "image": "registry.example.com/ns/app:v1",
                "cloudBuild": {
                    "dir": "src",
                    "setupScript": "",
                    "timeoutMinutes": 30,
                    "cpu": "8c",
                    "memory": "16384",
                    "region": "cn-shanghai",
                    "registry": {"username": "u", "password": "p"},
                    "baseContainerConfig": {
                        "image": "registry.example.com/ns/worker:tag"
                    },
                },
            }
        }
    )
    cloud_build = parse_yaml_text(text)[0].container.cloud_build
    assert cloud_build is not None
    assert cloud_build.dir == "src"
    assert cloud_build.setup_script == ""
    assert cloud_build.timeout_minutes == "30"
    assert cloud_build.cpu == "8c"
    assert cloud_build.memory == "16384"
    assert cloud_build.region == "cn-shanghai"
    assert cloud_build.registry and cloud_build.registry.username == "u"
    assert cloud_build.base_container_image == "registry.example.com/ns/worker:tag"


def test_cloud_build_allows_image_without_prevalidation():
    text = _doc_with(
        spec={
            "container": {
                "image": "registry.example.com/ns/app",
                "cloudBuild": {},
            }
        }
    )
    cloud_build = parse_yaml_text(text)[0].container.cloud_build
    assert cloud_build is not None


def test_cloud_build_rejects_registry_mode_field():
    text = _doc_with(
        spec={
            "container": {
                "image": "registry.example.com/ns/app:v1",
                "cloudBuild": {"registryMode": "fc-registry"},
            }
        }
    )
    with pytest.raises(YamlSchemaError, match="unsupported field"):
        parse_yaml_text(text)


def test_cloud_build_rejects_acree_base_fields():
    text = _doc_with(
        spec={
            "container": {
                "image": "registry.example.com/ns/app:v1",
                "cloudBuild": {"baseAcrInstanceId": "cri-xxx"},
            }
        }
    )
    with pytest.raises(YamlSchemaError, match="unsupported field"):
        parse_yaml_text(text)


def test_custom_registry_requires_config():
    text = _doc_with(
        spec={"container": {"image": "img", "imageRegistryType": "CUSTOM"}}
    )
    with pytest.raises(YamlSchemaError, match="registryConfig"):
        parse_yaml_text(text)


def test_custom_registry_config_parsed():
    text = _doc_with(
        spec={
            "container": {
                "image": "img",
                "imageRegistryType": "CUSTOM",
                "registryConfig": {
                    "auth": {"userName": "u", "password": "p"},
                    "cert": {"insecure": True},
                    "network": {"vpcId": "vpc-1"},
                },
            }
        }
    )
    rc = parse_yaml_text(text)[0].container.registry_config
    assert rc is not None
    assert rc.auth and rc.auth.user_name == "u"
    assert rc.cert and rc.cert.insecure is True
    assert rc.network and rc.network.vpc_id == "vpc-1"


def test_resource_fields():
    text = _doc_with(
        spec={
            "container": {"image": "img"},
            "cpu": 4,
            "memory": 8192,
            "diskSize": 20,
            "port": 9100,
            "enableSessionIsolation": True,
        }
    )
    rt = parse_yaml_text(text)[0]
    assert rt.cpu == 4
    assert rt.memory == 8192
    assert rt.disk_size == 20
    assert rt.port == 9100
    assert rt.enable_session_isolation is True


def test_protocol_parsed():
    text = _doc_with(
        spec={
            "container": {"image": "img"},
            "protocol": {
                "type": "MCP",
                "settings": [{"type": "MCP", "path": "/mcp", "method": "POST"}],
            },
        }
    )
    rt = parse_yaml_text(text)[0]
    assert rt.protocol and rt.protocol.type == "MCP"
    assert rt.protocol.settings and rt.protocol.settings[0].path == "/mcp"


def test_network_private_requires_vpc():
    text = _doc_with(
        spec={
            "container": {"image": "img"},
            "network": {"mode": "PRIVATE"},
        }
    )
    with pytest.raises(YamlSchemaError, match="vpcId"):
        parse_yaml_text(text)


def test_network_private_with_vpc_ok():
    text = _doc_with(
        spec={
            "container": {"image": "img"},
            "network": {
                "mode": "PUBLIC_AND_PRIVATE",
                "vpcId": "vpc-1",
                "vswitchIds": ["vsw-1"],
                "securityGroupId": "sg-1",
            },
        }
    )
    rt = parse_yaml_text(text)[0]
    assert rt.network and rt.network.mode == "PUBLIC_AND_PRIVATE"
    assert rt.network.vpc_id == "vpc-1"
    assert rt.network.vswitch_ids == ["vsw-1"]


def test_log_pair_required():
    text = _doc_with(
        spec={
            "container": {"image": "img"},
            "log": {"project": "p"},
        }
    )
    with pytest.raises(YamlSchemaError, match="log.logstore"):
        parse_yaml_text(text)


def test_log_both_present():
    text = _doc_with(
        spec={
            "container": {"image": "img"},
            "log": {"project": "p", "logstore": "ls"},
        }
    )
    rt = parse_yaml_text(text)[0]
    assert rt.log and rt.log.project == "p" and rt.log.logstore == "ls"


def test_env_parsed():
    text = _doc_with(
        spec={
            "container": {"image": "img"},
            "env": {"LOG_LEVEL": "info", "FOO": "bar"},
        }
    )
    rt = parse_yaml_text(text)[0]
    assert rt.env == {"LOG_LEVEL": "info", "FOO": "bar"}


def test_health_check_parsed():
    text = _doc_with(
        spec={
            "container": {"image": "img"},
            "healthCheck": {
                "httpGetUrl": "/healthz",
                "initialDelaySeconds": 5,
                "periodSeconds": 10,
                "timeoutSeconds": 3,
                "failureThreshold": 3,
                "successThreshold": 1,
            },
        }
    )
    rt = parse_yaml_text(text)[0]
    hc = rt.health_check
    assert hc and hc.http_get_url == "/healthz" and hc.period_seconds == 10


def test_nas_parsed():
    text = _doc_with(
        spec={
            "container": {"image": "img"},
            "nas": {
                "userId": 1000,
                "groupId": 1000,
                "mountPoints": [
                    {"serverAddr": "x.nas:/", "mountDir": "/mnt", "enableTLS": True},
                ],
            },
        }
    )
    rt = parse_yaml_text(text)[0]
    assert rt.nas and rt.nas.user_id == 1000
    assert rt.nas.mount_points[0].server_addr == "x.nas:/"
    assert rt.nas.mount_points[0].enable_tls is True


def test_nas_missing_required_field():
    text = _doc_with(
        spec={
            "container": {"image": "img"},
            "nas": {"mountPoints": [{"serverAddr": "x.nas:/"}]},  # missing mountDir
        }
    )
    with pytest.raises(YamlSchemaError, match="mountDir"):
        parse_yaml_text(text)


def test_oss_parsed():
    text = _doc_with(
        spec={
            "container": {"image": "img"},
            "ossMount": {
                "mountPoints": [
                    {"bucketName": "b", "mountDir": "/mnt/oss", "readOnly": True},
                ]
            },
        }
    )
    rt = parse_yaml_text(text)[0]
    assert rt.oss_mount and rt.oss_mount.mount_points[0].bucket_name == "b"
    assert rt.oss_mount.mount_points[0].read_only is True


def test_oss_missing_required_field():
    text = _doc_with(
        spec={
            "container": {"image": "img"},
            "ossMount": {"mountPoints": [{"bucketName": "b"}]},
        }
    )
    with pytest.raises(YamlSchemaError, match="mountDir"):
        parse_yaml_text(text)


def test_endpoints_omitted_is_none():
    rt = parse_yaml_text(MINIMAL_YAML)[0]
    assert rt.endpoints is None  # CLI render layer will inject default


def test_endpoints_empty_list_preserved():
    text = _doc_with(spec={"container": {"image": "img"}, "endpoints": []})
    rt = parse_yaml_text(text)[0]
    assert rt.endpoints == []  # explicit "no endpoints"


def test_endpoint_basic_parsed():
    text = _doc_with(
        spec={
            "container": {"image": "img"},
            "endpoints": [{"name": "prod", "targetVersion": "LATEST"}],
        }
    )
    rt = parse_yaml_text(text)[0]
    assert rt.endpoints and rt.endpoints[0].name == "prod"
    assert rt.endpoints[0].target_version == "LATEST"


def test_endpoint_duplicate_name_rejected():
    text = _doc_with(
        spec={
            "container": {"image": "img"},
            "endpoints": [{"name": "a"}, {"name": "a"}],
        }
    )
    with pytest.raises(YamlSchemaError, match="duplicate"):
        parse_yaml_text(text)


def test_endpoint_target_version_and_routing_mutex():
    text = _doc_with(
        spec={
            "container": {"image": "img"},
            "endpoints": [
                {
                    "name": "x",
                    "targetVersion": "1",
                    "routing": [{"version": "1", "weight": 100}],
                }
            ],
        }
    )
    with pytest.raises(YamlSchemaError, match="mutually exclusive"):
        parse_yaml_text(text)


def test_endpoint_routing_weight_sum():
    text = _doc_with(
        spec={
            "container": {"image": "img"},
            "endpoints": [
                {
                    "name": "x",
                    "routing": [
                        {"version": "1", "weight": 60},
                        {"version": "2", "weight": 30},
                    ],
                }
            ],
        }
    )
    with pytest.raises(YamlSchemaError, match="weight"):
        parse_yaml_text(text)


def test_endpoint_routing_ok():
    text = _doc_with(
        spec={
            "container": {"image": "img"},
            "endpoints": [
                {
                    "name": "x",
                    "routing": [
                        {"version": "1", "weight": 80},
                        {"version": "2", "weight": 20},
                    ],
                }
            ],
        }
    )
    rt = parse_yaml_text(text)[0]
    assert rt.endpoints[0].routing == [("1", 80.0), ("2", 20.0)]


def test_endpoint_scaling_target_lt_min_rejected():
    text = _doc_with(
        spec={
            "container": {"image": "img"},
            "endpoints": [
                {
                    "name": "x",
                    "scaling": {
                        "minInstances": 5,
                        "scheduledPolicies": [
                            {
                                "name": "p",
                                "target": 3,
                                "scheduleExpression": "0 * * * *",
                            },
                        ],
                    },
                }
            ],
        }
    )
    with pytest.raises(YamlSchemaError, match="minInstances"):
        parse_yaml_text(text)


def test_multi_doc_supported():
    text = (
        _doc_with(metadata={"name": "a"}) + "---\n" + _doc_with(metadata={"name": "b"})
    )
    docs = parse_yaml_text(text)
    assert [d.name for d in docs] == ["a", "b"]


def test_parse_yaml_file(tmp_path):
    from agentrun_cli._utils.agentruntime_yaml import parse_yaml_file

    p = tmp_path / "rt.yaml"
    p.write_text(MINIMAL_YAML, encoding="utf-8")
    docs = parse_yaml_file(str(p))
    assert docs[0].name == "my-agent"


# --- additional coverage for edge / error branches -----------------------------


def test_top_level_not_mapping():
    with pytest.raises(YamlSchemaError, match="Top level"):
        parse_yaml_text("- 1\n- 2\n")


def test_metadata_not_mapping():
    with pytest.raises(YamlSchemaError, match="metadata"):
        parse_yaml_text(
            "apiVersion: agentrun/v1\nkind: AgentRuntime\nmetadata: foo\n"
            "spec:\n  container:\n    image: img\n"
        )


def test_protocol_not_mapping():
    with pytest.raises(YamlSchemaError, match="protocol"):
        parse_yaml_text(
            _doc_with(
                spec={
                    "container": {"image": "img"},
                    "protocol": "bad",
                }
            )
        )


def test_protocol_settings_not_list():
    with pytest.raises(YamlSchemaError, match="settings"):
        parse_yaml_text(
            _doc_with(
                spec={
                    "container": {"image": "img"},
                    "protocol": {"type": "HTTP", "settings": "bad"},
                }
            )
        )


def test_network_not_mapping():
    with pytest.raises(YamlSchemaError, match="network"):
        parse_yaml_text(
            _doc_with(
                spec={
                    "container": {"image": "img"},
                    "network": "bad",
                }
            )
        )


def test_health_check_not_mapping():
    with pytest.raises(YamlSchemaError, match="healthCheck"):
        parse_yaml_text(
            _doc_with(
                spec={
                    "container": {"image": "img"},
                    "healthCheck": "bad",
                }
            )
        )


def test_log_not_mapping():
    with pytest.raises(YamlSchemaError, match="log"):
        parse_yaml_text(
            _doc_with(
                spec={
                    "container": {"image": "img"},
                    "log": "bad",
                }
            )
        )


def test_env_not_mapping():
    with pytest.raises(YamlSchemaError, match="env"):
        parse_yaml_text(
            _doc_with(
                spec={
                    "container": {"image": "img"},
                    "env": "bad",
                }
            )
        )


def test_env_non_string_key():
    # Non-string keys are valid YAML but should be rejected. Build YAML manually.
    text = (
        "apiVersion: agentrun/v1\nkind: AgentRuntime\n"
        "metadata: {name: x}\n"
        "spec:\n  container: {image: img}\n  env:\n    1: v\n"
    )
    with pytest.raises(YamlSchemaError, match="env"):
        parse_yaml_text(text)


def test_nas_not_mapping():
    with pytest.raises(YamlSchemaError, match="nas"):
        parse_yaml_text(
            _doc_with(
                spec={
                    "container": {"image": "img"},
                    "nas": "bad",
                }
            )
        )


def test_nas_mount_point_not_mapping():
    with pytest.raises(YamlSchemaError, match="mountPoints"):
        parse_yaml_text(
            _doc_with(
                spec={
                    "container": {"image": "img"},
                    "nas": {"mountPoints": ["bad"]},
                }
            )
        )


def test_oss_not_mapping():
    with pytest.raises(YamlSchemaError, match="ossMount"):
        parse_yaml_text(
            _doc_with(
                spec={
                    "container": {"image": "img"},
                    "ossMount": "bad",
                }
            )
        )


def test_oss_mount_point_not_mapping():
    with pytest.raises(YamlSchemaError, match="mountPoints"):
        parse_yaml_text(
            _doc_with(
                spec={
                    "container": {"image": "img"},
                    "ossMount": {"mountPoints": ["bad"]},
                }
            )
        )


def test_endpoints_not_list():
    with pytest.raises(YamlSchemaError, match="endpoints"):
        parse_yaml_text(
            _doc_with(
                spec={
                    "container": {"image": "img"},
                    "endpoints": "bad",
                }
            )
        )


def test_endpoint_item_not_mapping():
    with pytest.raises(YamlSchemaError, match="endpoints"):
        parse_yaml_text(
            _doc_with(
                spec={
                    "container": {"image": "img"},
                    "endpoints": ["bad"],
                }
            )
        )


def test_endpoint_missing_name():
    with pytest.raises(YamlSchemaError, match="name"):
        parse_yaml_text(
            _doc_with(
                spec={
                    "container": {"image": "img"},
                    "endpoints": [{}],
                }
            )
        )


def test_endpoint_routing_not_list():
    with pytest.raises(YamlSchemaError, match="routing"):
        parse_yaml_text(
            _doc_with(
                spec={
                    "container": {"image": "img"},
                    "endpoints": [{"name": "x", "routing": "bad"}],
                }
            )
        )


def test_endpoint_routing_item_not_mapping():
    with pytest.raises(YamlSchemaError, match="routing"):
        parse_yaml_text(
            _doc_with(
                spec={
                    "container": {"image": "img"},
                    "endpoints": [{"name": "x", "routing": ["bad"]}],
                }
            )
        )


def test_endpoint_routing_missing_version_weight():
    with pytest.raises(YamlSchemaError, match="version and weight"):
        parse_yaml_text(
            _doc_with(
                spec={
                    "container": {"image": "img"},
                    "endpoints": [{"name": "x", "routing": [{"version": "1"}]}],
                }
            )
        )


def test_endpoint_scaling_not_mapping():
    with pytest.raises(YamlSchemaError, match="scaling"):
        parse_yaml_text(
            _doc_with(
                spec={
                    "container": {"image": "img"},
                    "endpoints": [{"name": "x", "scaling": "bad"}],
                }
            )
        )


def test_endpoint_scheduled_policy_not_mapping():
    with pytest.raises(YamlSchemaError, match="scheduledPolicies"):
        parse_yaml_text(
            _doc_with(
                spec={
                    "container": {"image": "img"},
                    "endpoints": [
                        {
                            "name": "x",
                            "scaling": {"scheduledPolicies": ["bad"]},
                        }
                    ],
                }
            )
        )


def test_document_error_includes_index():
    text = (
        _doc_with(metadata={"name": "ok"}) + "---\n" + _doc_with(apiVersion="wrong/v1")
    )
    with pytest.raises(YamlSchemaError, match="Document #2"):
        parse_yaml_text(text)


def test_registry_config_for_acr_optional_parsed():
    # registryConfig is allowed even when imageRegistryType is ACR
    text = _doc_with(
        spec={
            "container": {
                "image": "img",
                "imageRegistryType": "ACR",
                "registryConfig": {
                    "auth": {"userName": "u"},
                },
            }
        }
    )
    rc = parse_yaml_text(text)[0].container.registry_config
    assert rc and rc.auth and rc.auth.user_name == "u"


def test_endpoint_minimal_keeps_target_version_none():
    text = _doc_with(
        spec={
            "container": {"image": "img"},
            "endpoints": [{"name": "x"}],
        }
    )
    rt = parse_yaml_text(text)[0]
    assert rt.endpoints[0].target_version is None
    assert rt.endpoints[0].routing is None


def test_registry_password_not_in_repr():
    from agentrun_cli._utils.agentruntime_yaml import ParsedRegistryAuth

    auth = ParsedRegistryAuth(user_name="u", password="secret")  # noqa: S106
    rendered = repr(auth)
    assert "secret" not in rendered
    assert "u" in rendered


def test_image_registry_type_must_be_known():
    text = _doc_with(
        spec={
            "container": {"image": "img", "imageRegistryType": "acree"},
        }
    )
    with pytest.raises(YamlSchemaError, match="imageRegistryType"):
        parse_yaml_text(text)


def test_endpoint_routing_non_numeric_weight():
    text = _doc_with(
        spec={
            "container": {"image": "img"},
            "endpoints": [
                {
                    "name": "x",
                    "routing": [{"version": "1", "weight": "abc"}],
                }
            ],
        }
    )
    with pytest.raises(YamlSchemaError, match="weight"):
        parse_yaml_text(text)
