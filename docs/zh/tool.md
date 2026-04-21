[English](../en/tool.md) | **简体中文**

# ar tool

管理 **Tool** 资源 —— Super Agent 可调用的 MCP Server 和 FunctionCall 工具。
支持多种创建方式：`MCP_REMOTE`（代理外部 SSE 服务）、`MCP_BUNDLE`（运行预构建
镜像）、`CODE_PACKAGE`（用户提供代码）、`OPENAPI_IMPORT`（从 OpenAPI 生成）。

## 子命令

- [create](#create)
- [get](#get)
- [list](#list)
- [update](#update)
- [delete](#delete)
- [list-tools](#list-tools)
- [invoke](#invoke)

---

## create

```
ar tool create --name <name> --tool-type <MCP|FUNCTIONCALL> --create-method <method> [options]
```

### 参数

| Flag | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--name` | string | 是 |  | 全局唯一工具名。 |
| `--tool-type` | string | 是 |  | `MCP` 或 `FUNCTIONCALL`。 |
| `--create-method` | string | 是 |  | `MCP_REMOTE` / `MCP_BUNDLE` / `CODE_PACKAGE` / `OPENAPI_IMPORT`。 |
| `--description` | string | 否 |  | 描述。 |
| `--protocol-spec` | string | 否 |  | 内联 JSON 字符串 **或** 指向 JSON 文件的路径。 |
| `--proxy-enabled / --no-proxy-enabled` | flag | 否 |  | 是否启用 MCP 代理（仅 `MCP_REMOTE`）。 |
| `--session-affinity` | string | 否 |  | `MCP_SSE` 或 `MCP_STREAMABLE`。 |
| `--image` | string | 否 |  | 容器镜像（`MCP_BUNDLE` / `CODE_PACKAGE`）。 |
| `--port` | int | 否 |  | 容器端口。 |
| `--command` | string | 否 |  | 容器启动命令。 |
| `--timeout` | int | 否 |  | 请求超时（秒）。 |
| `--memory` | int | 否 |  | 内存（MB）。 |
| `--cpu` | float | 否 |  | CPU 核数。 |
| `--credential` | string | 否 |  | 凭证名。 |
| `--env` | multi | 否 |  | 环境变量 `KEY=VALUE`，可重复。 |
| `--from-file` | path | 否 |  | 完整 `CreateToolInputV2` 的 JSON 文件。 |

### 示例

```bash
# 代理外部 MCP SSE 服务
ar tool create --name weather-mcp \
  --tool-type MCP --create-method MCP_REMOTE \
  --protocol-spec '{"mcpServers":{"w":{"url":"https://example.com/sse"}}}'

# 容器化 MCP
ar tool create --name custom-mcp \
  --tool-type MCP --create-method MCP_BUNDLE \
  --image registry.example.com/custom-mcp:v1 --port 8080

# 带环境变量的 FunctionCall
ar tool create --name calc-fc \
  --tool-type FUNCTIONCALL --create-method CODE_PACKAGE \
  --image registry.example.com/calc:latest \
  --env LOG_LEVEL=info --env REGION=cn-hangzhou
```

---

## get

```
ar tool get --name <name>
```

### 参数

| Flag | 类型 | 必填 | 说明 |
|------|------|------|------|
| `--name` | string | 是 | 工具名。 |

### 示例

```bash
ar tool get --name weather-mcp
```

---

## list

```
ar tool list [--tool-type <type>] [--page-number <n>] [--page-size <n>]
```

### 参数

| Flag | 类型 | 必填 | 说明 |
|------|------|------|------|
| `--tool-type` | string | 否 | 过滤：`MCP` 或 `FUNCTIONCALL`。 |
| `--page-number` | int | 否 | 页码。 |
| `--page-size` | int | 否 | 每页条数。 |

### 示例

```bash
ar tool list
ar tool list --tool-type MCP --page-size 50
```

---

## update

```
ar tool update --name <name> [options]
```

### 参数

| Flag | 类型 | 必填 | 说明 |
|------|------|------|------|
| `--name` | string | 是 | 要更新的工具名。 |
| `--description` | string | 否 | 新描述。 |
| `--protocol-spec` | string | 否 | 新 protocol spec。 |
| `--timeout` | int | 否 | 新超时。 |
| `--memory` | int | 否 | 新内存（MB）。 |
| `--cpu` | float | 否 | 新 CPU 核数。 |
| `--credential` | string | 否 | 新凭证名。 |
| `--proxy-enabled / --no-proxy-enabled` | flag | 否 | 切换 MCP 代理开关。 |
| `--session-affinity` | string | 否 | 新 session affinity。 |
| `--from-file` | path | 否 | 更新字段的 JSON 文件。 |

### 示例

```bash
ar tool update --name weather-mcp --timeout 60
ar tool update --name custom-mcp --proxy-enabled
```

---

## delete

```
ar tool delete --name <name>
```

### 参数

| Flag | 类型 | 必填 | 说明 |
|------|------|------|------|
| `--name` | string | 是 | 要删除的工具名。 |

### 示例

```bash
ar tool delete --name weather-mcp
```

---

## list-tools

列出某个 Tool 暴露的子工具（函数/方法）。

```
ar tool list-tools --name <name>
```

### 参数

| Flag | 类型 | 必填 | 说明 |
|------|------|------|------|
| `--name` | string | 是 | 工具名。 |

### 示例

```bash
ar tool list-tools --name weather-mcp
```

---

## invoke

直接调用某个子工具。适合把 Tool 接入 Super Agent 前先验证行为，或在脚本化
流水线里使用。

```
ar tool invoke --name <name> --sub-tool <fn> [--arguments <json> | --arguments-file <path>]
```

### 参数

| Flag | 类型 | 必填 | 说明 |
|------|------|------|------|
| `--name` | string | 是 | 工具名。 |
| `--sub-tool` | string | 是 | 子工具（函数）名。 |
| `--arguments` | string | 否 | 内联 JSON 参数。与 `--arguments-file` 互斥。 |
| `--arguments-file` | path | 否 | JSON 参数文件。 |

### 示例

```bash
ar tool invoke --name weather-mcp \
  --sub-tool get_weather \
  --arguments '{"city": "杭州"}'

ar tool invoke --name custom-mcp \
  --sub-tool translate \
  --arguments-file ./args.json
```
