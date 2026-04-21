[English](../en/skill.md) | **简体中文**

# ar skill

管理 **Skill** 技能包。Skill 是以 ZIP 打包的目录，包含 `SKILL.md` 指令文件和
实现代码。命令分为两个平面：

- **控制面**：上传、列表、查看、下载、删除平台上的 Skill。
- **数据面**：扫描本地 Skill、读取 `SKILL.md` 指令、读取文件、在 Skill 目录中
  执行命令。

## 子命令

控制面：

- [create](#create)
- [list](#list)
- [get](#get)
- [download](#download)
- [delete](#delete)

数据面（本地）：

- [scan](#scan)
- [load](#load)
- [read-file](#read-file)
- [exec](#exec)

---

## create

把本地 Skill 目录打包上传到平台。

```
ar skill create --name <name> --code-dir <dir> [options]
```

### 参数

| Flag | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--name` | string | 是 |  | 全局唯一 Skill 名。 |
| `--code-dir` | path | 是 |  | 包含 `SKILL.md` 的本地目录。 |
| `--description` | string | 否 | 自动 | 省略时从 `SKILL.md` 的 YAML frontmatter 读取。 |
| `--credential` | string | 否 |  | 凭证名。 |
| `--from-file` | path | 否 |  | 完整创建配置的 JSON 文件。 |

### 示例

```bash
ar skill create --name web-scraper --code-dir ./skills/web-scraper
ar skill create --name restricted --code-dir ./skills/restricted --credential my-key
```

---

## list

```
ar skill list [--page-number <n>] [--page-size <n>]
```

### 参数

| Flag | 类型 | 必填 | 说明 |
|------|------|------|------|
| `--page-number` | int | 否 | 页码。 |
| `--page-size` | int | 否 | 每页条数。 |

### 示例

```bash
ar skill list
ar skill list --page-size 50
```

---

## get

```
ar skill get --name <name>
```

### 示例

```bash
ar skill get --name web-scraper
```

---

## download

下载 Skill 包并解压到本地目录。

```
ar skill download --name <name> [--dir <dir>]
```

### 参数

| Flag | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--name` | string | 是 |  | Skill 名。 |
| `--dir` | path | 否 | `.skills` | 解压到的目标目录。 |

### 示例

```bash
ar skill download --name web-scraper
# → 解压到 ./.skills/web-scraper/

ar skill download --name web-scraper --dir ~/my-skills
```

---

## delete

```
ar skill delete --name <name>
```

### 示例

```bash
ar skill delete --name web-scraper
```

---

## scan

扫描本地 Skill 目录，列出每个 Skill 的元数据。

```
ar skill scan [--dir <dir>]
```

### 参数

| Flag | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--dir` | path | 否 | `.skills` | 要扫描的 Skills 目录。 |

### 示例

```bash
ar skill scan
ar skill scan --dir ~/my-skills
```

---

## load

打印某个本地 Skill 的指令（`SKILL.md`）和文件列表。

```
ar skill load --name <name> [--dir <dir>]
```

### 参数

| Flag | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--name` | string | 是 |  | Skill 名。 |
| `--dir` | path | 否 | `.skills` | 本地 Skills 目录。 |

### 示例

```bash
ar skill load --name web-scraper
```

如果 Skill 不存在，以退出码 `1` 结束并提示 `Skill '<name>' not found in <dir>`。

---

## read-file

读取某个 Skill 目录下的文件（或列目录），内容按原始格式打印，方便管道传给
其他工具。

```
ar skill read-file --name <name> --path <relpath> [--dir <dir>]
```

### 参数

| Flag | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--name` | string | 是 |  | Skill 名。 |
| `--path` | string | 是 |  | 相对于 Skill 目录的路径。 |
| `--dir` | path | 否 | `.skills` | 本地 Skills 目录。 |

### 示例

```bash
ar skill read-file --name web-scraper --path scraper.py
ar skill read-file --name web-scraper --path assets/  # 列目录
```

---

## exec

在 Skill 目录下执行 shell 命令（以该目录为 cwd）。

```
ar skill exec --name <name> --command <cmd> [--dir <dir>] [--timeout <sec>]
```

### 参数

| Flag | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--name` | string | 是 |  | Skill 名。 |
| `--command` | string | 是 |  | 要执行的 shell 命令。 |
| `--dir` | path | 否 | `.skills` | 本地 Skills 目录。 |
| `--timeout` | int | 否 | `300` | 超时时间（秒）。 |

### 示例

```bash
ar skill exec --name web-scraper --command "python scraper.py --url https://example.com"
ar skill exec --name my-skill --command "pytest tests/" --timeout 600
```
