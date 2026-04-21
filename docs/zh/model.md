[English](../en/model.md) | **简体中文**

# ar model

注册与管理 **ModelService** —— 外部 LLM Provider（通义 / DashScope、OpenAI、
DeepSeek、Anthropic……）接入 AgentRun 平台的配置对象。Super Agent 通过 ModelService
名 + 其中暴露的某个具体模型名来引用。

## 子命令

- [create](#create)
- [get](#get)
- [list](#list)
- [update](#update)
- [delete](#delete)

---

## create

```
ar model create --name <name> --provider <id> [options]
```

### 参数

| Flag | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--name` | string | 是 |  | 全局唯一的 ModelService 名。 |
| `--provider` | string | 是 |  | Provider 标识：`tongyi` / `openai` / `deepseek` / `anthropic` 等。 |
| `--model-type` | string | 否 | `llm` | `llm` / `text-embedding` / `rerank` / `speech2text` / `tts` / `moderation`。 |
| `--model-names` | string | 否 |  | 该服务暴露的模型名列表（逗号分隔）。 |
| `--base-url` | string | 否 |  | 自定义 Provider Base URL。 |
| `--api-key` | string | 否 |  | Provider API Key（推荐改用 `--credential`）。 |
| `--credential` | string | 否 |  | 使用平台凭证资源做认证。 |
| `--description` | string | 否 |  | 描述。 |
| `--from-file` | path | 否 |  | 指向完整 `ModelServiceCreateInput` 的 JSON 文件。 |

### 示例

```bash
# 接入通义（DashScope）
ar model create --name svc-tongyi \
  --provider tongyi \
  --model-type llm \
  --model-names qwen-max,qwen-plus,qwen-turbo

# 通过凭证接入 OpenAI 兼容端点
ar model create --name svc-openai \
  --provider openai \
  --model-names gpt-4o,gpt-4o-mini \
  --credential openai-key

# 完整 JSON 配置
ar model create --from-file model.json
```

---

## get

```
ar model get --name <name>
```

### 参数

| Flag | 类型 | 必填 | 说明 |
|------|------|------|------|
| `--name` | string | 是 | ModelService 名。 |

### 示例

```bash
ar model get --name svc-tongyi
```

---

## list

```
ar model list [--provider <id>] [--model-type <type>]
```

### 参数

| Flag | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--provider` | string | 否 |  | 按 Provider 过滤。 |
| `--model-type` | string | 否 | `llm` | 按 model-type 过滤。 |

### 示例

```bash
ar model list
ar model list --provider openai
ar model list --model-type text-embedding
```

---

## update

```
ar model update --name <name> [options]
```

### 参数

| Flag | 类型 | 必填 | 说明 |
|------|------|------|------|
| `--name` | string | 是 | 要更新的 ModelService。 |
| `--description` | string | 否 | 新描述。 |
| `--api-key` | string | 否 | 新 API Key。 |
| `--base-url` | string | 否 | 新 Base URL。 |
| `--credential` | string | 否 | 新凭证名。 |
| `--from-file` | path | 否 | `ModelServiceUpdateInput` 的 JSON 文件。 |

### 示例

```bash
ar model update --name svc-tongyi --description "线上通义服务"
ar model update --name svc-openai --credential openai-key-v2
```

---

## delete

```
ar model delete --name <name>
```

### 参数

| Flag | 类型 | 必填 | 说明 |
|------|------|------|------|
| `--name` | string | 是 | 要删除的 ModelService 名。 |

### 示例

```bash
ar model delete --name svc-tongyi
```
