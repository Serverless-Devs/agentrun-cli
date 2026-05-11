**English** | [简体中文](../zh/sync-skills.md)

# ar sync-skills

Sync platform Skills to local AI tool skill directories (Claude Code or Codex).

```
ar sync-skills [tool] [scope] [options]
```

## Options

| Flag | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `--claude-code` | flag | yes* |  | Sync to Claude Code skill directory. |
| `--codex` | flag | yes* |  | Sync to Codex skill directory. |
| `--user` | flag | yes** |  | Sync to user-level directory. |
| `--project` | flag | yes** |  | Sync to project-level directory. |
| `--workspace` | multi | no | all | Workspace filter, repeatable. |
| `--delete-unmanaged` | flag | no | false | Delete local skills outside selected workspace scope (with confirmation). |
| `-y`, `--yes` | flag | no | false | Skip confirmation prompts. |

\* Exactly one of `--claude-code` or `--codex` is required.  
\** Exactly one of `--user` or `--project` is required.

## Behavior

- By default, all platform skills are selected (unless `--workspace` is provided).
- Before downloading/updating skills, the CLI asks for confirmation.
- Sync checks local metadata and only downloads skills that are missing or outdated.
- When `--delete-unmanaged` is enabled, local skill directories not in the selected
  managed scope can be removed after confirmation.

## Examples

```bash
# Sync skills from workspace abc + def into user-level Claude Code skills
ar sync-skills --claude-code --user --workspace abc --workspace def

# Sync skills from workspace abc into project-level Codex skills
ar sync-skills --codex --project --workspace abc

# Sync all skills and also remove unmanaged local skills
ar sync-skills --claude-code --project --delete-unmanaged
```
