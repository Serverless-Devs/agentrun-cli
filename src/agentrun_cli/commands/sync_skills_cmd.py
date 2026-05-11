"""``ar sync-skills`` — sync platform skills to local AI tool directories."""

import json
import os
import shutil

import click

from agentrun_cli._utils.config import build_sdk_config
from agentrun_cli._utils.error import handle_errors
from agentrun_cli._utils.inner_client import get_agentrun_client
from agentrun_cli._utils.output import format_output

_META_FILE_NAME = ".agentrun-sync-skills.json"

_TOOL_CHOICES = (
    "claude-code",
    "codex",
    "github-copilot",
    "cursor",
    "qoder",
)


def _ctx_cfg(ctx):
    return (ctx.obj or {}).get("profile"), (ctx.obj or {}).get("region")


def _extract_skill_name(skill) -> str:
    return getattr(skill, "tool_name", None) or getattr(skill, "name", None) or ""


def _extract_updated_at(skill):
    return (
        getattr(skill, "updated_at", None)
        or getattr(skill, "last_updated_at", None)
        or getattr(skill, "last_modified_time", None)
        or getattr(skill, "updated_time", None)
    )


def _extract_workspace_values(skill) -> set[str]:
    keys = ("name", "workspace_name", "workspace", "id", "workspace_id")
    values = set()
    raw = (
        getattr(skill, "workspace_names", None)
        or getattr(skill, "workspaces", None)
        or getattr(skill, "workspace_name", None)
        or getattr(skill, "workspace", None)
    )
    if raw is None:
        return values
    if isinstance(raw, str):
        return {raw}
    if isinstance(raw, (list, tuple, set)):
        for item in raw:
            if isinstance(item, str):
                values.add(item)
            elif isinstance(item, dict):
                for key in keys:
                    v = item.get(key)
                    if v:
                        values.add(str(v))
            else:
                for key in keys:
                    v = getattr(item, key, None)
                    if v:
                        values.add(str(v))
        return values
    if isinstance(raw, dict):
        for key in keys:
            v = raw.get(key)
            if v:
                values.add(str(v))
        return values
    for key in keys:
        v = getattr(raw, key, None)
        if v:
            values.add(str(v))
    return values


_TOOL_ROOTS: dict[str, tuple[str, str]] = {
    # (user_root, project_subdir_name)
    "claude-code": ("~/.claude", ".claude"),
    "codex": ("~/.codex", ".codex"),
    "github-copilot": ("~/.github/copilot", ".github/copilot"),
    "cursor": ("~/.cursor", ".cursor"),
    "qoder": ("~/.qoder", ".qoder"),
}


def _resolve_target_dir(ai_tool: str, scope: str) -> str:
    user_root, project_dir = _TOOL_ROOTS[ai_tool]
    root = (
        os.path.expanduser(user_root)
        if scope == "user"
        else os.path.abspath(project_dir)
    )
    return os.path.join(root, "skills")


def _meta_file_path(target_dir: str) -> str:
    return os.path.join(target_dir, _META_FILE_NAME)


def _load_sync_meta(target_dir: str) -> dict:
    path = _meta_file_path(target_dir)
    if not os.path.isfile(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def _save_sync_meta(target_dir: str, data: dict):
    path = _meta_file_path(target_dir)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)


def _list_local_skill_dirs(target_dir: str) -> set[str]:
    if not os.path.isdir(target_dir):
        return set()
    result = set()
    for entry in os.listdir(target_dir):
        if entry.startswith("."):
            continue
        full = os.path.join(target_dir, entry)
        if os.path.isdir(full):
            result.add(entry)
    return result


def _list_platform_skills(profile, region):
    from alibabacloud_agentrun20250910 import models

    client, headers, runtime = get_agentrun_client(profile, region)

    page_number = 1
    page_size = 100
    all_items = []
    while True:
        req = models.ListToolsRequest(
            tool_type="SKILL",
            page_number=page_number,
            page_size=page_size,
        )
        resp = client.list_tools_with_options(req, headers, runtime)
        data = getattr(resp.body, "data", None)
        page_items = (getattr(data, "items", None) or []) if data else []
        if not page_items:
            break
        all_items.extend(page_items)
        if len(page_items) < page_size:
            break
        page_number += 1
    return all_items


