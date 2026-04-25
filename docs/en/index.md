**English** | [简体中文](../zh/index.md)

# AgentRun CLI Reference

`ar` (alias for `agentrun`) is the CLI for managing AI-agent infrastructure on the
AgentRun platform. This page covers installation, authentication, global options,
output formats and exit codes. Jump to a command group at the bottom for per-command
option tables and examples.

## Contents

- [Installation](#installation)
- [Prerequisites](#prerequisites)
- [Authentication](#authentication)
- [Global options](#global-options)
- [Output formats](#output-formats)
- [Exit codes](#exit-codes)
- [Command groups](#command-groups)

## Installation

Three installation paths are supported. Pick the one that fits your environment.

### 1. Prebuilt binary (no Python required)

Supported targets: `linux-amd64`, `linux-arm64`, `darwin-amd64`, `darwin-arm64`, `windows-amd64`.

**Linux / macOS**:

```bash
curl -fsSL https://raw.githubusercontent.com/Serverless-Devs/agentrun-cli/main/scripts/install.sh | sh
```

**Windows** (PowerShell):

```powershell
irm https://raw.githubusercontent.com/Serverless-Devs/agentrun-cli/main/scripts/install.ps1 | iex
```

Both installers resolve the latest tag on GitHub Releases, verify the SHA256 checksum, and drop the binary into a user-writable directory (`$HOME/.local/bin` on Unix, `%LOCALAPPDATA%\Programs\agentrun` on Windows). Override with `AGENTRUN_VERSION`, `AGENTRUN_INSTALL` or `AGENTRUN_REPO`.

Release assets follow this naming scheme:

```
agentrun-<version>-<os>-<arch>.<ext>
# agentrun-0.1.0-linux-amd64.tar.gz
# agentrun-0.1.0-linux-arm64.tar.gz
# agentrun-0.1.0-darwin-amd64.tar.gz
# agentrun-0.1.0-darwin-arm64.tar.gz
# agentrun-0.1.0-windows-amd64.zip
```

Each archive has a sibling `.sha256` file, plus a combined `SHA256SUMS` for the whole release.

### 2. From PyPI

```bash
pip install agentrun-cli
```

### 3. From source

```bash
git clone https://github.com/Serverless-Devs/agentrun-cli.git
cd agentrun-cli
make install      # editable install into .venv
make build        # local binary → dist/agentrun
```

After installation, both `ar` and `agentrun` are available as entry points and behave
identically. `ar` is shorter; the examples in this manual use it.

## Prerequisites

Two one-time setup steps are required before `ar super-agent` will work.

### 1. Authorize the AliyunAgentRunSuperAgentRole

AgentRun uses a custom RAM service role — **`AliyunAgentRunSuperAgentRole`** —
to manage runtime resources on your behalf. Open the link below and confirm
in the RAM console:

[**→ Create AliyunAgentRunSuperAgentRole**](https://ram.console.aliyun.com/authorize?hideTopbar=true&hideSidebar=true&request=%7B%22template%22%3A%22AgentRun%22%2C%22payloads%22%3A%5B%7B%22missionId%22%3A%22SuperAgentCustomRole%22%7D%5D%7D)

Without this role, `ar super-agent run` / `apply` will fail at creation time.

### 2. Grant `AliyunAgentRunFullAccess` to your AccessKey

The AccessKey configured below (see [Authentication](#authentication)) must
belong to a RAM user (or role) that has the **`AliyunAgentRunFullAccess`**
system policy attached. If a command exits with code `3` or returns
`AccessDenied`, this is almost always the cause.

### Want more than QuickStart? Use the console

This CLI covers the QuickStart conversational flow end-to-end. For the full
AgentRun experience (visual designer, observability, knowledge bases, agent
marketplace, …), head to the Function Compute AgentRun console:
<https://functionai.console.aliyun.com/cn-hangzhou/agent/>

## Authentication

The CLI resolves credentials from three sources, in this order:

1. **Explicit CLI flag** — `--region` on the root command.
2. **Config-file profile** — values saved under `~/.agentrun/config.json`.
3. **Environment variables** — `AGENTRUN_*`, `ALIBABA_CLOUD_*`, `FC_*`.

The four keys the platform needs are:

| Key | Purpose | Env var fallbacks |
|-----|---------|-------------------|
| `access_key_id` | AccessKey ID | `AGENTRUN_ACCESS_KEY_ID`, `ALIBABA_CLOUD_ACCESS_KEY_ID` |
| `access_key_secret` | AccessKey Secret | `AGENTRUN_ACCESS_KEY_SECRET`, `ALIBABA_CLOUD_ACCESS_KEY_SECRET` |
| `account_id` | Alibaba Cloud account ID | `AGENTRUN_ACCOUNT_ID`, `FC_ACCOUNT_ID` |
| `region` | Region (e.g. `cn-hangzhou`) | `AGENTRUN_REGION`, `FC_REGION` |

Optional `security_token` (STS) is read from `AGENTRUN_SECURITY_TOKEN` or
`ALIBABA_CLOUD_SECURITY_TOKEN`.

Write all four at once:

```bash
ar config set access_key_id     LTAI5t...
ar config set access_key_secret ***
ar config set account_id        1234567890
ar config set region            cn-hangzhou
```

Use a named profile to separate environments:

```bash
ar config set access_key_id LTAI-staging --profile staging
ar config set region        cn-shanghai  --profile staging

# Any command can then target that profile:
ar --profile staging sandbox list
```

See [`config.md`](./config.md) for the full command reference.

## Global options

These flags apply to every subcommand and must come **before** the group name
(`ar --profile staging sandbox list`, not `ar sandbox list --profile staging`):

| Flag | Default | Description |
|------|---------|-------------|
| `--profile <name>` | `default` | Select a named profile from `~/.agentrun/config.json`. Also reads `AGENTRUN_PROFILE`. |
| `--region <id>` | profile value | Override the region for this invocation. Also reads `AGENTRUN_REGION`. |
| `--output <fmt>` | `json` | Output format: `json`, `table`, `yaml`, `quiet`. Also reads `AGENTRUN_OUTPUT`. |
| `--debug` | off | Enable DEBUG-level logging to stderr. |
| `-V`, `--version` |  | Print the CLI version. |
| `-h`, `--help` |  | Show help for any command. |

## Output formats

All commands route their result through a single formatter:

| Format | Use case | Notes |
|--------|----------|-------|
| `json` | Default — agents, scripts | Pretty-printed JSON. |
| `table` | Human reading | Renders via `rich`; falls back to JSON if `rich` not installed. |
| `yaml` | Config file generation |  |
| `quiet` | Shell piping | Prints the primary identifier only (e.g. `sandbox_id`). |

`quiet` makes scripting terse:

```bash
SANDBOX=$(ar sandbox create --template my-tpl --type CodeInterpreter --output quiet)
ar sandbox exec "$SANDBOX" --code "print('hello')"
```

## Exit codes

| Code | Meaning | Typical trigger |
|------|---------|-----------------|
| `0` | Success | Operation completed. |
| `1` | Resource not found / failed state | `get` on a missing resource; super agent ended in `*_FAILED`. |
| `2` | Bad input | Missing required flag, invalid JSON, mutually-exclusive flags combined, non-TTY missing model. |
| `3` | Authentication failure | Invalid AK/SK or insufficient permissions. |
| `4` | Server error or timeout | Backend API exception, SSE stream error, `apply --wait` timeout. |
| `130` | User interrupt | REPL received two Ctrl+C or Ctrl+D. |

Errors are written to stderr as JSON:

```json
{"error": "ResourceNotFound", "message": "Sandbox 'sb-nope' does not exist"}
```

## Command groups

| Group | Alias | Summary | Reference |
|-------|-------|---------|-----------|
| `config` |  | Credentials and named profiles | [config.md](./config.md) |
| `model` |  | ModelService registration (Tongyi, OpenAI, DeepSeek, …) | [model.md](./model.md) |
| `sandbox` | `sb` | Sandboxes plus file, process, context, template and browser sub-groups | [sandbox.md](./sandbox.md) |
| `tool` |  | MCP and FunctionCall tools + sub-tool invocation | [tool.md](./tool.md) |
| `skill` |  | Platform skill packages + local scan/load/exec | [skill.md](./skill.md) |
| `super-agent` | `sa` | Quickstart REPL, declarative deploy, CRUD, conversations | [super-agent.md](./super-agent.md) |
