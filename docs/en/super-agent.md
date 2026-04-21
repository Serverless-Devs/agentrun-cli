**English** | [简体中文](../zh/super-agent.md)

# ar super-agent

Manage **Super Agents** — platform-hosted AI agents configured with
`prompt / model / tools / skills / sandboxes / workspaces / sub-agents`.
You declare intent; the platform hosts the runtime.

Also available as the alias `ar sa`. The conversation sub-group can be reached
as `ar sa conv` or `ar sa conversation`.

## Commands

Quickstart & chat:

- [run](#run) — create a (temporary) agent and enter a REPL
- [chat](#chat) — enter a REPL on an existing agent, auto-resuming the last conversation
- [invoke](#invoke) — one-shot call, stream response, ideal for scripts

Declarative:

- [apply](#apply) — create-or-update from YAML
- [render](#render) — dry-run rendering of YAML

CRUD:

- [create](#create)
- [get](#get)
- [list](#list)
- [update](#update)
- [delete](#delete)

Conversation (sub-group [`conversation` / `conv`](#conversation-sub-group)):

- `get` / `delete` / `list`

Also covered here:

- [YAML schema](#yaml-schema) used by `apply` / `render`
- [REPL commands](#repl-commands) available inside `run` / `chat`
- [Render modes](#render-modes) — `pretty`, `raw`, `text-only`
- [Local state file](#local-state-file) — how conversation IDs persist

---

## run

Quickstart. Creates a super agent (auto-named if `--name` is omitted) and enters
an interactive REPL. The agent persists after you exit — resume with
`ar sa chat <name>`.

```
ar sa run [options]
```

### Options

| Flag | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `--name` | string | no | `super-agent-tmp-<YYYYMMDDHHMMSS>` | Agent name. Explicit name → persistent; auto-name → still persistent but clearly temporary. |
| `--prompt`, `-p` | string | no | `You are a helpful assistant.` | System prompt. |
| `--model-service` | string | no | TTY-picker | ModelService name. Required if stdin is not a TTY or `--no-input` is set. |
| `--model` | string | no | TTY-picker | Model name within the ModelService. |
| `--tool` | multi | no |  | Tool name, repeatable. |
| `--skill` | multi | no |  | Skill name, repeatable. |
| `--sandbox` | multi | no |  | Sandbox name, repeatable. |
| `--workspace` | multi | no |  | Workspace name, repeatable. |
| `--sub-agent` | multi | no |  | Sub-agent name, repeatable. |
| `--message`, `-m` | string | no |  | Initial message — sent right after entering the REPL. |
| `--raw` | flag | no | false | Force raw SSE JSON-line output. |
| `--text-only` | flag | no | false | Only show assistant text (hide tool calls). |
| `--no-input` | flag | no | false | Disable interactive pickers; any missing required arg fails the command. |

### Examples

```bash
# Zero-config — CLI picks ModelService/Model interactively
ar sa run

# Explicit prompt and an initial message
ar sa run -p "You write concise Python" -m "Implement FizzBuzz"

# Non-interactive (scripts / CI)
ar sa run \
  --model-service svc-tongyi --model qwen-max \
  --prompt "You are an assistant" \
  --tool mcp-time-sa \
  --no-input

# Name it and keep it around
ar sa run --name my-helper -p "You are my helper"
# → later:
ar sa chat my-helper
```

---

## chat

Enter the REPL against an existing agent. By default it resumes the last
conversation (read from [the local state file](#local-state-file)).

```
ar sa chat <NAME> [options]
```

### Options

| Flag | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `NAME` | positional | yes |  | Super-agent name. |
| `--conversation`, `-c` | string | no | from state file | Explicit conversation id to resume. |
| `--new` | flag | no | false | Force-start a new conversation (ignore state). |
| `--message`, `-m` | string | no |  | Initial message sent right after entering REPL. |
| `--raw` | flag | no | false | Force raw output. |
| `--text-only` | flag | no | false | Force text-only output. |

### Examples

```bash
ar sa chat my-helper                  # resume last conversation
ar sa chat my-helper --new            # start fresh
ar sa chat my-helper -c conv-abc123   # resume a specific conversation
ar sa chat my-helper -m "Where were we?"
```

---

## invoke

Single-shot non-interactive call. Streams SSE events and exits when the run
finishes. Ideal for scripting and CI.

```
ar sa invoke <NAME> (--message <msg> | --messages <json>) [options]
```

### Options

| Flag | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `NAME` | positional | yes |  | Super-agent name. |
| `--message`, `-m` | string | one of |  | User message (becomes a single `user`-role message). |
| `--messages` | JSON | one of |  | Full messages array. Mutually exclusive with `-m`. |
| `--conversation`, `-c` | string | no |  | Continue an existing conversation. |
| `--save-conv` | flag | no | false | Persist the returned conversation id to local state so `ar sa chat` resumes it. |
| `--raw` | flag | no | TTY→pretty / non-TTY→raw | Force raw SSE JSON-line output. |
| `--text-only` | flag | no | false | Emit only assistant text; no envelope, no tool calls. |
| `--timeout` | int | no | `300` | Overall timeout in seconds. |

### Examples

```bash
# Minimal call (non-TTY → raw JSON-line stream by default)
ar sa invoke my-helper -m "What time is it?"

# Just the assistant text, good for piping
ar sa invoke my-helper -m "Explain closures" --text-only | tee answer.txt

# Full messages array
ar sa invoke my-helper --messages '[
  {"role": "system", "content": "You are a Python teacher"},
  {"role": "user",   "content": "What is a decorator?"}
]'

# Persist the conversation id for follow-up chat
ar sa invoke my-helper -m "Hello" --save-conv
ar sa chat my-helper   # resumes the same conversation
```

---

## apply

Declaratively create-or-update super agents from YAML. See the
[YAML schema](#yaml-schema) below.

```
ar sa apply -f <FILE> [--dry-run]
```

### Options

| Flag | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `-f`, `--file` | path | yes |  | YAML file path. Supports multiple documents separated by `---`. |
| `--dry-run` | flag | no | false | Validate and render only; no API call. Equivalent to `render`. |

### Examples

```bash
ar sa apply -f superagent.yaml
ar sa apply -f agents-stack.yaml          # multi-doc YAML
ar sa apply -f superagent.yaml --dry-run  # validate only
```

Output is a JSON array, one entry per document. `action` is one of
`created`, `updated`, `dry-run`.

---

## render

Render a YAML file to the exact JSON that would be sent to the server. Does
**not** call the server — no credentials required.

```
ar sa render -f <FILE>
```

### Examples

```bash
ar sa render -f superagent.yaml
ar sa render -f superagent.yaml | jq '.[0].rendered_create_input.agentRuntimeName'
```

---

## create

One-shot creation of a super agent.

```
ar sa create --name <name> [options]
```

### Options

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--name` | string | yes | Agent name (globally unique). |
| `--description` | string | no | Description. |
| `--prompt`, `-p` | string | no | System prompt. |
| `--model-service` | string | no | ModelService name. |
| `--model` | string | no | Model name. |
| `--tool` | multi | no | Tool name, repeatable. |
| `--skill` | multi | no | Skill name, repeatable. |
| `--sandbox` | multi | no | Sandbox name, repeatable. |
| `--workspace` | multi | no | Workspace name, repeatable. |
| `--sub-agent` | multi | no | Sub-agent name, repeatable. |

### Examples

```bash
ar sa create --name my-helper \
  -p "You are my assistant" \
  --model-service svc-tongyi --model qwen-max

ar sa create --name researcher \
  -p "Deep research assistant" \
  --model-service svc-tongyi --model qwen-max \
  --tool web-search --tool mcp-time-sa \
  --skill data-analyzer --skill report-generator
```

---

## get

```
ar sa get <NAME>
```

### Examples

```bash
ar sa get my-helper
```

---

## list

```
ar sa list [--page <n>] [--page-size <n>] [--all]
```

### Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--page` | int | `1` | Page number. |
| `--page-size` | int | `20` | Page size. |
| `--all` | flag | false | Fetch every page automatically. |

### Examples

```bash
ar sa list
ar sa list --all
ar sa list --page 2 --page-size 50
```

---

## update

Partial update. Only fields explicitly passed are changed. Passing a repeatable
flag **replaces** the whole list (e.g. `--tool a --tool b` replaces existing
tools with `[a, b]`). To empty a list, use the corresponding `--clear-*` flag.

```
ar sa update <NAME> [options]
```

### Options

| Flag | Type | Description |
|------|------|-------------|
| `NAME` | positional | Agent to update. |
| `--description` | string | New description. |
| `--prompt`, `-p` | string | New prompt. |
| `--model-service` | string | New ModelService. |
| `--model` | string | New model name. |
| `--tool` | multi | Replacement tool list. |
| `--skill` | multi | Replacement skill list. |
| `--sandbox` | multi | Replacement sandbox list. |
| `--workspace` | multi | Replacement workspace list. |
| `--sub-agent` | multi | Replacement sub-agent list. |
| `--clear-tools` | flag | Empty the tools list. |
| `--clear-skills` | flag | Empty the skills list. |
| `--clear-sandboxes` | flag | Empty the sandboxes list. |
| `--clear-workspaces` | flag | Empty the workspaces list. |
| `--clear-sub-agents` | flag | Empty the sub-agents list. |

`--tool` and `--clear-tools` (and the other pairs) are mutually exclusive — using
both fails with exit code `2`.

### Examples

```bash
ar sa update my-helper -p "You are a concise helper"
ar sa update my-helper --model-service svc-openai --model gpt-4o
ar sa update my-helper --tool web-search --tool calculator
ar sa update my-helper --clear-tools
```

---

## delete

```
ar sa delete <NAME>
```

### Examples

```bash
ar sa delete my-helper
```

---

## conversation sub-group

Manage conversations for a super agent. Also reachable as `ar sa conv`.

### conversation list

```
ar sa conv list <NAME>
```

> Requires agentrun SDK ≥ `0.0.157`. Older SDK versions exit with status `1`
> and the message `list_conversations not available on this SDK version; please
> upgrade agentrun SDK to >= 0.0.157.`

### conversation get

```
ar sa conv get <NAME> <CONVERSATION_ID>
```

### conversation delete

```
ar sa conv delete <NAME> <CONVERSATION_ID>
```

If the deleted conversation id matches the one stored in the local state file
for `<NAME>`, the local entry is cleared so `ar sa chat <NAME>` will start a
fresh conversation next time.

### Examples

```bash
ar sa conv list my-helper
ar sa conv get  my-helper conv-abc-123
ar sa conv delete my-helper conv-abc-123
```

---

## YAML schema

`apply` and `render` consume YAML in a Kubernetes-style shape:

```yaml
apiVersion: agentrun/v1
kind: SuperAgent
metadata:
  name: my-helper          # required, globally unique
  description: "..."       # optional
spec:
  prompt: |                # optional
    You are a helpful assistant.
  model:                   # optional (but required to actually invoke)
    service: svc-tongyi
    name: qwen-max
  tools:
    - mcp-time-sa
  skills: []
  sandboxes: []
  workspaces: []
  subAgents: []            # maps to SDK's `agents` field
```

### Field mapping

| YAML field | SDK field |
|------------|-----------|
| `metadata.name` | `name` |
| `metadata.description` | `description` |
| `spec.prompt` | `prompt` |
| `spec.model.service` | `model_service_name` |
| `spec.model.name` | `model_name` |
| `spec.tools` | `tools` |
| `spec.skills` | `skills` |
| `spec.sandboxes` | `sandboxes` |
| `spec.workspaces` | `workspaces` |
| `spec.subAgents` | `agents` |

### Multi-document YAML

Separate documents with `---`:

```yaml
apiVersion: agentrun/v1
kind: SuperAgent
metadata:
  name: doc-writer
spec:
  prompt: "You write clear docs"
  model: { service: svc-tongyi, name: qwen-max }
---
apiVersion: agentrun/v1
kind: SuperAgent
metadata:
  name: code-reviewer
spec:
  prompt: "You are a Python reviewer"
  model: { service: svc-tongyi, name: qwen-max }
```

`apply -f` processes documents in order; if any fails, already-succeeded agents
are **not** rolled back.

---

## REPL commands

Inside the `run` and `chat` REPL, lines starting with `/` are handled locally
(never sent to the agent):

| Command | Description |
|---------|-------------|
| `/exit`, `/quit` | Exit the REPL. |
| `/new` | Drop the current conversation id and start fresh on the next message. |
| `/conv` | Print the current conversation id. |
| `/raw` | Toggle raw-JSON output mode. |
| `/help` | List available commands. |

Keyboard:

- `Ctrl+C` (once) — interrupt the current streaming response, return to prompt
- `Ctrl+C` (twice) — exit with status `130`
- `Ctrl+D` — same as `/exit`

---

## Render modes

Three output modes control how SSE events are displayed:

| Mode | Default context | Behavior |
|------|-----------------|----------|
| `pretty` | TTY | Stream assistant text inline; tool calls shown as dim one-liners. |
| `raw` | non-TTY | Emit every SSE event as one JSON line; `invoke` appends an envelope `{"_meta":"envelope","conversation_id":"…","status":"completed"}`. |
| `text-only` | `--text-only` flag | Only assistant text; no envelope, no tool calls. |

Pipe friendliness:

```bash
ar sa invoke my-helper -m "Ping" | jq '.event'            # raw mode by default
ar sa chat my-helper -m "Ping" | head -20                 # chat also switches to raw when piped
```

---

## Local state file

Path: `~/.agentrun/super-agent-state.json`.

Schema:

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

Write triggers:

- Every completed turn in `ar sa run` / `ar sa chat`
- `ar sa invoke --save-conv`

Read triggers:

- `ar sa chat <name>` without `--conversation` / `--new` — reads
  `agents.<name>.last_conversation_id` for auto-resume.

Failure to read or write the state file is non-fatal — a warning is logged to
stderr and the main flow continues.
