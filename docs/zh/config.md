[English](../en/config.md) | **简体中文**

# ar config

管理 CLI 凭证与偏好配置，数据存于 `~/.agentrun/config.json`。每个 profile 存一套
独立的 AccessKey、账号 ID 与 region。

## 子命令

- [set](#set)
- [get](#get)
- [list](#list)

---

## set

设置某个 profile 下的单个配置项，写入 `~/.agentrun/config.json`。

```
ar config set <KEY> <VALUE> [--profile <name>]
```

### 参数

| Flag | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `KEY` | 位置参数 | 是 |  | 配置项名（见下方支持列表）。 |
| `VALUE` | 位置参数 | 是 |  | 要写入的值。 |
| `--profile <name>` | string | 否 | 当前 profile | 指定写入的 profile。 |

### 支持的 Key

- `access_key_id` —— AccessKey ID
- `access_key_secret` —— AccessKey Secret
- `account_id` —— 阿里云账号 ID
- `region` —— 地域（如 `cn-hangzhou`、`cn-shanghai`）
- `security_token` —— STS 临时凭证（可选）
- `control_endpoint` —— 覆盖控制面 endpoint
- `data_endpoint` —— 覆盖数据面 endpoint

### 示例

```bash
# 配置 default profile
ar config set access_key_id     LTAI5t...
ar config set access_key_secret ***
ar config set account_id        1234567890
ar config set region            cn-hangzhou

# 写入具名 profile
ar config set region cn-shanghai --profile staging
```

---

## get

打印某个 profile 下指定 key 的值。

```
ar config get <KEY> [--profile <name>]
```

### 参数

| Flag | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `KEY` | 位置参数 | 是 |  | 要读取的 key。 |
| `--profile <name>` | string | 否 | 当前 profile | 指定要读取的 profile。 |

### 示例

```bash
ar config get region
# cn-hangzhou

ar config get access_key_id --profile staging
# LTAI-staging-...
```

若该 key 未设置，命令以退出码 `1` 结束，stderr 会打印
`Key '<key>' is not set.`。

---

## list

以 JSON 形式打印某 profile 的全部 key。敏感字段（`access_key_secret`、
`security_token`）会做脱敏，只保留首 4 位和末 4 位。

```
ar config list [--profile <name>]
```

### 参数

| Flag | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--profile <name>` | string | 否 | 当前 profile | 指定显示哪个 profile。 |

### 示例

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

若 profile 为空，命令会打印提示而非 JSON：

```
Profile 'staging' is empty. Run 'ar config set <key> <value>' to configure.
```
