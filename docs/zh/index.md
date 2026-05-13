[English](../en/index.md) | **简体中文**

# AgentRun CLI 使用手册

`ar`（`agentrun` 的别名）是 AgentRun 平台的命令行工具，用于管理 AI Agent 相关的基础
设施。本页覆盖安装、认证、全局选项、输出格式与退出码；每个命令组的参数表与示例请
跳转到页面底部的命令组入口。

## 目录

- [安装](#安装)
- [前置准备](#前置准备)
- [认证](#认证)
- [全局选项](#全局选项)
- [输出格式](#输出格式)
- [退出码](#退出码)
- [命令组](#命令组)

## 安装

提供三种安装方式，按环境选一种即可。

### 1. 预编译二进制（无需 Python）

支持的目标：`linux-amd64`、`linux-arm64`、`darwin-amd64`、`darwin-arm64`、`windows-amd64`。

**Linux / macOS**：

```bash
curl -fsSL https://raw.githubusercontent.com/Serverless-Devs/agentrun-cli/main/scripts/install.sh | sh
```

**Windows**（PowerShell）：

```powershell
irm https://raw.githubusercontent.com/Serverless-Devs/agentrun-cli/main/scripts/install.ps1 | iex
```

两个脚本都会自动解析 GitHub Releases 上最新的 tag、校验 SHA256，然后落到用户可写目录（Unix 下为 `$HOME/.local/bin`，Windows 下为 `%LOCALAPPDATA%\Programs\agentrun`）。可通过 `AGENTRUN_VERSION`、`AGENTRUN_INSTALL`、`AGENTRUN_REPO` 覆盖。

Release 产物的命名规则：

```
agentrun-<version>-<os>-<arch>.<ext>
# agentrun-0.1.0-linux-amd64.tar.gz
# agentrun-0.1.0-linux-arm64.tar.gz
# agentrun-0.1.0-darwin-amd64.tar.gz
# agentrun-0.1.0-darwin-arm64.tar.gz
# agentrun-0.1.0-windows-amd64.zip
```

每个归档都带一个 `.sha256` 同名兄弟文件，Release 里还有一个汇总的 `SHA256SUMS`。

### 2. 从 PyPI 安装

```bash
pip install agentrun-cli
```

### 3. 从源码安装

```bash
git clone https://github.com/Serverless-Devs/agentrun-cli.git
cd agentrun-cli
make install      # editable 安装到 .venv
make build        # 本地打独立二进制 → dist/agentrun
```

安装完成后 `ar` 和 `agentrun` 都是入口点，行为完全一致。`ar` 更短，文档里的示例
默认用 `ar`。

## 前置准备

使用 `ar super-agent` 相关命令前，需要完成两项**一次性**配置。

### 1. 授权 AliyunAgentRunSuperAgentRole

AgentRun 通过自定义 RAM 服务角色 **`AliyunAgentRunSuperAgentRole`** 代你管理
运行时资源。点击下方链接，在 RAM 控制台完成授权：

[**→ 创建 AliyunAgentRunSuperAgentRole**](https://ram.console.aliyun.com/authorize?hideTopbar=true&hideSidebar=true&request=%7B%22template%22%3A%22AgentRun%22%2C%22payloads%22%3A%5B%7B%22missionId%22%3A%22SuperAgentCustomRole%22%7D%5D%7D)

未授权时 `ar super-agent run` / `apply` 在创建阶段会直接失败。

### 2. 给 AccessKey 授予 `AliyunAgentRunFullAccess`

下文 [认证](#认证) 章节中配置的 AccessKey，所属 RAM 用户/角色需要挂载系统策略
**`AliyunAgentRunFullAccess`**。命令报 `AccessDenied` 或退出码 `3` 时，多半就是
少了这一项权限。

### 想体验更完整的能力？请前往控制台

本 CLI 完整覆盖 QuickStart 快速对话流程。如需可视化编排、Observability、
知识库、Agent 市场等更完整的能力，请前往函数计算 AgentRun 控制台：
<https://functionai.console.aliyun.com/cn-hangzhou/agent/>

## 认证

CLI 按以下顺序解析凭证（上面优先）：

1. **命令行显式参数** —— 根命令的 `--region`。
2. **配置文件 profile** —— `~/.agentrun/config.json` 里某个 profile 的值。
3. **环境变量** —— `AGENTRUN_*` / `ALIBABA_CLOUD_*` / `FC_*`。

平台需要的四个关键字段：

| Key | 用途 | 环境变量回退 |
|-----|------|--------------|
| `access_key_id` | AccessKey ID | `AGENTRUN_ACCESS_KEY_ID`、`ALIBABA_CLOUD_ACCESS_KEY_ID` |
| `access_key_secret` | AccessKey Secret | `AGENTRUN_ACCESS_KEY_SECRET`、`ALIBABA_CLOUD_ACCESS_KEY_SECRET` |
| `account_id` | 阿里云账号 ID | `AGENTRUN_ACCOUNT_ID`、`FC_ACCOUNT_ID` |
| `region` | 地域（如 `cn-hangzhou`） | `AGENTRUN_REGION`、`FC_REGION` |

可选的 `security_token`（STS 临时凭证）从 `AGENTRUN_SECURITY_TOKEN` 或
`ALIBABA_CLOUD_SECURITY_TOKEN` 读取。

一次性写好四项：

```bash
ar config set access_key_id     LTAI5t...
ar config set access_key_secret ***
ar config set account_id        1234567890
ar config set region            cn-hangzhou
```

用具名 profile 隔离多套环境：

```bash
ar config set access_key_id LTAI-staging --profile staging
ar config set region        cn-shanghai  --profile staging

# 任意命令都可以切换到指定 profile：
ar --profile staging sandbox list
```

完整命令见 [`config.md`](./config.md)。

## 全局选项

以下选项对所有子命令都有效，且必须写在 **命令组名前面**
（`ar --profile staging sandbox list`，不是 `ar sandbox list --profile staging`）：

| Flag | 默认值 | 说明 |
|------|--------|------|
| `--profile <name>` | `default` | 选择 `~/.agentrun/config.json` 中的 profile，也读取 `AGENTRUN_PROFILE`。 |
| `--region <id>` | profile 里的值 | 覆盖本次调用的 region，也读取 `AGENTRUN_REGION`。 |
| `--output <fmt>` | `json` | 输出格式：`json` / `table` / `yaml` / `quiet`，也读取 `AGENTRUN_OUTPUT`。 |
| `--debug` | 关闭 | 开启 DEBUG 级别日志（写到 stderr）。 |
| `-V`、`--version` |  | 打印 CLI 版本。 |
| `-h`、`--help` |  | 打印命令帮助。 |

## 输出格式

所有命令的结果都经过统一的格式化器处理：

| 格式 | 适用场景 | 备注 |
|------|----------|------|
| `json` | 默认值 —— Agent、脚本 | 格式化后的 JSON。 |
| `table` | 人类阅读 | 通过 `rich` 渲染，若未安装则回退 JSON。 |
| `yaml` | 生成配置文件 |  |
| `quiet` | Shell 管道 | 只打印主标识符（如 `sandbox_id`）。 |

`quiet` 让脚本书写更简洁：

```bash
SANDBOX=$(ar sandbox create --template my-tpl --type CodeInterpreter --output quiet)
ar sandbox exec "$SANDBOX" --code "print('hello')"
```

## 退出码

| Code | 含义 | 典型触发场景 |
|------|------|--------------|
| `0` | 成功 | 操作完成。 |
| `1` | 资源不存在 / 失败态 | `get` 不存在的资源；Super Agent 停留在 `*_FAILED`。 |
| `2` | 参数错误 | 缺少必填参数、非法 JSON、互斥参数同时出现、非 TTY 缺 model。 |
| `3` | 认证失败 | AK/SK 无效或权限不足。 |
| `4` | 服务端错误 / 超时 | 后端 API 异常、SSE 流中断、`apply --wait` 超时。 |
| `130` | 用户中断 | REPL 中连按两次 Ctrl+C 或 Ctrl+D。 |

错误以 JSON 形式写到 stderr：

```json
{"error": "ResourceNotFound", "message": "Sandbox 'sb-nope' does not exist"}
```

## 命令组

| 命令组 | 别名 | 概要 | 参考 |
|--------|------|------|------|
| `config` |  | 凭证与多 profile 管理 | [config.md](./config.md) |
| `model` |  | 注册 ModelService（通义、OpenAI、DeepSeek……） | [model.md](./model.md) |
| `sandbox` | `sb` | 沙箱以及 file / process / context / template / browser 子组 | [sandbox.md](./sandbox.md) |
| `tool` |  | MCP 与 FunctionCall 工具 + 子工具调用 | [tool.md](./tool.md) |
| `skill` |  | 平台侧技能包 + 本地 scan / load / exec + 批量同步到 AI 工具目录 | [skill.md](./skill.md) |
| `super-agent` | `sa` | 一键拉起 REPL、声明式部署、CRUD、会话管理 | [super-agent.md](./super-agent.md) |
