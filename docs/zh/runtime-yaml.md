[English](../en/runtime-yaml.md) | **简体中文**

# `ar runtime` YAML 参考

本页是 [`ar runtime apply`](./runtime.md#apply) 与 [`ar runtime render`](./runtime.md#render)
所消费 YAML 的字段级规范。一份文档描述一个 Agent Runtime；endpoint 嵌入在
`spec.endpoints` 下。CLI 仅支持容器模式 —— `spec.code`、`metadata.tags`、
`metadata.systemTags` 一律拒绝（详见[校验规则](#校验规则)）。

## 目录

- [文档结构](#文档结构)
- [CLI 自动注入](#cli-自动注入)
- [`metadata`](#metadata)
- [`spec.container`](#speccontainer)
- [`spec` 资源与运行时开关](#spec-资源与运行时开关)
- [`spec.protocol`](#specprotocol)
- [`spec.network`](#specnetwork)
- [`spec.healthCheck`](#spechealthcheck)
- [`spec.log`](#speclog)
- [`spec.env`](#specenv)
- [`spec.nas`](#specnas)
- [`spec.ossMount`](#specossmount)
- [`spec.endpoints`](#specendpoints)
- [校验规则](#校验规则)
- [示例](#示例)
- [YAML → SDK 字段映射](#yaml--sdk-字段映射)

## 文档结构

```yaml
apiVersion: agentrun/v1            # 必填，固定值
kind: AgentRuntime                 # 必填，固定值
metadata: {...}                    # 见下文
spec: {...}                        # 见下文
```

支持多文档 YAML（`---` 分隔），每篇按顺序独立解析并依次 apply。空流报错。

## CLI 自动注入

下列字段由 CLI 管控，**不允许**在 YAML 中出现：

| 注入字段 | 值 | 说明 |
|---|---|---|
| `system_tags` | `["x-agentrun-cli"]` | SDK 0.0.200 唯一可写入的标签位；`ar runtime list --created-by-cli` 依赖此标签。 |
| `artifact_type` | `Container` | 本 CLI 只交付容器模式 runtime。 |

当 `spec.endpoints` **整段省略**时，CLI 还会注入：

```yaml
endpoints:
  - name: default
    targetVersion: LATEST
```

显式写 `spec.endpoints: []` 时不会注入 —— 不创建任何 endpoint；
默认还会删除远端已存在的 endpoint（除非加 `--no-prune-endpoints`）。

## `metadata`

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | string | ✓ | 必须匹配 `[a-z0-9-]{1,63}`。映射为 `agent_runtime_name`。 |
| `description` | string |  | 自由文本。 |
| `workspace` | string |  | 工作空间**名称**；与 `workspaceId` 互斥。省略时落到账号默认工作空间。 |
| `workspaceId` | string |  | 工作空间 ID；与 `workspace` 互斥。 |
| `tags` | — | ✗ | 已被 SDK 0.0.200 移除，禁止写入。 |
| `systemTags` | — | ✗ | 由 CLI 管控，禁止写入。 |

## `spec.container`

必填块。定义容器镜像与凭证。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `image` | string | ✓ | OCI 镜像引用。 |
| `command` | list&lt;string&gt; |  | 覆盖镜像的 `ENTRYPOINT`/`CMD`。 |
| `port` | int |  | 容器监听端口。若设置，则覆盖 `spec.port`。 |
| `imageRegistryType` | 枚举 |  | `ACR`、`ACREE`、`CUSTOM` 之一。 |
| `acrInstanceId` | string |  | `imageRegistryType=ACREE` 时建议设置。 |
| `registryConfig` | 映射 | 条件必填 | `imageRegistryType=CUSTOM` 时**必填**；其它情况允许且会被解析。 |

### `spec.container.registryConfig`

```yaml
registryConfig:
  auth:
    userName: <str>
    password: <str>             # 敏感，建议通过环境变量注入
  cert:
    insecure: <bool>
    rootCaCertBase64: <str>
  network:
    vpcId: <str>
    vSwitchId: <str>
    securityGroupId: <str>
```

三个子块（`auth`、`cert`、`network`）各自可选；但 `registryConfig` 本身在
`CUSTOM` 下必填。

## `spec` 资源与运行时开关

| 字段 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `cpu` | float | `2` | 核数。 |
| `memory` | int | `4096` | MB。 |
| `port` | int | `9000` | 与 `spec.container.port` 同时存在时以后者为准。 |
| `diskSize` | int |  | MB。 |
| `enableSessionIsolation` | bool |  |  |
| `credentialName` | string |  | 引用已注册凭证。 |
| `executionRoleArn` | string |  | runtime 承担的 RAM 角色 ARN。 |
| `sessionConcurrencyLimitPerInstance` | int |  |  |
| `sessionIdleTimeoutSeconds` | int |  |  |

## `spec.protocol`

| 字段 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `type` | 枚举 | `HTTP` | `HTTP`、`MCP`、`SUPER_AGENT` 之一。 |
| `settings` | list&lt;ProtocolSetting&gt; |  | 多路由进阶配置。 |

`ProtocolSetting` 字段（除非另注，均为可选字符串）：

| 字段 | 说明 |
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

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `mode` | 枚举 |  | `PUBLIC`（默认）、`PRIVATE`、`PUBLIC_AND_PRIVATE` 之一。 |
| `vpcId` | string | 条件必填 | `mode ∈ {PRIVATE, PUBLIC_AND_PRIVATE}` 时**必填**。 |
| `vswitchIds` | list&lt;string&gt; |  |  |
| `securityGroupId` | string |  |  |

## `spec.healthCheck`

| 字段 | 类型 | 说明 |
|---|---|---|
| `httpGetUrl` | string |  |
| `initialDelaySeconds` | int |  |
| `periodSeconds` | int |  |
| `timeoutSeconds` | int |  |
| `failureThreshold` | int |  |
| `successThreshold` | int |  |

## `spec.log`

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `project` | string | 与 `logstore` 成对 | SLS project。 |
| `logstore` | string | 与 `project` 成对 | SLS logstore。 |

要么两个键同时出现，要么整段省略；只写一个键会被拒绝。

## `spec.env`

`string → string` 的映射。非字符串值会被强制转字符串。

```yaml
env:
  LOG_LEVEL: info
  HTTP_PROXY: http://proxy.internal:8080
```

## `spec.nas`

| 字段 | 类型 | 说明 |
|---|---|---|
| `userId` | int |  |
| `groupId` | int |  |
| `mountPoints` | list&lt;NasMountPoint&gt; | 可选。 |

`NasMountPoint`：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `serverAddr` | string | ✓ |  |
| `mountDir` | string | ✓ | 容器内绝对路径。 |
| `enableTLS` | bool |  |  |

## `spec.ossMount`

| 字段 | 类型 | 说明 |
|---|---|---|
| `mountPoints` | list&lt;OssMountPoint&gt; |  |

`OssMountPoint`：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `bucketName` | string | ✓ |  |
| `mountDir` | string | ✓ | 容器内绝对路径。 |
| `bucketPath` | string |  | bucket 内子路径。 |
| `endpoint` | string |  | OSS endpoint 覆盖。 |
| `readOnly` | bool |  |  |

## `spec.endpoints`

允许三种写法：

| YAML | 行为 |
|---|---|
| 整段省略 | CLI 注入 `[{name: default, targetVersion: LATEST}]`。 |
| `endpoints: []` | 不创建任何 endpoint。`--prune-endpoints`（默认开）时会删除远端已存在的 endpoint。 |
| `endpoints: [...]` | 按 `name` 逐项 reconcile。 |

每个 endpoint 字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | string | ✓ | 同一文档内唯一。 |
| `description` | string |  |  |
| `targetVersion` | string |  | 默认 `LATEST`。与 `routing` 互斥。 |
| `routing` | list&lt;RoutingWeight&gt; |  | 多版本流量分配。与 `targetVersion` 互斥。权重之和必须**正好 100**。 |
| `disablePublicNetworkAccess` | bool |  |  |
| `scaling` | 映射 |  | 见下文。 |

`RoutingWeight`：

```yaml
routing:
  - version: "2"
    weight: 90
  - version: "3"
    weight: 10
```

### `spec.endpoints[i].scaling`

| 字段 | 类型 | 说明 |
|---|---|---|
| `minInstances` | int |  |
| `scheduledPolicies` | list&lt;ScheduledPolicy&gt; |  |

`ScheduledPolicy`：

| 字段 | 类型 | 说明 |
|---|---|---|
| `name` | string |  |
| `scheduleExpression` | string | Cron 表达式。 |
| `startTime` | string |  |
| `endTime` | string |  |
| `target` | int | 与 `minInstances` 同时存在时必须 `>= minInstances`。 |
| `timeZone` | string |  |

## 校验规则

所有违反均以退出码 `2`（"bad input"）退出。下表对解析器
（`src/agentrun_cli/_utils/agentruntime_yaml.py`）是穷尽的。

| 规则 | 触发条件 |
|---|---|
| `apiVersion != agentrun/v1` 或 `kind != AgentRuntime` | 不支持的文档。 |
| `metadata.name` 缺失或不符合 `[a-z0-9-]{1,63}` |  |
| `spec.container` 缺失或不是映射 |  |
| `spec.container.image` 缺失或为空 |  |
| `spec.container.imageRegistryType` 不在 `ACR|ACREE|CUSTOM` 中 |  |
| `imageRegistryType=CUSTOM` 但 `registryConfig` 缺失 |  |
| 出现 `metadata.tags` | SDK 0.0.200 已移除该字段。 |
| 出现 `metadata.systemTags` | 由 CLI 管控。 |
| `metadata.workspace` 与 `metadata.workspaceId` 同时出现 |  |
| 出现 `spec.code` | 本 CLI 仅支持 Container 模式。 |
| `spec.network.mode` 是 `PRIVATE`/`PUBLIC_AND_PRIVATE` 但缺 `vpcId` |  |
| `spec.log.project` 与 `spec.log.logstore` 单边出现 |  |
| `spec.env` 不是映射，或键不是字符串 |  |
| `spec.nas.mountPoints[*]` 缺 `serverAddr` 或 `mountDir` |  |
| `spec.ossMount.mountPoints[*]` 缺 `bucketName` 或 `mountDir` |  |
| `spec.endpoints` 不是列表，或 `endpoints[*]` 不是映射 |  |
| `spec.endpoints[*].name` 缺失或重复 |  |
| 同一 endpoint 同时设置 `targetVersion` 与 `routing` |  |
| `routing` 为空、缺 `version`/`weight`、`weight` 非数字，或权重之和 ≠ 100 |  |
| `scaling.scheduledPolicies[*].target < scaling.minInstances` |  |

## 示例

### 最小示例

```yaml
apiVersion: agentrun/v1
kind: AgentRuntime
metadata:
  name: my-agent
spec:
  container:
    image: registry.cn-hangzhou.aliyuncs.com/my-ns/my-agent:v1
```

经 CLI 自动注入后等价于：

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

### 生产示例 —— ACREE + 私网 + NAS + 金丝雀

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
  diskSize: 10240                # MB（10 GiB）
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

### 自建 registry

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
        password: ${REGISTRY_PASSWORD}     # apply 前先做模板替换
      cert:
        insecure: false
      network:
        vpcId: vpc-xxx
        vSwitchId: vsw-xxx
        securityGroupId: sg-xxx
```

## YAML → SDK 字段映射

需要与 SDK（`agentrun.agent_runtime.model`）交叉对照时：

| YAML 键 | SDK 字段 |
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
| *（自动注入）* `system_tags` | `system_tags = ["x-agentrun-cli"]` |
| *（自动注入）* `artifact_type` | `artifact_type = "Container"` |
