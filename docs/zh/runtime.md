[English](../en/runtime.md) | **简体中文**

# ar runtime

通过 YAML 声明式管理 **Agent Runtime**。本命令组支持基于已有 OCI 镜像部署，也支持
通过 `spec.container.cloudBuild` 在部署前调用云上构建。Endpoint 嵌入同一份
YAML；用户不写时 CLI 会自动注入一个名为 `default` 的 endpoint（`targetVersion=LATEST`）。

别名：`ar rt`。

> **提示：** 执行任何命令前，请先完成 [Prerequisites](./index.md#prerequisites) 中的
> 两步一次性设置。角色或策略缺失会以退出码 `3` 暴露。

## 命令

- [apply](#apply) — 配置后先云上构建，再从 YAML create-or-update。
- [cloud-build](#cloud-build) — 只按 YAML 构建镜像，不部署 runtime。
- [render](#render) — 校验 + 渲染为 SDK 输入（不调用服务端）。
- [get](#get) — 按名字获取单个 runtime。
- [list](#list) — 列出 runtime；可用 `--created-by-cli` 或 `--workspace` 过滤。
- [delete](#delete) — 删除 runtime（默认等待）。
- [status](#status) — 查看（可选等待）终态状态。

退出码（在全局表的基础上扩展）：

| 码 | 含义 |
|----|------|
| `5` | Runtime 或 endpoint 进入 `CREATE_FAILED`、`UPDATE_FAILED` 或 `DELETE_FAILED`。 |
| `6` | 轮询超过 `--timeout`。 |

---

## apply

```
ar runtime apply -f FILE [--wait/--no-wait] [--timeout DURATION]
                       [--prune-endpoints/--no-prune-endpoints]
```

### Options

| Flag | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `-f`, `--file` | path | yes |  | YAML 文件路径（支持多文档）。 |
| `--wait/--no-wait` | flag | no | `--wait` | 轮询 runtime + endpoints 到终态。`--no-wait` 时仅提交 runtime 创建/更新，**不会 reconcile endpoint** —— 后端在 runtime 处于 `CREATING`/`UPDATING` 时会拒绝 endpoint create/update。等 runtime 到 `READY` 后再 apply 一次即可。 |
| `--timeout` | duration | no | `10m` | 轮询超时。支持 `Ns` / `Nm` / `Nh` 或裸秒数。 |
| `--prune-endpoints/--no-prune-endpoints` | flag | no | `--prune-endpoints` | 删除远端存在但 YAML 缺失的 endpoint。 |

YAML 中省略 `cpu` / `memory` / `port` 时，CLI 会自动注入合理默认值（2 核 /
4096 MB / 9000）—— 后端对这三个字段的 null 会回复 HTTP 400。若 YAML 写了
`spec.container.cloudBuild`，`apply` 会先调用 docker-image-builder，再提交
runtime，最终仍部署同一个 image 引用。docker-image-builder 默认会跳过已存在的目标
tag。

### Examples

```bash
# 最小可用：仅容器，CLI 自动注入默认 endpoint
cat > runtime.yaml <<'EOF'
apiVersion: agentrun/v1
kind: AgentRuntime
metadata: {name: my-agent}
spec:
  container:
    image: registry.cn-hangzhou.aliyuncs.com/my-ns/my-agent:v1
EOF
ar runtime apply -f runtime.yaml

# 先云上构建，再部署 runtime
cat > runtime-build.yaml <<EOF
apiVersion: agentrun/v1
kind: AgentRuntime
metadata: {name: my-agent}
spec:
  container:
    image: registry.cn-hangzhou.aliyuncs.com/my-ns/my-agent:v1
    cloudBuild:
      dir: .
      setupScript: scripts/setup.sh
      baseContainerConfig:
        image: serverless-registry.cn-hangzhou.cr.aliyuncs.com/functionai/docker-image-builder-worker:20260514-111141-2d80effe
EOF
ar runtime apply -f runtime-build.yaml

# CI 场景：异步提交不等待
ar runtime apply -f runtime.yaml --no-wait

# 自定义超时
ar runtime apply -f runtime.yaml --timeout 20m

# 在 YAML 之间迁移时关闭 prune
ar runtime apply -f runtime.yaml --no-prune-endpoints
```


---

## cloud-build

```
ar runtime cloud-build -f FILE
```

### Options

| Flag | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `-f`, `--file` | path | yes |  | YAML 文件路径（支持多文档）。 |

只执行 `spec.container.cloudBuild` 构建步骤，不创建或更新 runtime。每篇文档都会调用
docker-image-builder；builder 成功退出时输出 `completed`。docker-image-builder
默认会跳过已存在的目标 tag。

`cloud-build` 使用与 `apply` 相同的凭据来源：阿里云 UID/AK/SK 读取 AgentRun profile；
镜像仓库用户名和密码优先读 YAML 的 `cloudBuild.registry`，否则读取
`DOCKER_IMAGE_BUILDER_USERNAME` / `DOCKER_IMAGE_BUILDER_PASSWORD`。

### Examples

```bash
# 只构建，不部署 runtime
ar runtime cloud-build -f runtime-build.yaml
```

---

## render

```
ar runtime render -f FILE
```

### Options

| Flag | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `-f`, `--file` | path | yes |  | YAML 文件路径（支持多文档）。 |

校验 YAML 并应用 CLI 自动注入（`system_tags=["x-agentrun-cli"]`、
`artifact_type=Container`、`spec.endpoints` 缺省时注入默认 endpoint），
以 JSON 形式打印 SDK create-input，不调用服务端。YAML 包含 `cloudBuild` 时，`render`
还会输出 `cloudBuildPlan` 预览，但不会检查 registry，也不会构建镜像。可在 `apply`
之前用于预览。

---

## get

```
ar runtime get NAME
```

以 JSON 形式展示一个 Agent Runtime。不存在则退出码 `1`。

### Examples

```bash
ar runtime get my-agent
ar runtime get my-agent --output quiet     # 只打印名字
```

---

## list

```
ar runtime list [--created-by-cli] [--workspace NAME]
```

### Options

| Flag | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `--created-by-cli` | flag | no | false | 只显示带 `x-agentrun-cli` 系统标签的 runtime。 |
| `--workspace` | string | no |  | 按工作空间名过滤。 |

### Examples

```bash
ar runtime list
ar runtime list --created-by-cli
ar runtime list --output table
```

---

## delete

```
ar runtime delete NAME [--wait/--no-wait] [--timeout DURATION] [--yes]
```

### Options

| Flag | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `--wait/--no-wait` | flag | no | `--wait` | 阻塞直到资源消失（或失败）。 |
| `--timeout` | duration | no | `5m` | 轮询超时。 |
| `--yes` | flag | no | false | 跳过交互式确认。 |

### Examples

```bash
ar runtime delete my-agent --yes
ar runtime delete my-agent --no-wait
```

---

## status

```
ar runtime status NAME [--wait] [--timeout DURATION]
```

### Options

| Flag | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `--wait` | flag | no | false | 轮询到 READY / *_FAILED。 |
| `--timeout` | duration | no | `10m` | 轮询超时（仅 `--wait` 有效）。 |

### Examples

```bash
ar runtime status my-agent
ar runtime status my-agent --wait --timeout 20m
```

---

## YAML schema

完整字段参考、CLI 自动注入规则、校验表与可直接复用的示例（最小、生产、自建 registry）
见 [**runtime-yaml.md**](./runtime-yaml.md)。
