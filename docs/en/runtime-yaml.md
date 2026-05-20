**English** | [简体中文](../zh/runtime-yaml.md)

# `ar runtime` YAML Reference

This page is the field-level specification for the YAML consumed by
[`ar runtime apply`](./runtime.md#apply) and
[`ar runtime render`](./runtime.md#render). One document describes one Agent
Runtime; endpoints are embedded under `spec.endpoints`. The CLI is intentionally
container-only — `spec.code`, `metadata.tags`, and `metadata.systemTags` are
rejected (see [Validation rules](#validation-rules)).

## Contents

- [Document shape](#document-shape)
- [CLI auto-injection](#cli-auto-injection)
- [`metadata`](#metadata)
- [`spec.container`](#speccontainer)
- [`spec` resource & runtime knobs](#spec-resource--runtime-knobs)
- [`spec.protocol`](#specprotocol)
- [`spec.network`](#specnetwork)
- [`spec.healthCheck`](#spechealthcheck)
- [`spec.log`](#speclog)
- [`spec.env`](#specenv)
- [`spec.nas`](#specnas)
- [`spec.ossMount`](#specossmount)
- [`spec.endpoints`](#specendpoints)
- [Validation rules](#validation-rules)
- [Examples](#examples)
- [YAML → SDK field map](#yaml--sdk-field-map)

## Document shape

```yaml
apiVersion: agentrun/v1            # required, fixed string
kind: AgentRuntime                 # required, fixed string
metadata: {...}                    # see below
spec: {...}                        # see below
```

Multi-document YAML (`---` separators) is supported; each document is parsed and
applied independently in order. An empty stream is an error.

## CLI auto-injection

Two fields are managed by the CLI and **must not** appear in YAML:

| Injected field | Value | Notes |
|---|---|---|
| `system_tags` | `["x-agentrun-cli"]` | The only label slot SDK 0.0.200 still exposes; powers `ar runtime list --created-by-cli`. |
| `artifact_type` | `Container` | This CLI only ships container-mode runtimes. |

When `spec.endpoints` is **omitted entirely**, the CLI also injects:

```yaml
endpoints:
  - name: default
    targetVersion: LATEST
```

`spec.endpoints: []` (explicitly empty) is honored — no endpoint is created and
existing ones are pruned (unless `--no-prune-endpoints`).

## `metadata`

| Key | Type | Required | Notes |
|---|---|---|---|
| `name` | string | ✓ | Must match `[a-z0-9-]{1,63}`. Becomes `agent_runtime_name`. |
| `description` | string |  | Free text. |
| `workspace` | string |  | Workspace **name**; mutually exclusive with `workspaceId`. Defaults to the account-level workspace when omitted. |
| `workspaceId` | string |  | Workspace ID; mutually exclusive with `workspace`. |
| `tags` | — | ✗ | Rejected — SDK 0.0.200 removed user-facing tags. |
| `systemTags` | — | ✗ | Rejected — managed by the CLI. |

## `spec.container`

Required block. Defines the container image and registry credentials.

| Key | Type | Required | Notes |
|---|---|---|---|
| `image` | string | ✓ | OCI image reference. |
| `command` | list&lt;string&gt; |  | Overrides image `ENTRYPOINT`/`CMD`. |
| `port` | int |  | Container listen port. If set, wins over `spec.port`. |
| `imageRegistryType` | enum |  | One of `ACR`, `ACREE`, `CUSTOM`. |
| `acrInstanceId` | string |  | Recommended when `imageRegistryType=ACREE`. |
| `registryConfig` | mapping | conditional | **Required** when `imageRegistryType=CUSTOM`; allowed (and parsed) otherwise. |

### `spec.container.registryConfig`

```yaml
registryConfig:
  auth:
    userName: <str>
    password: <str>             # sensitive — prefer env-var injection
  cert:
    insecure: <bool>
    rootCaCertBase64: <str>
  network:
    vpcId: <str>
    vSwitchId: <str>
    securityGroupId: <str>
```

All three sub-blocks (`auth`, `cert`, `network`) are individually optional, but
`registryConfig` itself is mandatory under `CUSTOM`.

## `spec` resource & runtime knobs

| Key | Type | Default | Notes |
|---|---|---|---|
| `cpu` | float | `2` | Cores. |
| `memory` | int | `4096` | MB. |
| `port` | int | `9000` | Falls back behind `spec.container.port` if both are set. |
| `diskSize` | int |  | MB. |
| `enableSessionIsolation` | bool |  |  |
| `credentialName` | string |  | Reference to a registered credential. |
| `executionRoleArn` | string |  | RAM role ARN the runtime assumes. |
| `sessionConcurrencyLimitPerInstance` | int |  |  |
| `sessionIdleTimeoutSeconds` | int |  |  |

## `spec.protocol`

| Key | Type | Default | Notes |
|---|---|---|---|
| `type` | enum | `HTTP` | One of `HTTP`, `MCP`, `SUPER_AGENT`. |
| `settings` | list&lt;ProtocolSetting&gt; |  | Advanced multi-route definitions. |

`ProtocolSetting` fields (all optional, free-form strings unless noted):

| Key | Notes |
|---|---|
| `type` |  |
| `name` |  |
| `path` |  |
| `pathPrefix` |  |
| `method` |  |
| `requestContentType` |  |
| `responseContentType` |  |
| `headers` |  |
| `inputBodyJsonSchema` |  |
| `outputBodyJsonSchema` |  |
| `a2aAgentCard` |  |
| `a2aAgentCardUrl` |  |
| `config` |  |

## `spec.network`

| Key | Type | Required | Notes |
|---|---|---|---|
| `mode` | enum |  | One of `PUBLIC` (default), `PRIVATE`, `PUBLIC_AND_PRIVATE`. |
| `vpcId` | string | conditional | **Required** when `mode ∈ {PRIVATE, PUBLIC_AND_PRIVATE}`. |
| `vswitchIds` | list&lt;string&gt; |  |  |
| `securityGroupId` | string |  |  |

## `spec.healthCheck`

| Key | Type | Notes |
|---|---|---|
| `httpGetUrl` | string |  |
| `initialDelaySeconds` | int |  |
| `periodSeconds` | int |  |
| `timeoutSeconds` | int |  |
| `failureThreshold` | int |  |
| `successThreshold` | int |  |

## `spec.log`

| Key | Type | Required | Notes |
|---|---|---|---|
| `project` | string | paired with `logstore` | SLS project. |
| `logstore` | string | paired with `project` | SLS logstore. |

Either both keys are set, or the whole block is omitted; setting one without
the other is rejected.

## `spec.env`

Map of `string → string`. Non-string values are coerced to strings.

```yaml
env:
  LOG_LEVEL: info
  HTTP_PROXY: http://proxy.internal:8080
```

## `spec.nas`

| Key | Type | Notes |
|---|---|---|
| `userId` | int |  |
| `groupId` | int |  |
| `mountPoints` | list&lt;NasMountPoint&gt; | Optional. |

`NasMountPoint`:

| Key | Type | Required | Notes |
|---|---|---|---|
| `serverAddr` | string | ✓ |  |
| `mountDir` | string | ✓ | Absolute path inside the container. |
| `enableTLS` | bool |  |  |

## `spec.ossMount`

| Key | Type | Notes |
|---|---|---|
| `mountPoints` | list&lt;OssMountPoint&gt; |  |

`OssMountPoint`:

| Key | Type | Required | Notes |
|---|---|---|---|
| `bucketName` | string | ✓ |  |
| `mountDir` | string | ✓ | Absolute path inside the container. |
| `bucketPath` | string |  | Sub-path inside the bucket. |
| `endpoint` | string |  | OSS endpoint override. |
| `readOnly` | bool |  |  |

## `spec.endpoints`

Three shapes are allowed:

| YAML | Behaviour |
|---|---|
| key absent | CLI injects `[{name: default, targetVersion: LATEST}]`. |
| `endpoints: []` | No endpoints are created. With `--prune-endpoints` (default), any existing endpoint is deleted. |
| `endpoints: [...]` | Each item is reconciled by name. |

Per-endpoint fields:

| Key | Type | Required | Notes |
|---|---|---|---|
| `name` | string | ✓ | Unique within the document. |
| `description` | string |  |  |
| `targetVersion` | string |  | Defaults to `LATEST`. Mutually exclusive with `routing`. |
| `routing` | list&lt;RoutingWeight&gt; |  | Multi-version traffic split. Mutually exclusive with `targetVersion`. Weights must sum to **exactly 100**. |
| `disablePublicNetworkAccess` | bool |  |  |
| `scaling` | mapping |  | See below. |

`RoutingWeight`:

```yaml
routing:
  - version: "2"
    weight: 90
  - version: "3"
    weight: 10
```

### `spec.endpoints[i].scaling`

| Key | Type | Notes |
|---|---|---|
| `minInstances` | int |  |
| `scheduledPolicies` | list&lt;ScheduledPolicy&gt; |  |

`ScheduledPolicy`:

| Key | Type | Notes |
|---|---|---|
| `name` | string |  |
| `scheduleExpression` | string | Cron expression. |
| `startTime` | string |  |
| `endTime` | string |  |
| `target` | int | Must be `>= minInstances` when both are set. |
| `timeZone` | string |  |

## Validation rules

All violations exit with code `2` ("bad input"). The list below is exhaustive
for the parser (`src/agentrun_cli/_utils/agentruntime_yaml.py`).

| Rule | Trigger |
|---|---|
| `apiVersion != agentrun/v1` or `kind != AgentRuntime` | Unsupported document. |
| `metadata.name` missing or fails `[a-z0-9-]{1,63}` |  |
| `spec.container` missing or not a mapping |  |
| `spec.container.image` missing or empty |  |
| `spec.container.imageRegistryType` not in `ACR|ACREE|CUSTOM` |  |
| `imageRegistryType=CUSTOM` but `registryConfig` missing |  |
| `metadata.tags` present | SDK 0.0.200 removed the field. |
| `metadata.systemTags` present | Managed by the CLI. |
| `metadata.workspace` + `metadata.workspaceId` both set |  |
| `spec.code` present | Container-only CLI. |
| `spec.network.mode` is `PRIVATE`/`PUBLIC_AND_PRIVATE` without `vpcId` |  |
| `spec.log.project` and `spec.log.logstore` not paired |  |
| `spec.env` not a mapping, or non-string keys |  |
| `spec.nas.mountPoints[*]` missing `serverAddr` or `mountDir` |  |
| `spec.ossMount.mountPoints[*]` missing `bucketName` or `mountDir` |  |
| `spec.endpoints` not a list, or `endpoints[*]` not a mapping |  |
| `spec.endpoints[*].name` missing or duplicated |  |
| Endpoint with both `targetVersion` and `routing` |  |
| `routing` empty, items missing `version`/`weight`, non-numeric `weight`, or sum ≠ 100 |  |
| `scaling.scheduledPolicies[*].target < scaling.minInstances` |  |

## Examples

### Minimal

```yaml
apiVersion: agentrun/v1
kind: AgentRuntime
metadata:
  name: my-agent
spec:
  container:
    image: registry.cn-hangzhou.aliyuncs.com/my-ns/my-agent:v1
```

After CLI auto-injection this is equivalent to:

```yaml
apiVersion: agentrun/v1
kind: AgentRuntime
metadata: {name: my-agent}
spec:
  container:
    image: registry.cn-hangzhou.aliyuncs.com/my-ns/my-agent:v1
  endpoints:
    - name: default
      targetVersion: LATEST
# system_tags=["x-agentrun-cli"], artifact_type=Container
```

### Production — ACREE + private network + NAS + canary endpoint

```yaml
apiVersion: agentrun/v1
kind: AgentRuntime
metadata:
  name: my-agent
  workspace: prod-ws
spec:
  container:
    image: registry-vpc.cn-hangzhou.cr.aliyuncs.com/my-ns/my-agent:v3
    command: ["python", "app.py"]
    imageRegistryType: ACREE
    acrInstanceId: cri-xxxxx
  cpu: 4
  memory: 8192
  diskSize: 10240                # MB (10 GiB)
  enableSessionIsolation: true
  network:
    mode: PUBLIC_AND_PRIVATE
    vpcId: vpc-xxx
    vswitchIds: [vsw-xxx]
    securityGroupId: sg-xxx
  log:
    project: my-agent-logs
    logstore: runtime
  env:
    LOG_LEVEL: info
  nas:
    userId: 1000
    groupId: 1000
    mountPoints:
      - serverAddr: xxxx.nas.aliyuncs.com:/
        mountDir: /mnt/nas
        enableTLS: true
  endpoints:
    - name: prod
      targetVersion: LATEST
      scaling:
        minInstances: 2
    - name: canary
      routing:
        - {version: "2", weight: 90}
        - {version: "3", weight: 10}
      disablePublicNetworkAccess: true
```

### Custom registry

```yaml
apiVersion: agentrun/v1
kind: AgentRuntime
metadata: {name: my-agent}
spec:
  container:
    image: registry.example.com/team/agent:v1
    imageRegistryType: CUSTOM
    registryConfig:
      auth:
        userName: deploy-bot
        password: ${REGISTRY_PASSWORD}     # interpolate before piping into apply
      cert:
        insecure: false
      network:
        vpcId: vpc-xxx
        vSwitchId: vsw-xxx
        securityGroupId: sg-xxx
```

## YAML → SDK field map

For users who need to cross-reference the SDK
(`agentrun.agent_runtime.model`):

| YAML key | SDK field |
|---|---|
| `metadata.name` | `agent_runtime_name` |
| `metadata.description` | `description` |
| `metadata.workspace` | `workspace_name` |
| `metadata.workspaceId` | `workspace_id` |
| `spec.container.image` | `container_configuration.image` |
| `spec.container.command` | `container_configuration.command` |
| `spec.container.port` | `container_configuration.port` |
| `spec.container.imageRegistryType` | `container_configuration.image_registry_type` |
| `spec.container.acrInstanceId` | `container_configuration.acr_instance_id` |
| `spec.container.registryConfig.*` | `container_configuration.registry_config.*` |
| `spec.cpu / memory / port / diskSize` | `cpu / memory / port / disk_size` |
| `spec.enableSessionIsolation` | `enable_session_isolation` |
| `spec.protocol.type` | `protocol_configuration.type` |
| `spec.protocol.settings` | `protocol_configuration.protocol_settings` |
| `spec.network.{mode,vpcId,vswitchIds,securityGroupId}` | `network_configuration.{network_mode,vpc_id,vswitch_ids,security_group_id}` |
| `spec.healthCheck.*` | `health_check_configuration.*` |
| `spec.log.{project,logstore}` | `log_configuration.{project,logstore}` |
| `spec.env` | `environment_variables` |
| `spec.credentialName` | `credential_name` |
| `spec.executionRoleArn` | `execution_role_arn` |
| `spec.sessionConcurrencyLimitPerInstance` | `session_concurrency_limit_per_instance` |
| `spec.sessionIdleTimeoutSeconds` | `session_idle_timeout_seconds` |
| `spec.nas.*` | `nas_config.*` |
| `spec.ossMount.*` | `oss_mount_config.*` |
| `spec.endpoints[i].name` | `agent_runtime_endpoint_name` |
| `spec.endpoints[i].description` | `description` |
| `spec.endpoints[i].targetVersion` | `target_version` |
| `spec.endpoints[i].routing` | `routing_configuration.version_weights` |
| `spec.endpoints[i].disablePublicNetworkAccess` | `disable_public_network_access` |
| `spec.endpoints[i].scaling.*` | `scaling_config.*` |
| *(auto-injected)* `system_tags` | `system_tags = ["x-agentrun-cli"]` |
| *(auto-injected)* `artifact_type` | `artifact_type = "Container"` |
