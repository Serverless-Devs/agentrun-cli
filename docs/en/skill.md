**English** | [简体中文](../zh/skill.md)

# ar skill

Manage **Skill** packages. A skill is a ZIP-packaged directory containing a
`SKILL.md` instruction file plus implementation code. Skills split into two
planes:

- **Control plane** — upload, list, get, download, delete skills on the platform.
- **Data plane** — scan local skills, load their instruction, read files, and
  execute commands inside a skill's directory.

## Commands

Control plane:

- [create](#create)
- [list](#list)
- [get](#get)
- [download](#download)
- [delete](#delete)

Data plane (local):

- [scan](#scan)
- [load](#load)
- [read-file](#read-file)
- [exec](#exec)

---

## create

Upload a local skill directory to the platform.

```
ar skill create --name <name> --code-dir <dir> [options]
```

### Options

| Flag | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `--name` | string | yes |  | Skill name (globally unique). |
| `--code-dir` | path | yes |  | Local directory containing `SKILL.md`. |
| `--description` | string | no | auto | If omitted, read from YAML frontmatter of `SKILL.md`. |
| `--credential` | string | no |  | Credential name. |
| `--from-file` | path | no |  | JSON file with the full create config. |

### Examples

```bash
ar skill create --name web-scraper --code-dir ./skills/web-scraper
ar skill create --name restricted --code-dir ./skills/restricted --credential my-key
```

---

## list

```
ar skill list [--page-number <n>] [--page-size <n>]
```

### Options

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--page-number` | int | no | Page number. |
| `--page-size` | int | no | Page size. |

### Examples

```bash
ar skill list
ar skill list --page-size 50
```

---

## get

```
ar skill get --name <name>
```

### Examples

```bash
ar skill get --name web-scraper
```

---

## download

Download a skill package and unpack it to a local directory.

```
ar skill download --name <name> [--dir <dir>]
```

### Options

| Flag | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `--name` | string | yes |  | Skill name. |
| `--dir` | path | no | `.skills` | Target directory to unpack into. |

### Examples

```bash
ar skill download --name web-scraper
# → unpacks to ./.skills/web-scraper/

ar skill download --name web-scraper --dir ~/my-skills
```

---

## delete

```
ar skill delete --name <name>
```

### Examples

```bash
ar skill delete --name web-scraper
```

---

## scan

Scan a local skills directory and list each skill's metadata.

```
ar skill scan [--dir <dir>]
```

### Options

| Flag | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `--dir` | path | no | `.skills` | Skills directory to scan. |

### Examples

```bash
ar skill scan
ar skill scan --dir ~/my-skills
```

---

## load

Print the instruction (`SKILL.md`) and file list of a local skill.

```
ar skill load --name <name> [--dir <dir>]
```

### Options

| Flag | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `--name` | string | yes |  | Skill name. |
| `--dir` | path | no | `.skills` | Local skills directory. |

### Examples

```bash
ar skill load --name web-scraper
```

Exits with status `1` and `Skill '<name>' not found in <dir>` if the skill is
missing.

---

## read-file

Read a file (or list a directory) inside a skill's directory, printed as raw
content so it can be piped to other tools.

```
ar skill read-file --name <name> --path <relpath> [--dir <dir>]
```

### Options

| Flag | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `--name` | string | yes |  | Skill name. |
| `--path` | string | yes |  | Relative path inside the skill directory. |
| `--dir` | path | no | `.skills` | Local skills directory. |

### Examples

```bash
ar skill read-file --name web-scraper --path scraper.py
ar skill read-file --name web-scraper --path assets/  # lists directory contents
```

---

## exec

Execute a shell command in a skill's directory (uses the skill dir as `cwd`).

```
ar skill exec --name <name> --command <cmd> [--dir <dir>] [--timeout <sec>]
```

### Options

| Flag | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `--name` | string | yes |  | Skill name. |
| `--command` | string | yes |  | Shell command to run. |
| `--dir` | path | no | `.skills` | Local skills directory. |
| `--timeout` | int | no | `300` | Timeout in seconds. |

### Examples

```bash
ar skill exec --name web-scraper --command "python scraper.py --url https://example.com"
ar skill exec --name my-skill --command "pytest tests/" --timeout 600
```
