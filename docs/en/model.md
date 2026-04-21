**English** | [简体中文](../zh/model.md)

# ar model

Register and manage **ModelServices** — bindings between external LLM providers
(Tongyi / DashScope, OpenAI, DeepSeek, Anthropic, …) and the AgentRun platform.
Super agents reference a ModelService by name plus one of the models exposed by it.

## Commands

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

### Options

| Flag | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `--name` | string | yes |  | Unique ModelService name. |
| `--provider` | string | yes |  | Provider identifier: `tongyi`, `openai`, `deepseek`, `anthropic`, etc. |
| `--model-type` | string | no | `llm` | `llm`, `text-embedding`, `rerank`, `speech2text`, `tts`, `moderation`. |
| `--model-names` | string | no |  | Comma-separated list of model names exposed by the service. |
| `--base-url` | string | no |  | Custom provider base URL. |
| `--api-key` | string | no |  | Provider API key (prefer `--credential` instead). |
| `--credential` | string | no |  | Name of a platform credential to use for auth. |
| `--description` | string | no |  | Human-readable description. |
| `--from-file` | path | no |  | JSON file with the full `ModelServiceCreateInput`. |

### Examples

```bash
# Register a Tongyi (DashScope) service
ar model create --name svc-tongyi \
  --provider tongyi \
  --model-type llm \
  --model-names qwen-max,qwen-plus,qwen-turbo

# Register an OpenAI-compatible endpoint via credential
ar model create --name svc-openai \
  --provider openai \
  --model-names gpt-4o,gpt-4o-mini \
  --credential openai-key

# Full JSON config
ar model create --from-file model.json
```

---

## get

```
ar model get --name <name>
```

### Options

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--name` | string | yes | ModelService name. |

### Examples

```bash
ar model get --name svc-tongyi
```

---

## list

```
ar model list [--provider <id>] [--model-type <type>]
```

### Options

| Flag | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `--provider` | string | no |  | Filter by provider. |
| `--model-type` | string | no | `llm` | Filter by model type. |

### Examples

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

### Options

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--name` | string | yes | ModelService to update. |
| `--description` | string | no | New description. |
| `--api-key` | string | no | New API key. |
| `--base-url` | string | no | New base URL. |
| `--credential` | string | no | New credential name. |
| `--from-file` | path | no | JSON file with `ModelServiceUpdateInput`. |

### Examples

```bash
ar model update --name svc-tongyi --description "Production Tongyi service"
ar model update --name svc-openai --credential openai-key-v2
```

---

## delete

```
ar model delete --name <name>
```

### Options

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--name` | string | yes | ModelService to delete. |

### Examples

```bash
ar model delete --name svc-tongyi
```
