[English](../en/sync-skills.md) | **简体中文**

# ar sync-skills

把平台上的 Skill 同步到本地 AI 工具技能目录。

```
ar sync-skills --tool <tool> (--user | --project) [options]
```

## 参数

| Flag | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--tool` | choice | 是 |  | 目标 AI 工具，见下表。 |
| `--user` | flag | 是* |  | 同步到用户级目录。 |
| `--project` | flag | 是* |  | 同步到项目级目录。 |
| `--workspace` | multi | 否 | 全部 | 工作空间过滤，可重复。 |
| `--delete-unmanaged` | flag | 否 | false | 删除不在所选管控范围内的本地技能目录（需确认）。 |
| `-y`、`--yes` | flag | 否 | false | 跳过确认提示。 |

\* `--user` 与 `--project` 二选一。

### `--tool` 可选值

| 选项 | 用户级路径 | 项目级路径 |
|------|-----------|-----------|
| `claude-code` | `~/.claude/skills` | `.claude/skills` |
| `codex` | `~/.codex/skills` | `.codex/skills` |
| `github-copilot` | `~/.github/copilot/skills` | `.github/copilot/skills` |
| `cursor` | `~/.cursor/skills` | `.cursor/skills` |
| `qoder` | `~/.qoder/skills` | `.qoder/skills` |

## 行为说明

- 默认同步全部平台 Skill（除非传入 `--workspace`）。
- 在下载/更新 Skill 前会先进行用户确认（传 `-y` 可跳过）。
- 同步会检查本地元数据，仅下载缺失或有更新的 Skill。
- 开启 `--delete-unmanaged` 时，会在再次确认后删除不在当前管控范围内的本地 Skill 目录。

## 示例

```bash
# 将 workspace abc + def 的 skills 同步到用户级 Claude Code 目录
ar sync-skills --tool claude-code --user --workspace abc --workspace def

# 将 workspace abc 的 skills 同步到项目级 Codex 目录
ar sync-skills --tool codex --project --workspace abc

# 跳过确认，将全部 skills 同步到项目级 Cursor 目录
ar sync-skills --tool cursor --project -y

# 同步到 GitHub Copilot 用户级目录，并删除不在管控范围的本地 skills
ar sync-skills --tool github-copilot --user --delete-unmanaged

# 同步到 Qoder 项目级目录
ar sync-skills --tool qoder --project --workspace my-workspace
```
