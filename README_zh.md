[English](./README.md) | **简体中文**

# AgentRun CLI

> 管理 AgentRun 平台 AI Agent 基础设施的命令行工具。

`ar`（或 `agentrun`）是对 AgentRun Python SDK 的一个单二进制封装，让开发者、CI 流水线
和 LLM Agent 能够创建并操作沙箱、工具、技能、模型服务，最重要的是 **超级 Agent（Super
Agent）**：一种由平台托管、用户只需声明配置、无需编写或部署任何运行时代码的 AI Agent。

## 特性

- **一键拉起超级 Agent** — `ar super-agent run` 一条命令创建托管 Agent 并进入 REPL 对话。
- **声明式部署** — Kubernetes 风格 YAML（`ar sa apply -f superagent.yaml`），可版本化、可重复部署。
- **六大资源组** — `config`、`model`、`sandbox`、`tool`、`skill`、`super-agent`，统一 `ar <group> <action>` 模式。
- **多 Profile 配置** — `~/.agentrun/config.json` 支持多套凭证，通过 `--profile` 切换。
- **多种输出格式** — 默认 `json`，支持 `table` / `yaml` / `quiet`（适合 shell 管道）。
- **对 Agent 友好** — 默认 JSON 输出、确定性退出码、非 TTY 下不弹交互提示。
- **完整沙箱能力** — 代码执行、文件系统、进程管理、CDP/VNC 浏览器自动化。
- **单文件分发** — 基于 Nuitka `--onefile` 产出 Linux / macOS / Windows（x86_64 + arm64）上的独立 `ar` / `agentrun` 二进制，热启动复用 `~/.agentrun/cache/` 缓存。

## 安装

### 预编译二进制（推荐）

从 [Releases](https://github.com/Serverless-Devs/agentrun-cli/releases) 下载单文件二进制，无需 Python。

**Linux / macOS**（x86_64 或 arm64）：

```bash
curl -fsSL https://raw.githubusercontent.com/Serverless-Devs/agentrun-cli/main/scripts/install.sh | sh
```

**Windows**（x86_64，PowerShell）：

```powershell
irm https://raw.githubusercontent.com/Serverless-Devs/agentrun-cli/main/scripts/install.ps1 | iex
```

通过 `AGENTRUN_VERSION=v0.1.0 …` 指定版本；通过 `AGENTRUN_INSTALL=…` 指定安装目录。两个安装脚本都会在落盘前校验 SHA256。

也可以从 Release 页面手动下载对应归档，命名规则：

```
agentrun-<version>-<os>-<arch>.<ext>
# 例如 agentrun-0.1.0-linux-amd64.tar.gz
#      agentrun-0.1.0-darwin-arm64.tar.gz
#      agentrun-0.1.0-windows-amd64.zip
```

### 从 PyPI 安装

```bash
pip install agentrun-cli
```

### 从源码安装

```bash
git clone https://github.com/Serverless-Devs/agentrun-cli.git
cd agentrun-cli
make install            # editable 安装到 .venv
make build              # 本地打独立二进制 → dist/agentrun
```

### 验证

```bash
ar --version            # 或者 agentrun --version
```

## 快速开始

### 第 1 步 —— 配置凭证

```bash
ar config set access_key_id     LTAI5t...
ar config set access_key_secret ***
ar config set account_id        1234567890
ar config set region            cn-hangzhou
```

凭证会落到 `~/.agentrun/config.json` 的 `default` profile。任何命令都可以通过
`--profile staging` 切换到指定 profile。

### 第 2 步 —— 一键拉起超级 Agent 并对话

```bash
$ ar super-agent run --prompt "你是一个 Python 专家"
Loading model services...
? Select model service: svc-tongyi
? Select model:         qwen-max
Creating super agent: super-agent-tmp-20260420213045 ...
Ready. Type your message (/help for commands).

> 写一个快速排序
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

退出后 Agent 会保留，下次直接用 `ar sa chat <name>` 续聊 —— CLI 会把上次的
conversation id 记在本地，自动续上。

### 第 3 步 —— 声明式部署

将下面内容保存为 `superagent.yaml`：

```yaml
apiVersion: agentrun/v1
kind: SuperAgent
metadata:
  name: my-helper
  description: "我的助手"
spec:
  prompt: "你是我的得力助手"
  model:
    service: svc-tongyi
    name: qwen-max
  tools:
    - mcp-time-sa
  skills: []
  sandboxes: []
  workspaces: []
  subAgents: []
```

然后部署：

```bash
ar super-agent apply -f superagent.yaml
# → action: "created"    （首次运行）
# → action: "updated"    （后续运行）

# 对话
ar sa chat my-helper

# 脚本场景：一次性调用
ar sa invoke my-helper -m "帮我规划今天的事情" --text-only
```

多文档 YAML（用 `---` 分隔）可以一次部署多个 Agent。

## 命令组总览

| 命令组 | 别名 | 用途 | 文档 |
|--------|------|------|------|
| `config` |  | 凭证与多 profile 管理 | [en](./docs/en/config.md) · [zh](./docs/zh/config.md) |
| `model` |  | 接入外部 LLM Provider 成为 ModelService | [en](./docs/en/model.md) · [zh](./docs/zh/model.md) |
| `sandbox` | `sb` | 沙箱 + 文件、进程、上下文、模板、浏览器 | [en](./docs/en/sandbox.md) · [zh](./docs/zh/sandbox.md) |
| `tool` |  | MCP 与 FunctionCall 工具 | [en](./docs/en/tool.md) · [zh](./docs/zh/tool.md) |
| `skill` |  | 平台技能包 + 本地执行 | [en](./docs/en/skill.md) · [zh](./docs/zh/skill.md) |
| `super-agent` | `sa` | 一键拉起 / CRUD / 声明式 / 会话管理 | [en](./docs/en/super-agent.md) · [zh](./docs/zh/super-agent.md) |

## 文档

- 中文手册: [docs/zh/index.md](./docs/zh/index.md)
- English reference: [docs/en/index.md](./docs/en/index.md)

每份文档涵盖安装、认证、全局选项、输出格式、退出码以及每个命令的全部选项，附可运行示例。

## License

Apache-2.0 — 详见 [LICENSE](./LICENSE)。
