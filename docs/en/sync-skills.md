**English** | [简体中文](../zh/sync-skills.md)

# ar sync-skills

Sync platform Skills to a local AI tool skill directory.

```
ar sync-skills --tool <tool> (--user | --project) [options]
```

## Options

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

## Behavior

- By default, all platform skills are selected (unless `--workspace` is provided).
- Before downloading/updating skills, the CLI asks for confirmation (skip with `-y`).
- Sync checks local metadata and only downloads skills that are missing or outdated.
- When `--delete-unmanaged` is enabled, local skill directories not in the selected
  managed scope can be removed after a separate confirmation.

## Examples

```bash
# Sync skills from workspace abc + def into user-level Claude Code skills
ar sync-skills --tool claude-code --user --workspace abc --workspace def

# Sync skills from workspace abc into project-level Codex skills
ar sync-skills --tool codex --project --workspace abc

# Sync all skills to project-level Cursor directory without prompts
ar sync-skills --tool cursor --project -y

# Sync to GitHub Copilot user-level directory and remove unmanaged local skills
ar sync-skills --tool github-copilot --user --delete-unmanaged

# Sync to Qoder project-level directory
ar sync-skills --tool qoder --project --workspace my-workspace
```
