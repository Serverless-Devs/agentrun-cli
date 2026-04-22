[English](../en/sandbox.md) | **简体中文**

# ar sandbox

管理 **Sandbox** 资源 —— 运行代码、Shell、文件系统与浏览器操作的隔离环境。
本命令组支持短别名 `ar sb`。

Sandbox 采用 Template + Instance 两层模型：

- **Template** 定义沙箱规格（CPU / 内存 / 网络 / 镜像 / 环境变量）。管理入口是
  [`template`](#template-子命令组) 子组。
- **Instance** 从 Template 创建，是实际运行任务的地方。

沙箱类型共有四种：`CodeInterpreter`、`Browser`、`AllInOne`、`CustomImage`。

## 子命令

顶层（实例生命周期与执行）：

- [create](#create)
- [get](#get)
- [list](#list)
- [stop](#stop)
- [delete](#delete)
- [health](#health)
- [exec](#exec)
- [cmd](#cmd)

子组：

- [file](#file-子命令组) —— read / write / upload / download / ls / stat / mv / rm / mkdir
- [process](#process-子命令组) —— list / get / kill
- [context](#context-子命令组) —— create / list / get / delete
- [template](#template-子命令组) —— create / get / list / update / delete
- [browser](#browser-子命令组) —— cdp-url / vnc-url / screenshot / navigate

---

## create

```
ar sandbox create --template <name> --type <type> [options]
```

### 参数

| Flag | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--template` | string | 是 |  | 要实例化的 Template 名。 |
| `--type` | string | 是 |  | 沙箱类型：`CodeInterpreter` / `Browser` / `AllInOne` / `CustomImage`。 |
| `--id` | string | 否 | 自动 | 自定义 sandbox id。 |
| `--idle-timeout` | int | 否 | `600` | 空闲超时（秒）。 |
| `--nas-server-addr` | string | 否 |  | NAS 服务地址。 |
| `--nas-mount-dir` | string | 否 | `/mnt/nas` | NAS 在沙箱内的挂载路径。 |
| `--oss-bucket` | string | 否 |  | OSS bucket 名。 |
| `--oss-mount-dir` | string | 否 | `/mnt/oss` | OSS 在沙箱内的挂载路径。 |
| `--from-file` | path | 否 |  | 完整 `SandboxInput` 的 JSON 文件。 |

### 示例

```bash
ar sandbox create --template my-tpl --type CodeInterpreter
ar sandbox create --template browser-tpl --type Browser --idle-timeout 1800
ar sandbox create --template aio-tpl --type AllInOne \
  --oss-bucket my-bucket --oss-mount-dir /data
```

---

## get

```
ar sandbox get <SANDBOX_ID>
```

### 示例

```bash
ar sandbox get sb-001
```

---

## list

```
ar sandbox list [options]
```

### 参数

| Flag | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--max-results` | int | 否 | `10` | 每页最大条数。 |
| `--next-token` | string | 否 |  | 分页 token。 |
| `--status` | string | 否 |  | 按状态过滤。 |
| `--template` | string | 否 |  | 按 Template 名过滤。 |
| `--type` | string | 否 |  | 按沙箱类型过滤。 |

### 示例

```bash
ar sandbox list
ar sandbox list --type Browser --status Running --max-results 50
```

---

## stop

停止沙箱（可再次启动）。

```
ar sandbox stop <SANDBOX_ID>
```

### 示例

```bash
ar sandbox stop sb-001
```

---

## delete

永久删除沙箱。

```
ar sandbox delete <SANDBOX_ID>
```

### 示例

```bash
ar sandbox delete sb-001
```

---

## health

检查沙箱健康状态。

```
ar sandbox health <SANDBOX_ID>
```

### 示例

```bash
ar sandbox health sb-001
```

---

## exec

在沙箱中执行代码。`--code` 和 `--file` 至少提供一个。

```
ar sandbox exec <SANDBOX_ID> (--code <src> | --file <path>) [options]
```

### 参数

| Flag | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `SANDBOX_ID` | 位置参数 | 是 |  | 目标沙箱 id。 |
| `--code` | string | 二选一 | | 内联代码。 |
| `--file` | path | 二选一 | | 代码文件路径。 |
| `--language` | string | 否 | 不带 `--context-id` 时为 `python`；与 `--context-id` 互斥 | `python` 或 `javascript`。与 `--context-id` 同时传会报错。 |
| `--context-id` | string | 否 |  | 有状态上下文 id（见 [context](#context-子命令组)）。 |
| `--timeout` | int | 否 | `30` | 执行超时（秒）。 |

### 示例

```bash
ar sandbox exec sb-001 --code "print(2 + 3)"
ar sandbox exec sb-001 --file ./script.py --language python --timeout 120
ar sandbox exec sb-001 --code "x = 1" --context-id ctx-a
ar sandbox exec sb-001 --code "print(x)" --context-id ctx-a   # x 仍在
```

---

## cmd

在沙箱中执行 Shell 命令。

```
ar sandbox cmd <SANDBOX_ID> --command <cmd> --cwd <dir> [--timeout <sec>]
```

### 参数

| Flag | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `SANDBOX_ID` | 位置参数 | 是 |  | 目标沙箱 id。 |
| `--command` | string | 是 |  | 要执行的 Shell 命令。 |
| `--cwd` | string | 是 |  | 工作目录。 |
| `--timeout` | int | 否 | `30` | 超时（秒）。 |

### 示例

```bash
ar sandbox cmd sb-001 --command "ls -la" --cwd /tmp
ar sandbox cmd sb-001 --command "pip install requests" --cwd /workspace --timeout 120
```

---

## file 子命令组

`ar sandbox file` —— 在沙箱中执行文件系统操作。所有命令的第一个位置参数都是
`<SANDBOX_ID>`。

### file read

```
ar sandbox file read <SANDBOX_ID> <PATH>
```

```bash
ar sandbox file read sb-001 /workspace/main.py
```

### file write

```
ar sandbox file write <SANDBOX_ID> <PATH> [--content <text> | --stdin] [--mode <octal>] [--encoding <enc>]
```

| Flag | 默认 | 说明 |
|------|------|------|
| `--content` |  | 内联内容。 |
| `--stdin` | false | 从 stdin 读取内容。 |
| `--mode` | `644` | 文件权限。 |
| `--encoding` | `utf-8` | 文件编码。 |

```bash
ar sandbox file write sb-001 /tmp/hello.txt --content "你好"
echo "from pipe" | ar sandbox file write sb-001 /tmp/from-pipe.txt --stdin
```

### file upload

把本地文件上传到沙箱。

```
ar sandbox file upload <SANDBOX_ID> <LOCAL_PATH> <REMOTE_PATH>
```

```bash
ar sandbox file upload sb-001 ./data.csv /workspace/data.csv
```

### file download

从沙箱下载文件到本地。

```
ar sandbox file download <SANDBOX_ID> <REMOTE_PATH> <LOCAL_PATH>
```

```bash
ar sandbox file download sb-001 /workspace/report.pdf ./report.pdf
```

### file ls

列出目录。

```
ar sandbox file ls <SANDBOX_ID> [<PATH>] [--depth <n>]
```

| Flag | 默认 | 说明 |
|------|------|------|
| `PATH` | `/` | 要列出的路径。 |
| `--depth` | `1` | 递归深度。 |

```bash
ar sandbox file ls sb-001 /workspace
ar sandbox file ls sb-001 /workspace --depth 3
```

### file stat

查看文件元数据。

```
ar sandbox file stat <SANDBOX_ID> <PATH>
```

```bash
ar sandbox file stat sb-001 /workspace/main.py
```

### file mv

移动或重命名文件。

```
ar sandbox file mv <SANDBOX_ID> <SOURCE> <DESTINATION>
```

```bash
ar sandbox file mv sb-001 /tmp/a.txt /tmp/b.txt
```

### file rm

删除文件或目录。

```
ar sandbox file rm <SANDBOX_ID> <PATH>
```

```bash
ar sandbox file rm sb-001 /tmp/unused.log
```

### file mkdir

创建目录。

```
ar sandbox file mkdir <SANDBOX_ID> <PATH> [--mode <octal>]
```

| Flag | 默认 | 说明 |
|------|------|------|
| `--mode` | `0755` | 目录权限。 |

```bash
ar sandbox file mkdir sb-001 /workspace/new
ar sandbox file mkdir sb-001 /var/data --mode 0700
```

---

## process 子命令组

`ar sandbox process` —— 查看与终止沙箱中的进程。

### process list

```
ar sandbox process list <SANDBOX_ID>
```

```bash
ar sandbox process list sb-001
```

### process get

```
ar sandbox process get <SANDBOX_ID> <PID>
```

```bash
ar sandbox process get sb-001 1234
```

### process kill

```
ar sandbox process kill <SANDBOX_ID> <PID> [--force-shell]
```

| Flag | 默认 | 说明 |
|------|------|------|
| `--force-shell` | false | Process API 找不到该 PID 时，回退为在沙箱内执行 `kill -9 <PID>`。适合终止 `process list` 显示但未由 Process API 登记的普通 PID。 |

```bash
ar sandbox process kill sb-001 1234
ar sandbox process kill sb-001 1234 --force-shell
```

---

## context 子命令组

`ar sandbox context` —— 管理有状态的执行上下文。Context 在多次 `sandbox exec`
调用之间保留变量与 import（类似 Jupyter Kernel）。

### context create

```
ar sandbox context create <SANDBOX_ID> [--language <lang>] [--cwd <dir>]
```

| Flag | 默认 | 说明 |
|------|------|------|
| `--language` | `python` | `python` 或 `javascript`。 |
| `--cwd` |  | 工作目录。 |

```bash
ar sandbox context create sb-001
ar sandbox context create sb-001 --language javascript --cwd /workspace
```

### context list

```
ar sandbox context list <SANDBOX_ID>
```

### context get

```
ar sandbox context get <SANDBOX_ID> <CONTEXT_ID>
```

### context delete

```
ar sandbox context delete <SANDBOX_ID> <CONTEXT_ID>
```

---

## template 子命令组

`ar sandbox template` —— 管理沙箱模板。

### template create

```
ar sandbox template create --type <type> [options]
```

| Flag | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--type` | string | 是 |  | `CodeInterpreter` / `Browser` / `AllInOne` / `CustomImage`。 |
| `--name` | string | 否 | 自动 | 模板名。 |
| `--cpu` | float | 否 |  | CPU 核数。 |
| `--memory` | int | 否 |  | 内存（MB）。 |
| `--disk-size` | int | 否 |  | 磁盘（MB）。 |
| `--idle-timeout` | int | 否 |  | 空闲超时（秒）。 |
| `--ttl` | int | 否 |  | 沙箱最长 TTL（秒）。 |
| `--concurrency` | int | 否 |  | 每个沙箱最大并发。 |
| `--description` | string | 否 |  | 描述。 |
| `--env` | multi | 否 |  | 环境变量 `KEY=VALUE`，可重复。 |
| `--network-mode` | string | 否 |  | `PUBLIC` / `PRIVATE` / `PUBLIC_AND_PRIVATE`。 |
| `--credential-name` | string | 否 |  | 凭证名。 |
| `--container-image` | string | 否 |  | 容器镜像（`CustomImage` 类型）。 |
| `--container-port` | int | 否 |  | 容器端口（`CustomImage` 类型）。 |
| `--from-file` | path | 否 |  | 完整 `TemplateInput` 的 JSON 文件。 |

```bash
ar sandbox template create --type CodeInterpreter --name my-tpl \
  --cpu 1 --memory 2048 --idle-timeout 900
ar sandbox template create --type CustomImage --name my-custom \
  --container-image registry.example.com/my-env:v1 --container-port 8080
```

### template get

```
ar sandbox template get <TEMPLATE_NAME>
```

### template list

```
ar sandbox template list [--page <n>] [--page-size <n>] [--type <type>]
```

| Flag | 默认 | 说明 |
|------|------|------|
| `--page` | `1` | 页码。 |
| `--page-size` | `10` | 每页条数。 |
| `--type` |  | 按类型过滤。 |

### template update

```
ar sandbox template update <TEMPLATE_NAME> [options]
```

| Flag | 说明 |
|------|------|
| `--cpu` | CPU 核数。 |
| `--memory` | 内存（MB）。 |
| `--idle-timeout` | 空闲超时（秒）。 |
| `--ttl` | 最长 TTL（秒）。 |
| `--description` | 描述。 |
| `--env` | 环境变量 `KEY=VALUE`，可重复。 |
| `--from-file` | 更新字段的 JSON 文件。 |

### template delete

```
ar sandbox template delete <TEMPLATE_NAME>
```

---

## browser 子命令组

`ar sandbox browser` —— 浏览器自动化命令（适用于 `Browser` / `AllInOne` 类型沙箱）。

### browser cdp-url

获取 CDP WebSocket URL（供 Playwright / Puppeteer / 自定义 CDP 客户端接入）。

```
ar sandbox browser cdp-url <SANDBOX_ID> [--with-headers]
```

| Flag | 说明 |
|------|------|
| `--with-headers` | 返回内容包含鉴权 Headers。 |

```bash
ar sandbox browser cdp-url sb-001
ar sandbox browser cdp-url sb-001 --with-headers
```

### browser vnc-url

获取 VNC WebSocket URL（浏览器内实时查看画面）。

```
ar sandbox browser vnc-url <SANDBOX_ID> [--with-headers]
```

### browser screenshot

对当前页面截图。

```
ar sandbox browser screenshot <SANDBOX_ID> [options]
```

| Flag | 默认 | 说明 |
|------|------|------|
| `--save-path` | `./screenshot.png` | 本地保存路径。 |
| `--full-page` | false | 截整页，而非 viewport。 |
| `--format` | `png` | `png` 或 `jpeg`。 |
| `--quality` | `80` | JPEG 质量 1–100。 |

```bash
ar sandbox browser screenshot sb-001 --full-page --save-path page.png
ar sandbox browser screenshot sb-001 --format jpeg --quality 90
```

### browser navigate

浏览器跳转到指定 URL。

```
ar sandbox browser navigate <SANDBOX_ID> <URL> [options]
```

| Flag | 默认 | 说明 |
|------|------|------|
| `--wait-until` | `load` | `load` / `domcontentloaded` / `networkidle`。 |
| `--timeout` | `30` | 导航超时（秒）。 |

```bash
ar sandbox browser navigate sb-001 https://example.com
ar sandbox browser navigate sb-001 https://example.com --wait-until networkidle --timeout 60
```