@click.command(
    "sync-skills",
    help="Sync platform skills to a local AI tool skill directory.",
)
@click.option(
    "--tool",
    "ai_tool",
    type=click.Choice(_TOOL_CHOICES),
    required=True,
    help=(
        "Target AI tool: claude-code, codex, github-copilot, cursor, qoder."
    ),
)
@click.option(
    "--user",
    "user_scope",
    is_flag=True,
    default=False,
    help="Use user-level skill directory.",
)
@click.option(
    "--project",
    "project_scope",
    is_flag=True,
    default=False,
    help="Use project-level skill directory.",
)
@click.option(
    "--workspace",
    "workspaces",
    multiple=True,
    help="Workspace filter (repeatable). Defaults to all workspaces.",
)
@click.option(
    "--delete-unmanaged",
    is_flag=True,
    default=False,
    help=(
        "Delete local skills not in selected workspace scope "
        "(with confirmation)."
    ),
)
@click.option(
    "-y",
    "--yes",
    "auto_confirm",
    is_flag=True,
    default=False,
    help="Skip confirmation prompts.",
)
@click.pass_context
@handle_errors
def sync_skills(
    ctx,
    ai_tool,
    user_scope,
    project_scope,
    workspaces,
    delete_unmanaged,
    auto_confirm,
):
    """Sync platform skills to local AI tool skill directories."""
    if user_scope == project_scope:
        raise click.UsageError("You must specify exactly one of --user or --project.")

    scope = "user" if user_scope else "project"
    target_dir = _resolve_target_dir(ai_tool, scope)
    os.makedirs(target_dir, exist_ok=True)

    profile, region = _ctx_cfg(ctx)
    all_skills = _list_platform_skills(profile, region)
    requested_workspaces = set(workspaces or [])

    selected_skills = []
    for skill in all_skills:
        if requested_workspaces:
            if not (_extract_workspace_values(skill) & requested_workspaces):
                continue
        name = _extract_skill_name(skill)
        if name:
            selected_skills.append(skill)

    selected_names = {_extract_skill_name(s) for s in selected_skills}
    sync_meta = _load_sync_meta(target_dir)

    to_sync = []
    skipped = []
    for skill in selected_skills:
        name = _extract_skill_name(skill)
        remote_updated_at = _extract_updated_at(skill)
        local_exists = os.path.isdir(os.path.join(target_dir, name))
        meta_updated_at = (sync_meta.get(name) or {}).get("updated_at")
        if local_exists and meta_updated_at == remote_updated_at:
            skipped.append(name)
            continue
        to_sync.append((name, remote_updated_at, local_exists))

    if to_sync and not auto_confirm:
        click.confirm(
            f"Will sync {len(to_sync)} skill(s) to {target_dir}. Continue?",
            default=True,
            abort=True,
        )

    downloaded = []
    updated = []
    cfg = build_sdk_config(profile_name=profile, region=region)
    from agentrun.tool import Tool

    for name, remote_updated_at, local_exists in to_sync:
        tool = Tool.get_by_name(name, config=cfg)
        path = tool.download_skill(target_dir=target_dir, config=cfg)
        sync_meta[name] = {"updated_at": remote_updated_at}
        record = {"skill_name": name, "path": path}
        if local_exists:
            updated.append(record)
        else:
            downloaded.append(record)

    removed = []
    if delete_unmanaged:
        local_skills = _list_local_skill_dirs(target_dir)
        unmanaged = sorted(local_skills - selected_names)
        if unmanaged:
            if not auto_confirm:
                click.confirm(
                    (
                        "Will delete "
                        f"{len(unmanaged)} unmanaged local skill(s) "
                        f"from {target_dir}. Continue?"
                    ),
                    default=False,
                    abort=True,
                )
            for name in unmanaged:
                full = os.path.join(target_dir, name)
                shutil.rmtree(full)
                sync_meta.pop(name, None)
                removed.append(name)

    _save_sync_meta(target_dir, sync_meta)

    format_output(
        ctx,
        {
            "ai_tool": ai_tool,
            "scope": scope,
            "target_dir": target_dir,
            "workspaces": sorted(requested_workspaces),
            "platform_skill_total": len(all_skills),
            "managed_skill_total": len(selected_skills),
            "downloaded": downloaded,
            "updated": updated,
            "skipped": sorted(skipped),
            "removed": removed,
        },
    )
