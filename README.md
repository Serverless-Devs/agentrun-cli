**English** | [简体中文](./README_zh.md)

# AgentRun CLI

> Command-line tool for managing AI-agent infrastructure on the AgentRun platform.

`ar` (or `agentrun`) is a single-binary CLI that wraps the AgentRun Python SDK. It lets
developers, CI pipelines, and LLM-powered agents create and operate sandboxes, tools,
skills, model services and — most importantly — **super agents**: platform-hosted AI
agents that you configure declaratively without writing or deploying any runtime code.

## Features

- **One-command super agent** — `ar super-agent run` creates a hosted agent and drops you into a chat REPL in seconds.
- **Declarative deployment** — Kubernetes-style YAML (`ar sa apply -f superagent.yaml`) for reproducible, version-controlled agents.
- **Six resource groups** — `config`, `model`, `sandbox`, `tool`, `skill`, `super-agent`, all following the same `ar <group> <action>` pattern.
- **Multi-profile config** — store multiple sets of credentials in `~/.agentrun/config.json` and switch with `--profile`.
- **Multiple output formats** — `json` (default), `table`, `yaml`, and `quiet` for shell piping.
- **Agent-friendly** — JSON-by-default output, deterministic exit codes, no interactive prompts when stdin isn't a TTY.
- **Rich sandbox primitives** — code execution, file system, process management, and CDP/VNC-backed browser automation.
- **Single-file distribution** — PyInstaller produces standalone `ar` / `agentrun` binaries for Linux, macOS and Windows (x86_64 + arm64).

## Installation

### Prebuilt binary (recommended)

