---
name: run-your-agents
description: 将当前项目整理并部署为 AgentRun Runtime，使用 agentrun-cli 的 ar runtime apply 与 cloudBuild 能力。Use when 用户要求把项目发布、部署、上线到 AgentRun runtime，提到 agentruntime.yaml、ar runtime apply、cloudBuild、docker-image-builder、AgentRun CLI runtime 部署，或需要补 scripts/setup.sh 和 scripts/start.sh。
---

# AgentRun CLI Runtime 部署

## 基本流程

1. 检查项目启动方式、依赖安装方式和运行端口，确定 runtime 名称、目标镜像和镜像仓库类型。
2. 补充可重复执行的 `scripts/setup.sh`。脚本在云端构建环境中运行，用于安装依赖、构建前端或准备运行目录。
3. 补充 `scripts/start.sh`。脚本必须读取环境变量 `PORT`，默认使用 `9000`，并绑定 `0.0.0.0`。
4. 编写 `agentruntime.yaml`，在 `spec.container.cloudBuild` 中声明云构建参数。
5. 运行 `ar runtime apply -f agentruntime.yaml --timeout 20m`。命令默认等待 runtime 和 endpoint 到终态。
6. 成功后从输出中的 `endpoints[].publicUrl` 获取公网访问地址，并按项目协议做访问验证。

## 脚本要求

`scripts/setup.sh` 应该可重复执行。只做构建期动作，例如安装依赖、编译前端、生成静态资源、准备运行目录。不要在脚本中写入密钥；密钥放入 `.env` 或运行环境变量，并确保不会进入 VCS。

`scripts/start.sh` 应该只负责启动服务。示例：

```bash
#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-9000}"
HOST="${HOST:-0.0.0.0}"

exec your-server-command --host "$HOST" --port "$PORT"
```

## Runtime YAML 示例

```yaml
apiVersion: agentrun/v1
kind: AgentRuntime
metadata:
  name: my-runtime
spec:
  container:
    image: registry.cn-hangzhou.aliyuncs.com/my-ns/my-agent:v1
    command: ["bash", "-lc", "exec bash scripts/start.sh"]
    cloudBuild:
      dir: .
      setupScript: scripts/setup.sh
      timeoutMinutes: 20
      cpu: 4
      memory: 8192
  port: 9000
```

`spec.container.cloudBuild` 会在部署前调用 docker-image-builder 云构建镜像；目标镜像就是 `spec.container.image`。

## 镜像仓库

- `cloudBuild` YAML 不支持 `registryMode` 字段；仅支持标准 OCI registry 模式。
- 如果设置了 `DOCKER_IMAGE_BUILDER_BINPATH`，agentrun-cli 会优先使用该路径的 docker-image-builder。
- 镜像仓库推送账号可通过 `DOCKER_IMAGE_BUILDER_USERNAME` 和 `DOCKER_IMAGE_BUILDER_PASSWORD` 提供；docker-image-builder 也兼容 `DOCKER_IMAGE_BUILDER_REGISTRY_USERNAME` 和 `DOCKER_IMAGE_BUILDER_REGISTRY_PASSWORD`。
- runtime 拉取私有镜像时，在 `spec.container.registryConfig.auth.userName` 和 `password` 中配置仓库账号密码；字段名必须是 `userName`，不是 `username`。
- 使用 ACR 企业版镜像时，可设置 `spec.container.imageRegistryType: ACREE` 和 `spec.container.acrInstanceId`。

## 验证命令

```bash
ar runtime render -f agentruntime.yaml
ar runtime apply -f agentruntime.yaml --timeout 20m
```

`render` 用于部署前校验和预览 SDK 输入；`apply` 默认等待 runtime 和 endpoint 到终态。
