**English** | [简体中文](../zh/config.md)

# ar config

Manage credentials and CLI preferences stored in `~/.agentrun/config.json`.
Each profile holds an independent set of AccessKey, account ID and region.

## Commands

- [set](#set)
- [get](#get)
- [list](#list)

---

## set

Set a single key in a profile. Writes to `~/.agentrun/config.json`.

```
ar config set <KEY> <VALUE> [--profile <name>]
```

### Options

| Flag | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `KEY` | positional | yes |  | Configuration key (see supported keys below). |
| `VALUE` | positional | yes |  | Value to write. |
| `--profile <name>` | string | no | active profile | Profile to write to. |

### Supported keys

- `access_key_id` — AccessKey ID
- `access_key_secret` — AccessKey Secret
- `account_id` — Alibaba Cloud account ID
- `region` — Region (e.g. `cn-hangzhou`, `cn-shanghai`)
- `security_token` — STS temporary token (optional)
- `control_endpoint` — Override control-plane endpoint
- `data_endpoint` — Override data-plane endpoint

### Examples

```bash
# Configure the default profile
ar config set access_key_id     LTAI5t...
ar config set access_key_secret ***
ar config set account_id        1234567890
ar config set region            cn-hangzhou

# Write to a named profile
ar config set region cn-shanghai --profile staging
```

---

## get

Print the value of a single key from a profile.

```
ar config get <KEY> [--profile <name>]
```

### Options

| Flag | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `KEY` | positional | yes |  | Key to read. |
| `--profile <name>` | string | no | active profile | Profile to read from. |

### Examples

```bash
ar config get region
# cn-hangzhou

ar config get access_key_id --profile staging
# LTAI-staging-...
```

If the key is unset the command exits with status `1` and the message
`Key '<key>' is not set.` on stderr.

---

## list

Print all keys in a profile as JSON. Secret fields (`access_key_secret`,
`security_token`) are masked so the first and last four characters are shown.

```
ar config list [--profile <name>]
```

### Options

| Flag | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `--profile <name>` | string | no | active profile | Profile to display. |

### Examples

```bash
ar config list
# {
#   "access_key_id": "LTAI5t...",
#   "access_key_secret": "LTAI***XXXX",
#   "account_id": "1234567890",
#   "region": "cn-hangzhou"
# }

ar config list --profile staging
```

If the profile is empty, the CLI prints a hint instead of JSON:

```
Profile 'staging' is empty. Run 'ar config set <key> <value>' to configure.
```
