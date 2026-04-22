**English** | [简体中文](../zh/sandbox.md)

# ar sandbox

Manage **Sandbox** resources — isolated execution environments for code, shell,
file system and browser operations. The command group is also available as the
shorter alias `ar sb`.

Sandbox has a Template + Instance two-layer model:

- **Template** defines the sandbox flavor (CPU/memory/network/image/env). Managed
  via the [`template`](#template-sub-group) sub-group.
- **Instance** is created from a template and is where you actually run workloads.

Four sandbox types are supported: `CodeInterpreter`, `Browser`, `AllInOne`,
`CustomImage`.

## Commands

Top-level (instance lifecycle & execution):

- [create](#create)
- [get](#get)
- [list](#list)
- [stop](#stop)
- [delete](#delete)
- [health](#health)
- [exec](#exec)
- [cmd](#cmd)

Sub-groups:

- [file](#file-sub-group) — read / write / upload / download / ls / stat / mv / rm / mkdir
- [process](#process-sub-group) — list / get / kill
- [context](#context-sub-group) — create / list / get / delete
- [template](#template-sub-group) — create / get / list / update / delete
- [browser](#browser-sub-group) — cdp-url / vnc-url / screenshot / navigate

---

## create

```
ar sandbox create --template <name> --type <type> [options]
```

### Options

| Flag | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `--template` | string | yes |  | Template name to instantiate. |
| `--type` | string | yes |  | Sandbox type: `CodeInterpreter` / `Browser` / `AllInOne` / `CustomImage`. |
| `--id` | string | no | auto | Custom sandbox id. |
| `--idle-timeout` | int | no | `600` | Idle timeout in seconds. |
| `--nas-server-addr` | string | no |  | NAS server address. |
| `--nas-mount-dir` | string | no | `/mnt/nas` | NAS mount path inside the sandbox. |
| `--oss-bucket` | string | no |  | OSS bucket name. |
| `--oss-mount-dir` | string | no | `/mnt/oss` | OSS mount path inside the sandbox. |
| `--from-file` | path | no |  | JSON file with a full `SandboxInput`. |

### Examples

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

### Examples

```bash
ar sandbox get sb-001
```

---

## list

```
ar sandbox list [options]
```

### Options

| Flag | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `--max-results` | int | no | `10` | Max results per page. |
| `--next-token` | string | no |  | Pagination token. |
| `--status` | string | no |  | Filter by status. |
| `--template` | string | no |  | Filter by template name. |
| `--type` | string | no |  | Filter by sandbox type. |

### Examples

```bash
ar sandbox list
ar sandbox list --type Browser --status Running --max-results 50
```

---

## stop

Stop a running sandbox (can be restarted).

```
ar sandbox stop <SANDBOX_ID>
```

### Examples

```bash
ar sandbox stop sb-001
```

---

## delete

Permanently delete a sandbox.

```
ar sandbox delete <SANDBOX_ID>
```

### Examples

```bash
ar sandbox delete sb-001
```

---

## health

Check sandbox health status.

```
ar sandbox health <SANDBOX_ID>
```

### Examples

```bash
ar sandbox health sb-001
```

---

## exec

Execute code inside a sandbox. Must supply either `--code` or `--file`.

```
ar sandbox exec <SANDBOX_ID> (--code <src> | --file <path>) [options]
```

### Options

| Flag | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `SANDBOX_ID` | positional | yes |  | Target sandbox id. |
| `--code` | string | one of | | Inline code to run. |
| `--file` | path | one of | | Path to a code file. |
| `--language` | string | no | `python` when `--context-id` is not set; mutually exclusive with `--context-id` | `python` or `javascript`. Passing both `--context-id` and `--language` is an error. |
| `--context-id` | string | no |  | Stateful context id (see [context](#context-sub-group)). |
| `--timeout` | int | no | `30` | Execution timeout (seconds). |

### Examples

```bash
ar sandbox exec sb-001 --code "print(2 + 3)"
ar sandbox exec sb-001 --file ./script.py --language python --timeout 120
ar sandbox exec sb-001 --code "x = 1" --context-id ctx-a
ar sandbox exec sb-001 --code "print(x)" --context-id ctx-a   # x preserved
```

---

## cmd

Execute a shell command inside a sandbox.

```
ar sandbox cmd <SANDBOX_ID> --command <cmd> --cwd <dir> [--timeout <sec>]
```

### Options

| Flag | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `SANDBOX_ID` | positional | yes |  | Target sandbox id. |
| `--command` | string | yes |  | Shell command to run. |
| `--cwd` | string | yes |  | Working directory. |
| `--timeout` | int | no | `30` | Timeout (seconds). |

### Examples

```bash
ar sandbox cmd sb-001 --command "ls -la" --cwd /tmp
ar sandbox cmd sb-001 --command "pip install requests" --cwd /workspace --timeout 120
```

---

## file sub-group

`ar sandbox file` — file system operations on a sandbox. All commands take
`<SANDBOX_ID>` as the first positional argument.

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

| Flag | Default | Description |
|------|---------|-------------|
| `--content` |  | Inline content. |
| `--stdin` | false | Read content from stdin. |
| `--mode` | `644` | File permission mode. |
| `--encoding` | `utf-8` | File encoding. |

```bash
ar sandbox file write sb-001 /tmp/hello.txt --content "Hello"
echo "piped" | ar sandbox file write sb-001 /tmp/from-pipe.txt --stdin
```

### file upload

Upload a local file to the sandbox.

```
ar sandbox file upload <SANDBOX_ID> <LOCAL_PATH> <REMOTE_PATH>
```

```bash
ar sandbox file upload sb-001 ./data.csv /workspace/data.csv
```

### file download

Download a file from the sandbox to local disk.

```
ar sandbox file download <SANDBOX_ID> <REMOTE_PATH> <LOCAL_PATH>
```

```bash
ar sandbox file download sb-001 /workspace/report.pdf ./report.pdf
```

### file ls

List directory entries.

```
ar sandbox file ls <SANDBOX_ID> [<PATH>] [--depth <n>]
```

| Flag | Default | Description |
|------|---------|-------------|
| `PATH` | `/` | Path to list. |
| `--depth` | `1` | Recursive depth. |

```bash
ar sandbox file ls sb-001 /workspace
ar sandbox file ls sb-001 /workspace --depth 3
```

### file stat

Show file metadata.

```
ar sandbox file stat <SANDBOX_ID> <PATH>
```

```bash
ar sandbox file stat sb-001 /workspace/main.py
```

### file mv

Move or rename a file.

```
ar sandbox file mv <SANDBOX_ID> <SOURCE> <DESTINATION>
```

```bash
ar sandbox file mv sb-001 /tmp/a.txt /tmp/b.txt
```

### file rm

Remove a file or directory.

```
ar sandbox file rm <SANDBOX_ID> <PATH>
```

```bash
ar sandbox file rm sb-001 /tmp/unused.log
```

### file mkdir

Create a directory.

```
ar sandbox file mkdir <SANDBOX_ID> <PATH> [--mode <octal>]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--mode` | `0755` | Directory permission mode. |

```bash
ar sandbox file mkdir sb-001 /workspace/new
ar sandbox file mkdir sb-001 /var/data --mode 0700
```

---

## process sub-group

`ar sandbox process` — inspect and kill processes inside a sandbox.

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

| Flag | Default | Description |
|------|---------|-------------|
| `--force-shell` | false | If the Process API does not know this PID, fall back to `kill -9 <PID>` via the shell. Useful for ending PIDs that appear in `process list` but were not started through the Process API. |

```bash
ar sandbox process kill sb-001 1234
ar sandbox process kill sb-001 1234 --force-shell
```

---

## context sub-group

`ar sandbox context` — manage stateful execution contexts. A context preserves
variables / imports across multiple `sandbox exec` calls (like a Jupyter kernel).

### context create

```
ar sandbox context create <SANDBOX_ID> [--language <lang>] [--cwd <dir>]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--language` | `python` | `python` or `javascript`. |
| `--cwd` |  | Working directory. |

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

## template sub-group

`ar sandbox template` — manage sandbox templates.

### template create

```
ar sandbox template create --type <type> [options]
```

| Flag | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `--type` | string | yes |  | `CodeInterpreter` / `Browser` / `AllInOne` / `CustomImage`. |
| `--name` | string | no | auto | Template name. |
| `--cpu` | float | no |  | CPU cores. |
| `--memory` | int | no |  | Memory (MB). |
| `--disk-size` | int | no |  | Disk size (MB). |
| `--idle-timeout` | int | no |  | Sandbox idle timeout (seconds). |
| `--ttl` | int | no |  | Sandbox max TTL (seconds). |
| `--concurrency` | int | no |  | Max concurrency per sandbox. |
| `--description` | string | no |  | Description. |
| `--env` | multi | no |  | Environment variable `KEY=VALUE`, repeatable. |
| `--network-mode` | string | no |  | `PUBLIC` / `PRIVATE` / `PUBLIC_AND_PRIVATE`. |
| `--credential-name` | string | no |  | Credential name. |
| `--container-image` | string | no |  | Container image (`CustomImage` type). |
| `--container-port` | int | no |  | Container port (`CustomImage` type). |
| `--from-file` | path | no |  | JSON file with a full `TemplateInput`. |

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

| Flag | Default | Description |
|------|---------|-------------|
| `--page` | `1` | Page number. |
| `--page-size` | `10` | Page size. |
| `--type` |  | Filter by type. |

### template update

```
ar sandbox template update <TEMPLATE_NAME> [options]
```

| Flag | Description |
|------|-------------|
| `--cpu` | CPU cores. |
| `--memory` | Memory (MB). |
| `--idle-timeout` | Idle timeout (seconds). |
| `--ttl` | Max TTL (seconds). |
| `--description` | Description. |
| `--env` | Environment variable `KEY=VALUE`, repeatable. |
| `--from-file` | JSON file with update fields. |

### template delete

```
ar sandbox template delete <TEMPLATE_NAME>
```

---

## browser sub-group

`ar sandbox browser` — browser automation commands (for `Browser` / `AllInOne`
sandbox types).

### browser cdp-url

Get a CDP WebSocket URL (for attaching Playwright / puppeteer / your own CDP
client).

```
ar sandbox browser cdp-url <SANDBOX_ID> [--with-headers]
```

| Flag | Description |
|------|-------------|
| `--with-headers` | Include auth headers in the response. |

```bash
ar sandbox browser cdp-url sb-001
ar sandbox browser cdp-url sb-001 --with-headers
```

### browser vnc-url

Get a VNC WebSocket URL (for live-view in a browser).

```
ar sandbox browser vnc-url <SANDBOX_ID> [--with-headers]
```

### browser screenshot

Capture a screenshot of the current page.

```
ar sandbox browser screenshot <SANDBOX_ID> [options]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--save-path` | `./screenshot.png` | Local file path. |
| `--full-page` | false | Capture full page, not just the viewport. |
| `--format` | `png` | `png` or `jpeg`. |
| `--quality` | `80` | JPEG quality 1–100. |

```bash
ar sandbox browser screenshot sb-001 --full-page --save-path page.png
ar sandbox browser screenshot sb-001 --format jpeg --quality 90
```

### browser navigate

Navigate the browser to a URL.

```
ar sandbox browser navigate <SANDBOX_ID> <URL> [options]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--wait-until` | `load` | `load`, `domcontentloaded`, or `networkidle`. |
| `--timeout` | `30` | Navigation timeout (seconds). |

```bash
ar sandbox browser navigate sb-001 https://example.com
ar sandbox browser navigate sb-001 https://example.com --wait-until networkidle --timeout 60
```