Download a single self-contained binary from [Releases](https://github.com/Serverless-Devs/agentrun-cli/releases). No Python required.

**Linux / macOS** (x86_64 or arm64):

```bash
curl -fsSL https://raw.githubusercontent.com/Serverless-Devs/agentrun-cli/main/scripts/install.sh | sh
```

**Windows** (x86_64, PowerShell):

```powershell
irm https://raw.githubusercontent.com/Serverless-Devs/agentrun-cli/main/scripts/install.ps1 | iex
```

Pin a specific version with `AGENTRUN_VERSION=v0.1.0 …`. Change the install directory with `AGENTRUN_INSTALL=…`. Both installers verify the SHA256 checksum before placing the binary.

Or download the archive manually from the Releases page — naming scheme:

```
agentrun-<version>-<os>-<arch>.<ext>
# e.g. agentrun-0.1.0-linux-amd64.tar.gz
#      agentrun-0.1.0-darwin-arm64.tar.gz
#      agentrun-0.1.0-windows-amd64.zip
```

### From PyPI

```bash
pip install agentrun-cli
```

### From source

```bash
git clone https://github.com/Serverless-Devs/agentrun-cli.git
cd agentrun-cli
make install            # editable install into .venv
make build              # standalone binary → dist/agentrun
```

### Verify

```bash
ar --version            # or: agentrun --version
```

## Prerequisites

Two one-time setup steps are required before `ar super-agent` will work:

### 1. Authorize the AliyunAgentRunSuperAgentRole

AgentRun uses a custom RAM service role — **`AliyunAgentRunSuperAgentRole`** —
to manage runtime resources on your behalf. Open the link below and confirm
in the RAM console:

[**→ Create AliyunAgentRunSuperAgentRole**](https://ram.console.aliyun.com/authorize?hideTopbar=true&hideSidebar=true&request=%7B%22template%22%3A%22AgentRun%22%2C%22payloads%22%3A%5B%7B%22missionId%22%3A%22SuperAgentCustomRole%22%7D%5D%7D)

Without this role, `ar super-agent run` / `apply` will fail at creation time.

### 2. Grant `AliyunAgentRunFullAccess` to your AccessKey

The AccessKey you save with `ar config set access_key_id ...` must belong to a
RAM user (or role) that has the **`AliyunAgentRunFullAccess`** system policy
attached. If you see exit code `3` or `AccessDenied`, this is almost always
the cause.

### Want more than QuickStart? Use the console

This CLI covers the QuickStart conversational flow end-to-end. For the full
AgentRun experience, head to the Function Compute AgentRun console:
<https://functionai.console.aliyun.com/cn-hangzhou/agent/>

## Quickstart

### Step 1 — Configure credentials

```bash
ar config set access_key_id     LTAI5t...
ar config set access_key_secret ***
ar config set account_id        1234567890
ar config set region            cn-hangzhou
```

Credentials land in `~/.agentrun/config.json` under the `default` profile. Use
`--profile staging` on any command to target a named profile.

### Step 2 — Spin up a super agent and chat

```bash
$ ar super-agent run --prompt "You are a Python expert"
Creating super agent: super-agent-tmp-20260420213045 ...
Ready. Type your message (/help for commands).

> Write a quicksort in Python
def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left  = [x for x in arr if x < pivot]
    mid   = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + mid + quicksort(right)

> /exit
─────────────────────────────────────────────
Super agent created: super-agent-tmp-20260420213045
Last conversation:  conv-9f8e7d6c-xxx
Resume:  ar sa chat super-agent-tmp-20260420213045
Delete:  ar sa delete super-agent-tmp-20260420213045
─────────────────────────────────────────────
```

The agent persists after you exit, so you can continue the conversation later with
`ar sa chat <name>` — the CLI remembers the last conversation id locally.

### Step 3 — Declarative deployment

Save this to `superagent.yaml`:

```yaml
apiVersion: agentrun/v1
kind: SuperAgent
metadata:
  name: my-helper
  description: "My personal assistant"
spec:
  prompt: "You are my helpful assistant"
  tools:
    - mcp-time-sa
  skills: []
  sandboxes: []
  workspaces: []
  subAgents: []
```

Then deploy it:

```bash
ar super-agent apply -f superagent.yaml
# → action: "created"    (first run)
# → action: "updated"    (subsequent runs)

# Chat with it
ar sa chat my-helper

# Single-shot invocation for scripts
ar sa invoke my-helper -m "Plan my day" --text-only
```

Multi-document YAMLs (`---` separated) let you deploy many agents in one call.

## Command groups

| Group | Alias | Purpose | Docs |
|-------|-------|---------|------|
| `config` |  | Credentials and named profiles | [en](./docs/en/config.md) · [zh](./docs/zh/config.md) |
| `model` |  | Register external LLM providers as ModelServices | [en](./docs/en/model.md) · [zh](./docs/zh/model.md) |
| `sandbox` | `sb` | Sandboxes + files, processes, contexts, templates, browser | [en](./docs/en/sandbox.md) · [zh](./docs/zh/sandbox.md) |
| `tool` |  | MCP and FunctionCall tools | [en](./docs/en/tool.md) · [zh](./docs/zh/tool.md) |
| `skill` |  | Platform skill packages + local execution + bulk sync to AI tool directories | [en](./docs/en/skill.md) · [zh](./docs/zh/skill.md) |
| `super-agent` | `sa` | Quickstart / CRUD / declarative / conversation | [en](./docs/en/super-agent.md) · [zh](./docs/zh/super-agent.md) |

## Documentation

- English reference: [docs/en/index.md](./docs/en/index.md)
- 中文手册: [docs/zh/index.md](./docs/zh/index.md)

Each page walks through installation, authentication, global options, output formats,
exit codes and every command option with runnable examples.

## Community

Questions, bug reports and feature requests are welcome on
[GitHub Issues](https://github.com/Serverless-Devs/agentrun-cli/issues).

For real-time discussion, join the **函数计算 AgentRun 客户群** on DingTalk —
group number **`134570017218`**.

## License

Apache-2.0 — see [LICENSE](./LICENSE).
