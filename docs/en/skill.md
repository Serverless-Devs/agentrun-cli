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

Sync (bulk download to AI tool directories):

- [sync](#sync)

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

---

## sync

Sync platform Skills to a local AI tool skill directory (bulk download with
change-detection and optional cleanup).

```
ar skill sync --tool <tool> (--user | --project) [options]
```

### Options

| Flag | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `--tool` | choice | yes |  | Target AI tool. See choices below. |
| `--user` | flag | yes* |  | Sync to user-level directory. |
| `--project` | flag | yes* |  | Sync to project-level directory. |
| `--workspace` | multi | no | all | Workspace filter, repeatable. |
| `--delete-unmanaged` | flag | no | false | Delete local skills outside selected workspace scope (with confirmation). |
| `-y`, `--yes` | flag | no | false | Skip confirmation prompts. |

\* Exactly one of `--user` or `--project` is required.

### `--tool` choices

| Choice | User-level path | Project-level path |
|--------|----------------|--------------------|
| `claude-code` | `~/.claude/skills` | `.claude/skills` |
| `codex` | `~/.codex/skills` | `.codex/skills` |
| `github-copilot` | `~/.github/copilot/skills` | `.github/copilot/skills` |
| `cursor` | `~/.cursor/skills` | `.cursor/skills` |
| `qoder` | `~/.qoder/skills` | `.qoder/skills` |

### Behavior

- By default, all platform skills are selected (unless `--workspace` is provided).
- Before downloading/updating, the CLI asks for confirmation (skip with `-y`).
- Sync checks local metadata and only downloads skills that are missing or outdated.
- When `--delete-unmanaged` is enabled, local skill directories not in the selected
  managed scope can be removed after a separate confirmation.

### Examples

```bash
# Sync skills from workspace abc + def into user-level Claude Code directory
ar skill sync --tool claude-code --user --workspace abc --workspace def

# Sync skills from workspace abc into project-level Codex directory
ar skill sync --tool codex --project --workspace abc

# Sync all skills to project-level Cursor directory without prompts
ar skill sync --tool cursor --project -y

# Sync to GitHub Copilot user-level directory and remove unmanaged local skills
ar skill sync --tool github-copilot --user --delete-unmanaged

# Sync to Qoder project-level directory
ar skill sync --tool qoder --project --workspace my-workspace
```
