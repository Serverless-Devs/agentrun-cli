[English](../en/super-agent.md) | **简体中文**

# ar super-agent

管理 **Super Agent** —— 由平台托管的 AI Agent，用户只需声明
`prompt / model / tools / skills / sandboxes / workspaces / sub-agents`
这些业务字段，运行时完全由平台托管，无需编写或部署任何代码。

该命令组还提供短别名 `ar sa`。会话子组既可用 `ar sa conv` 也可用
`ar sa conversation`，行为一致。

## 子命令

一键拉起与对话：

- [run](#run) —— 创建（临时）Agent 并进入 REPL
- [chat](#chat) —— 对已有 Agent 进入 REPL，自动续接上次会话
- [invoke](#invoke) —— 单次调用，流式输出，适合脚本

声明式：

- [apply](#apply) —— 从 YAML 创建或更新
- [render](#render) —— 空跑渲染 YAML

CRUD：

- [create](#create)
- [get](#get)
- [list](#list)
- [update](#update)
- [delete](#delete)

会话子组（[`conversation` / `conv`](#conversation-子命令组)）：

- `get` / `delete` / `list`

本页还涵盖：

- `apply` / `render` 所用的 [YAML Schema](#yaml-schema)
- `run` / `chat` REPL 内可用的 [REPL 指令](#repl-指令)
- [渲染模式](#渲染模式) —— `pretty` / `raw` / `text-only`
- [本地状态文件](#本地状态文件) —— conversation id 的持久化

---

## run

一键拉起。创建一个 Super Agent（未传 `--name` 时自动命名）并进入交互式 REPL。
退出后 Agent 依然保留，后续用 `ar sa chat <name>` 即可续聊。

```
ar sa run [options]
```

### 参数

| Flag | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--name` | string | 否 | `super-agent-tmp-<YYYYMMDDHHMMSS>` | Agent 名。显式命名 → 持久化；自动名 → 同样持久化，仅命名方便识别。 |
| `--prompt`、`-p` | string | 否 | `You are a helpful assistant.` | 系统提示词。 |
| `--tool` | multi | 否 |  | 工具名，可重复。 |
| `--skill` | multi | 否 |  | 技能名，可重复。 |
| `--sandbox` | multi | 否 |  | 沙箱名，可重复。 |
| `--workspace` | multi | 否 |  | 工作空间名，可重复。 |
| `--sub-agent` | multi | 否 |  | 子 Agent 名，可重复。 |
| `--message`、`-m` | string | 否 |  | 初始消息 —— 进入 REPL 后立刻发送。 |
| `--raw` | flag | 否 | false | 强制 raw SSE JSON 行输出。 |
| `--text-only` | flag | 否 | false | 只显示 Assistant 文本（隐藏工具调用）。 |
| `--no-input` | flag | 否 | false | 已弃用，行为为空操作；仅保留以兼容旧脚本。 |

### 示例

```bash
# 零配置 —— 服务端选用默认 model
ar sa run

# 指定 prompt + 初始消息
ar sa run -p "你是简洁风格的 Python 程序员" -m "写个 FizzBuzz"

# 启用工具
ar sa run \
  --prompt "你是助手" \
  --tool mcp-time-sa

# 命名让 Agent 持久保留
ar sa run --name my-helper -p "你是我的助手"
# → 后续：
ar sa chat my-helper
```

---

## chat

对已存在的 Agent 进入 REPL。默认会读取 [本地状态文件](#本地状态文件)，续聊上次
会话。

```
ar sa chat <NAME> [options]
```

### 参数

| Flag | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `NAME` | 位置参数 | 是 |  | Super Agent 名。 |
| `--conversation`、`-c` | string | 否 | 本地状态 | 指定续聊的 conversation id。 |
| `--new` | flag | 否 | false | 强制开新会话（忽略本地状态）。 |
| `--message`、`-m` | string | 否 |  | 进入 REPL 后立即发送的消息。 |
| `--raw` | flag | 否 | false | 强制 raw 输出。 |
| `--text-only` | flag | 否 | false | 强制 text-only 输出。 |

### 示例

```bash
ar sa chat my-helper                  # 续聊上次
ar sa chat my-helper --new            # 开新会话
ar sa chat my-helper -c conv-abc123   # 指定某个会话续聊
ar sa chat my-helper -m "刚才说到哪了"
```

---

## invoke

单次非交互调用，流式消费 SSE 事件，run 结束即退出。适合脚本化与 CI。

```
ar sa invoke <NAME> (--message <msg> | --messages <json>) [options]
```

### 参数

| Flag | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `NAME` | 位置参数 | 是 |  | Super Agent 名。 |
| `--message`、`-m` | string | 二选一 |  | 用户消息（组装为单条 `user` role）。 |
| `--messages` | JSON | 二选一 |  | 完整的 messages 数组，与 `-m` 互斥。 |
| `--conversation`、`-c` | string | 否 |  | 续聊指定会话。 |
| `--save-conv` | flag | 否 | false | 将本次返回的 conversation id 写入本地状态，后续 `ar sa chat` 可续聊。 |
| `--raw` | flag | 否 | TTY→pretty / 非 TTY→raw | 强制 raw SSE JSON 行输出。 |
| `--text-only` | flag | 否 | false | 只输出 Assistant 文本，无 envelope、无工具调用。 |
| `--timeout` | int | 否 | `300` | 整体超时（秒）。 |

### 示例

```bash
# 最简调用（非 TTY 默认 raw）
ar sa invoke my-helper -m "现在几点了"

# 只要 Assistant 文本，方便管道
ar sa invoke my-helper -m "解释一下闭包" --text-only | tee answer.txt

# 完整 messages 数组
ar sa invoke my-helper --messages '[
  {"role": "system", "content": "你是 Python 老师"},
  {"role": "user",   "content": "什么是装饰器?"}
]'

# 持久化 conversation id 给后续 chat
ar sa invoke my-helper -m "你好" --save-conv
ar sa chat my-helper   # 续聊同一会话
```

---

## apply

声明式地从 YAML 创建或更新 Super Agent。YAML 结构见下方 [YAML Schema](#yaml-schema)。

```
ar sa apply -f <FILE> [--dry-run]
```

### 参数

| Flag | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `-f`、`--file` | path | 是 |  | YAML 文件路径，支持 `---` 分隔的多文档。 |
| `--dry-run` | flag | 否 | false | 仅校验并渲染，不调服务端（等价于 `render`）。 |

### 示例

```bash
ar sa apply -f superagent.yaml
ar sa apply -f agents-stack.yaml          # 多文档 YAML
ar sa apply -f superagent.yaml --dry-run  # 只做校验
```

返回是 JSON 数组，每个文档对应一条。`action` 可能是 `created` / `updated` /
`dry-run`。

---

## render

把 YAML 文件渲染成最终会发给服务端的 JSON。**不调用服务端**，不需要凭证。

```
ar sa render -f <FILE>
```

### 示例

```bash
ar sa render -f superagent.yaml
ar sa render -f superagent.yaml | jq '.[0].rendered_create_input.agentRuntimeName'
```

---

## create

一行命令创建 Super Agent。

```
ar sa create --name <name> [options]
```

### 参数

| Flag | 类型 | 必填 | 说明 |
|------|------|------|------|
| `--name` | string | 是 | 全局唯一的 Agent 名。 |
| `--description` | string | 否 | 描述。 |
| `--prompt`、`-p` | string | 否 | 系统提示词。 |
| `--tool` | multi | 否 | 工具名，可重复。 |
| `--skill` | multi | 否 | 技能名，可重复。 |
| `--sandbox` | multi | 否 | 沙箱名，可重复。 |
| `--workspace` | multi | 否 | 工作空间名，可重复。 |
| `--sub-agent` | multi | 否 | 子 Agent 名，可重复。 |

### 示例

```bash
ar sa create --name my-helper \
  -p "你是我的助手"

ar sa create --name researcher \
  -p "深度调研助手" \
  --tool web-search --tool mcp-time-sa \
  --skill data-analyzer --skill report-generator
```

---

## get

```
ar sa get <NAME>
```

### 示例

```bash
ar sa get my-helper
```

---

## list

```
ar sa list [--page <n>] [--page-size <n>] [--all]
```

### 参数

| Flag | 类型 | 默认 | 说明 |
|------|------|------|------|
| `--page` | int | `1` | 页码。 |
| `--page-size` | int | `20` | 每页条数。 |
| `--all` | flag | false | 自动分页拉全部。 |

### 示例

```bash
ar sa list
ar sa list --all
ar sa list --page 2 --page-size 50
```

---

## update

部分更新。只有显式传入的字段会被修改。对可重复参数（如 `--tool`）传值时会
**整体替换** 原列表（即 `--tool a --tool b` 把 tools 覆盖为 `[a, b]`）。要清空
列表，使用对应的 `--clear-*`。

```
ar sa update <NAME> [options]
```

### 参数

| Flag | 类型 | 说明 |
|------|------|------|
| `NAME` | 位置参数 | 要更新的 Agent。 |
| `--description` | string | 新描述。 |
| `--prompt`、`-p` | string | 新 prompt。 |
| `--tool` | multi | 替换 tools 列表。 |
| `--skill` | multi | 替换 skills 列表。 |
| `--sandbox` | multi | 替换 sandboxes 列表。 |
| `--workspace` | multi | 替换 workspaces 列表。 |
| `--sub-agent` | multi | 替换 sub-agents 列表。 |
| `--clear-tools` | flag | 清空 tools。 |
| `--clear-skills` | flag | 清空 skills。 |
| `--clear-sandboxes` | flag | 清空 sandboxes。 |
| `--clear-workspaces` | flag | 清空 workspaces。 |
| `--clear-sub-agents` | flag | 清空 sub-agents。 |

`--tool` 与 `--clear-tools`（以及其他成对 flag）互斥，同时出现会以退出码 `2` 报错。

### 示例

```bash
ar sa update my-helper -p "简洁风格的助手"
ar sa update my-helper --tool web-search --tool calculator
ar sa update my-helper --clear-tools
```

---

## delete

```
ar sa delete <NAME>
```

### 示例

```bash
ar sa delete my-helper
```

---

## conversation 子命令组

管理 Super Agent 的会话。亦可简写为 `ar sa conv`。

### conversation list

```
ar sa conv list <NAME>
```

> 需要 agentrun SDK ≥ `0.0.157`。旧版本会以退出码 `1` 结束，并提示
> `list_conversations not available on this SDK version; please upgrade agentrun
> SDK to >= 0.0.157.`

### conversation get

```
ar sa conv get <NAME> <CONVERSATION_ID>
```

### conversation delete

```
ar sa conv delete <NAME> <CONVERSATION_ID>
```

若删除的 conversation id 恰好是本地状态文件里 `<NAME>` 的最近会话，CLI 会同步
清除本地记录，避免下次 `ar sa chat` 自动续聊到已删除的会话。

### 示例

```bash
ar sa conv list my-helper
ar sa conv get  my-helper conv-abc-123
ar sa conv delete my-helper conv-abc-123
```

---

## YAML Schema

`apply` 和 `render` 使用 Kubernetes 风格的 YAML：

```yaml
apiVersion: agentrun/v1
kind: SuperAgent
metadata:
  name: my-helper          # 必填，全局唯一
  description: "..."       # 可选
spec:
  prompt: |                # 可选
    你是一个得力助手。
  tools:
    - mcp-time-sa
  skills: []
  sandboxes: []
  workspaces: []
  subAgents: []            # 映射到 SDK 的 `agents` 字段
```

### 字段映射

| YAML 字段 | SDK 字段 |
|-----------|---------|
| `metadata.name` | `name` |
| `metadata.description` | `description` |
| `spec.prompt` | `prompt` |
| `spec.tools` | `tools` |
| `spec.skills` | `skills` |
| `spec.sandboxes` | `sandboxes` |
| `spec.workspaces` | `workspaces` |
| `spec.subAgents` | `agents` |

### 多文档 YAML

用 `---` 分隔：

```yaml
apiVersion: agentrun/v1
kind: SuperAgent
metadata:
  name: doc-writer
spec:
  prompt: "你擅长撰写清晰的技术文档"
---
apiVersion: agentrun/v1
kind: SuperAgent
metadata:
  name: code-reviewer
spec:
  prompt: "你是资深 Python Reviewer"
```

`apply -f` 按文档顺序处理；任一失败会导致后续中断，**但已成功的 Agent 不会回滚**。

---

## REPL 指令

在 `run` 和 `chat` 的 REPL 里，`/` 开头的行是本地指令，不会发给 Agent：

| 指令 | 说明 |
|------|------|
| `/exit`、`/quit` | 退出 REPL。 |
| `/new` | 丢弃当前 conversation id，下一条消息开新会话。 |
| `/conv` | 打印当前 conversation id。 |
| `/raw` | 切换 raw JSON 输出模式。 |
| `/help` | 列出全部指令。 |

键盘：

- `Ctrl+C`（一次）—— 打断当前的流式响应，回到提示符
- `Ctrl+C`（连按两次）—— 以退出码 `130` 退出
- `Ctrl+D` —— 同 `/exit`

---

## 渲染模式

SSE 事件有三种输出模式：

| 模式 | 默认触发 | 行为 |
|------|---------|------|
| `pretty` | TTY | Assistant 文本实时打印；工具调用以暗色单行显示。 |
| `raw` | 非 TTY | 每个 SSE 事件一行 JSON；`invoke` 结束会追加 envelope `{"_meta":"envelope","conversation_id":"…","status":"completed"}`。 |
| `text-only` | `--text-only` | 只输出 Assistant 文本，无 envelope、无工具调用。 |

管道友好：

```bash
ar sa invoke my-helper -m "Ping" | jq '.event'            # 默认 raw
ar sa chat my-helper -m "Ping" | head -20                 # chat 被 pipe 时也切到 raw
```

---

## 本地状态文件

路径：`~/.agentrun/super-agent-state.json`。

格式：

```json
{
  "agents": {
    "my-helper": {
      "last_conversation_id": "conv-9f8e7d6c-xxx",
      "last_used_at": "2026-04-20T21:35:12Z"
    }
  }
}
```

写入时机：

- `ar sa run` / `ar sa chat` 每完成一轮对话
- `ar sa invoke --save-conv`

读取时机：

- `ar sa chat <name>` 未带 `--conversation` / `--new` 时，读
  `agents.<name>.last_conversation_id` 自动续聊。

读写失败不会中断主流程 —— CLI 只会向 stderr 打印 warning 并继续。
