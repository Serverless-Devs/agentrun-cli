[English](../en/sync-skills.md) | **简体中文**

# ar sync-skills

把平台上的 Skill 同步到本地 AI 工具技能目录（Claude Code 或 Codex）。

```
ar sync-skills [tool] [scope] [options]
```

## 参数

| Flag | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--claude-code` | flag | 是* |  | 同步到 Claude Code 技能目录。 |
| `--codex` | flag | 是* |  | 同步到 Codex 技能目录。 |
| `--user` | flag | 是** |  | 同步到用户级目录。 |
| `--project` | flag | 是** |  | 同步到项目级目录。 |
| `--workspace` | multi | 否 | 全部 | 工作空间过滤，可重复。 |
| `--delete-unmanaged` | flag | 否 | false | 删除不在所选管控范围内的本地技能目录（需确认）。 |
| `-y`、`--yes` | flag | 否 | false | 跳过确认提示。 |

\* `--claude-code` 与 `--codex` 二选一。  
\** `--user` 与 `--project` 二选一。

## 行为说明

- 默认同步全部平台 Skill（除非传入 `--workspace`）。
- 在下载/更新 Skill 前会先进行用户确认。
- 同步会检查本地元数据，仅下载缺失或有更新的 Skill。
- 开启 `--delete-unmanaged` 时，会在确认后删除不在当前管控范围内的本地 Skill 目录。

## 示例

```bash
# 将 workspace abc + def 的 skills 同步到用户级 Claude Code 目录
ar sync-skills --claude-code --user --workspace abc --workspace def

# 将 workspace abc 的 skills 同步到项目级 Codex 目录
ar sync-skills --codex --project --workspace abc

# 同步全部 skills，并删除不在管控范围内的本地 skills
ar sync-skills --claude-code --project --delete-unmanaged
```
