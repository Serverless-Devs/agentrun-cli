**English** | [简体中文](../zh/tool.md)

# ar tool

Manage **Tool** resources — MCP servers and FunctionCall tools that a super agent
can invoke. Supports several creation methods: `MCP_REMOTE` (proxy an external SSE
server), `MCP_BUNDLE` (run a prebuilt image), `CODE_PACKAGE` (user-supplied code),
and `OPENAPI_IMPORT` (generate from OpenAPI).

## Commands

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

### Options

| Flag | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `--name` | string | yes |  | Unique tool name. |
| `--tool-type` | string | yes |  | `MCP` or `FUNCTIONCALL`. |
| `--create-method` | string | yes |  | `MCP_REMOTE` / `MCP_BUNDLE` / `CODE_PACKAGE` / `OPENAPI_IMPORT`. |
| `--description` | string | no |  | Description. |
| `--protocol-spec` | string | no |  | Inline protocol-spec JSON **or** path to a JSON file. |
| `--proxy-enabled / --no-proxy-enabled` | flag | no |  | Enable MCP proxy (MCP_REMOTE only). |
| `--session-affinity` | string | no |  | `MCP_SSE` or `MCP_STREAMABLE`. |
| `--image` | string | no |  | Container image (MCP_BUNDLE / CODE_PACKAGE). |
| `--port` | int | no |  | Container port. |
| `--command` | string | no |  | Container startup command. |
| `--timeout` | int | no |  | Request timeout (seconds). |
| `--memory` | int | no |  | Memory in MB. |
| `--cpu` | float | no |  | CPU cores. |
| `--credential` | string | no |  | Credential name. |
| `--env` | multi | no |  | Environment variable `KEY=VALUE`, repeatable. |
| `--from-file` | path | no |  | JSON file with a full `CreateToolInputV2`. |

### Examples

```bash
# Remote MCP server (SSE)
ar tool create --name weather-mcp \
  --tool-type MCP --create-method MCP_REMOTE \
  --protocol-spec '{"mcpServers":{"w":{"url":"https://example.com/sse"}}}'

# Container-based MCP
ar tool create --name custom-mcp \
  --tool-type MCP --create-method MCP_BUNDLE \
  --image registry.example.com/custom-mcp:v1 --port 8080

# FunctionCall with environment variables
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

### Options

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--name` | string | yes | Tool name. |

### Examples

```bash
ar tool get --name weather-mcp
```

---

## list

```
ar tool list [--tool-type <type>] [--page-number <n>] [--page-size <n>]
```

### Options

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--tool-type` | string | no | Filter: `MCP` or `FUNCTIONCALL`. |
| `--page-number` | int | no | Page number. |
| `--page-size` | int | no | Page size. |

### Examples

```bash
ar tool list
ar tool list --tool-type MCP --page-size 50
```

---

## update

```
ar tool update --name <name> [options]
```

### Options

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--name` | string | yes | Tool to update. |
| `--description` | string | no | New description. |
| `--protocol-spec` | string | no | New protocol spec. |
| `--timeout` | int | no | New timeout. |
| `--memory` | int | no | New memory (MB). |
| `--cpu` | float | no | New CPU cores. |
| `--credential` | string | no | New credential name. |
| `--proxy-enabled / --no-proxy-enabled` | flag | no | Toggle MCP proxy. |
| `--session-affinity` | string | no | New session affinity. |
| `--from-file` | path | no | JSON file with update fields. |

### Examples

```bash
ar tool update --name weather-mcp --timeout 60
ar tool update --name custom-mcp --proxy-enabled
```

---

## delete

```
ar tool delete --name <name>
```

### Options

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--name` | string | yes | Tool to delete. |

### Examples

```bash
ar tool delete --name weather-mcp
```

---

## list-tools

List sub-tools (the functions / methods) exposed by a Tool.

```
ar tool list-tools --name <name>
```

### Options

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--name` | string | yes | Tool name. |

### Examples

```bash
ar tool list-tools --name weather-mcp
```

---

## invoke

Call a sub-tool directly. Useful for testing before wiring a tool into a super
agent, or as part of scripted workflows.

```
ar tool invoke --name <name> --sub-tool <fn> [--arguments <json> | --arguments-file <path>]
```

### Options

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--name` | string | yes | Tool name. |
| `--sub-tool` | string | yes | Sub-tool (function) name. |
| `--arguments` | string | no | Inline JSON arguments. Mutually exclusive with `--arguments-file`. |
| `--arguments-file` | path | no | JSON file path with arguments. |

### Examples

```bash
ar tool invoke --name weather-mcp \
  --sub-tool get_weather \
  --arguments '{"city": "Hangzhou"}'

ar tool invoke --name custom-mcp \
  --sub-tool translate \
  --arguments-file ./args.json
```
