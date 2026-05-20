**English** | [简体中文](../zh/runtime.md)

# ar runtime

Manage **Agent Runtimes** declaratively from a YAML file. The CLI only supports
container-mode runtimes (you supply an OCI image; building the image is out of
scope for this command group). Endpoints are embedded in the same YAML; the
default behaviour is to inject one named `default` (`targetVersion=LATEST`).

Also available as the alias `ar rt`.

> **Heads up:** before running any command here, complete the two one-time
> setup steps in [Prerequisites](./index.md#prerequisites). Missing roles or
> policies surface as exit code `3`.

## Commands

- [apply](#apply) — create-or-update from YAML, with status polling.
- [render](#render) — dry-run validate + render to SDK input.
- [get](#get) — fetch one runtime by name.
- [list](#list) — list runtimes; filter by `--created-by-cli` or `--workspace`.
- [delete](#delete) — delete a runtime (waits by default).
- [status](#status) — fetch (and optionally wait for) terminal status.

Exit codes (extends global table):

| Code | Meaning |
|------|---------|
| `5` | Runtime or endpoint ended in `CREATE_FAILED`, `UPDATE_FAILED`, or `DELETE_FAILED`. |
| `6` | Polling exceeded `--timeout`. |

---

## apply

```
ar runtime apply -f FILE [--wait/--no-wait] [--timeout DURATION]
                       [--prune-endpoints/--no-prune-endpoints]
```

### Options

| Flag | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `-f`, `--file` | path | yes |  | YAML file path (supports multi-document). |
| `--wait/--no-wait` | flag | no | `--wait` | Poll runtime + endpoints to final status. Under `--no-wait` the runtime is submitted but **endpoints are not reconciled** — the backend rejects endpoint create/update while the runtime is still `CREATING`/`UPDATING`. Re-run apply once it reaches `READY`. |
| `--timeout` | duration | no | `10m` | Polling timeout. Accepts `Ns`, `Nm`, `Nh`, or bare seconds. |
| `--prune-endpoints/--no-prune-endpoints` | flag | no | `--prune-endpoints` | Delete remote endpoints absent from the YAML. |

The CLI injects sensible defaults for `cpu` (2 cores), `memory` (4096 MB) and
`port` (9000) when the YAML omits them — the backend rejects null values for
these three fields with HTTP 400.

### Examples

```bash
# Minimal: container-only, default endpoint auto-injected.
cat > runtime.yaml <<'EOF'
apiVersion: agentrun/v1
kind: AgentRuntime
metadata: {name: my-agent}
spec:
  container:
    image: registry.cn-hangzhou.aliyuncs.com/my-ns/my-agent:v1
EOF
ar runtime apply -f runtime.yaml

# Non-blocking submit (CI-friendly):
ar runtime apply -f runtime.yaml --no-wait

# Custom timeout:
ar runtime apply -f runtime.yaml --timeout 20m

# Disable endpoint pruning when migrating between YAML files:
ar runtime apply -f runtime.yaml --no-prune-endpoints
```

---

## render

```
ar runtime render -f FILE
```

### Options

| Flag | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `-f`, `--file` | path | yes |  | YAML file path (supports multi-document). |

Validates the YAML, applies CLI auto-injection (`system_tags=["x-agentrun-cli"]`,
`artifact_type=Container`, default endpoint when `spec.endpoints` is omitted),
and prints the SDK create-input as JSON without calling the server. Use this to
preview changes before `apply`.

---

## get

```
ar runtime get NAME
```

Show a single Agent Runtime as JSON. Exits `1` if no runtime with that name exists.

### Examples

```bash
ar runtime get my-agent
ar runtime get my-agent --output quiet     # prints just the name
```

---

## list

```
ar runtime list [--created-by-cli] [--workspace NAME]
```

### Options

| Flag | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `--created-by-cli` | flag | no | false | Only show runtimes carrying the `x-agentrun-cli` system tag. |
| `--workspace` | string | no |  | Restrict to runtimes belonging to the named workspace. |

### Examples

```bash
ar runtime list
ar runtime list --created-by-cli
ar runtime list --output table
```

---

## delete

```
ar runtime delete NAME [--wait/--no-wait] [--timeout DURATION] [--yes]
```

### Options

| Flag | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `--wait/--no-wait` | flag | no | `--wait` | Block until the runtime is gone (or fails). |
| `--timeout` | duration | no | `5m` | Polling timeout. |
| `--yes` | flag | no | false | Skip the interactive confirmation prompt. |

### Examples

```bash
ar runtime delete my-agent --yes
ar runtime delete my-agent --no-wait
```

---

## status

```
ar runtime status NAME [--wait] [--timeout DURATION]
```

### Options

| Flag | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `--wait` | flag | no | false | Poll until the runtime reaches READY / *_FAILED. |
| `--timeout` | duration | no | `10m` | Polling timeout (only meaningful with `--wait`). |

### Examples

```bash
ar runtime status my-agent
ar runtime status my-agent --wait --timeout 20m
```

---

## YAML schema

See [**runtime-yaml.md**](./runtime-yaml.md) for the full field reference,
CLI auto-injection rules, validation table, and copy-pasteable examples
(minimal, production, and custom-registry).
