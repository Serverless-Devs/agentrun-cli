"""``ar skill`` — manage skill packages.

Skills are downloadable tool packages containing a SKILL.md instruction file
and implementation code.  They are uploaded/downloaded as ZIP archives and
executed locally by the Agent.

Examples::

    ar skill create --name web-scraper --code-dir ./my-skill
    ar skill list
    ar skill get --name web-scraper
    ar skill download --name web-scraper
    ar skill scan
    ar skill load --name web-scraper
    ar skill read-file --name web-scraper --path scraper.py
    ar skill exec --name web-scraper --command "python scraper.py"
    ar skill delete --name web-scraper
"""

import base64
import io
import json
import os
import zipfile
from typing import Optional

import click

from agentrun_cli._utils.config import build_sdk_config
from agentrun_cli._utils.error import handle_errors
from agentrun_cli._utils.inner_client import get_agentrun_client
from agentrun_cli._utils.output import format_output


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ctx_cfg(ctx):
    return (ctx.obj or {}).get("profile"), (ctx.obj or {}).get("region")


def _serialize_tool(t) -> dict:
    return {
        k: v for k, v in {
            "tool_id": getattr(t, "tool_id", None),
            "tool_name": getattr(t, "tool_name", None) or getattr(t, "name", None),
            "tool_type": getattr(t, "tool_type", None),
            "status": getattr(t, "status", None),
            "description": getattr(t, "description", None),
            "created_at": getattr(t, "created_at", None) or getattr(t, "created_time", None),
            "updated_at": getattr(t, "updated_at", None) or getattr(t, "last_updated_at", None) or getattr(t, "last_modified_time", None),
        }.items() if v is not None
    }


def _zip_directory(dir_path: str) -> str:
    """ZIP a directory and return base64-encoded content."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(dir_path):
            for fname in files:
                full_path = os.path.join(root, fname)
                arcname = os.path.relpath(full_path, dir_path)
                zf.write(full_path, arcname)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _load_json_option(raw: Optional[str]) -> Optional[dict]:
    if raw is None:
        return None
    if not raw.strip().startswith("{"):
        with open(raw, "r", encoding="utf-8") as f:
            return json.load(f)
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Top-level group
# ---------------------------------------------------------------------------

@click.group("skill", help="Manage skill packages.")
def skill_group():
    pass


# ===========================================================================
# Platform-side (control plane)
# ===========================================================================

@skill_group.command("create")
@click.option("--name", "skill_name", required=True, help="Unique skill name.")
@click.option("--code-dir", required=True, help="Local skill directory (must contain SKILL.md).")
@click.option("--description", default=None, help="Skill description (auto-read from SKILL.md if omitted).")
@click.option("--credential", "credential_name", default=None, help="Credential name.")
@click.option("--from-file", "from_file", default=None, help="JSON file with full config.")
@click.pass_context
@handle_errors
def skill_create(ctx, skill_name, code_dir, description, credential_name, from_file):
    """Upload a local skill package to the platform."""
    from alibabacloud_agentrun20250910 import models

    profile, region = _ctx_cfg(ctx)
    client, headers, runtime = get_agentrun_client(profile, region)

    if from_file:
        payload = _load_json_option(from_file)
        payload.setdefault("tool_type", "SKILL")
        inp = models.CreateToolInputV2(**payload)
    else:
        # Validate code-dir
        skill_md = os.path.join(code_dir, "SKILL.md")
        if not os.path.isfile(skill_md):
            raise click.UsageError(f"SKILL.md not found in {code_dir}")

        # Auto-extract description from SKILL.md frontmatter if not provided
        if not description:
            description = _extract_description(skill_md)

        # ZIP and base64 encode
        zip_b64 = _zip_directory(code_dir)

        code_cfg = models.CodeConfiguration(zip_file=zip_b64)

        inp = models.CreateToolInputV2(
            tool_name=skill_name,
            tool_type="SKILL",
            description=description,
            code_configuration=code_cfg,
            credential_name=credential_name,
        )

    request = models.CreateToolRequest(body=inp)
    resp = client.create_tool_with_options(request, headers, runtime)
    data = resp.body.data
    result = _serialize_tool(data) if data else {"tool_name": skill_name, "status": "created"}
    format_output(ctx, result, quiet_field="tool_name")


def _extract_description(skill_md_path: str) -> Optional[str]:
    """Try to extract description from SKILL.md YAML frontmatter."""
    try:
        with open(skill_md_path, "r", encoding="utf-8") as f:
            content = f.read()
        if not content.startswith("---"):
            return None
        end = content.index("---", 3)
        frontmatter = content[3:end]
        for line in frontmatter.splitlines():
            line = line.strip()
            if line.startswith("description:"):
                val = line[len("description:"):].strip().strip("\"'")
                return val if val else None
    except Exception:
        pass
    return None


@skill_group.command("list")
@click.option("--page-number", type=int, default=None, help="Page number.")
@click.option("--page-size", type=int, default=None, help="Page size.")
@click.pass_context
@handle_errors
def skill_list(ctx, page_number, page_size):
    """List skills on the platform."""
    from alibabacloud_agentrun20250910 import models

    profile, region = _ctx_cfg(ctx)
    client, headers, runtime = get_agentrun_client(profile, region)

    request = models.ListToolsRequest(
        tool_type="SKILL",
        page_number=page_number,
        page_size=page_size,
    )
    resp = client.list_tools_with_options(request, headers, runtime)
    items = resp.body.data.items or []
    rows = [_serialize_tool(t) for t in items]
    format_output(ctx, rows)


@skill_group.command("get")
@click.option("--name", "skill_name", required=True, help="Skill name.")
@click.pass_context
@handle_errors
def skill_get(ctx, skill_name):
    """Get skill details from the platform."""
    from agentrun.tool import Tool

    profile, region = _ctx_cfg(ctx)
    cfg = build_sdk_config(profile_name=profile, region=region)
    tool = Tool.get_by_name(skill_name, config=cfg)
    format_output(ctx, _serialize_tool(tool), quiet_field="tool_name")


@skill_group.command("delete")
@click.option("--name", "skill_name", required=True, help="Skill name.")
@click.pass_context
@handle_errors
def skill_delete(ctx, skill_name):
    """Delete a skill from the platform."""
    profile, region = _ctx_cfg(ctx)
    client, headers, runtime = get_agentrun_client(profile, region)

    client.delete_tool_with_options(skill_name, headers, runtime)
    format_output(ctx, {"deleted": skill_name}, quiet_field="deleted")


@skill_group.command("download")
@click.option("--name", "skill_name", required=True, help="Skill name.")
@click.option("--dir", "target_dir", default=".skills", help="Target directory (default: .skills).")
@click.pass_context
@handle_errors
def skill_download(ctx, skill_name, target_dir):
    """Download a skill package to local directory."""
    from agentrun.tool import Tool

    profile, region = _ctx_cfg(ctx)
    cfg = build_sdk_config(profile_name=profile, region=region)
    tool = Tool.get_by_name(skill_name, config=cfg)
    path = tool.download_skill(target_dir=target_dir, config=cfg)
    format_output(ctx, {
        "skill_name": skill_name,
        "path": path,
        "status": "downloaded",
    }, quiet_field="path")


# ===========================================================================
# Local-side (data plane)
# ===========================================================================

@skill_group.command("scan")
@click.option("--dir", "skills_dir", default=".skills", help="Local skills directory (default: .skills).")
@click.pass_context
@handle_errors
def skill_scan(ctx, skills_dir):
    """Scan local skills directory."""
    from agentrun.integration.utils.skill_loader import SkillLoader

    loader = SkillLoader(skills_dir=skills_dir)
    skills = loader.scan_skills()
    rows = [{"name": s.name, "description": s.description, "version": s.version, "path": s.path}
            for s in skills]
    format_output(ctx, rows)


@skill_group.command("load")
@click.option("--name", "skill_name", required=True, help="Skill name.")
@click.option("--dir", "skills_dir", default=".skills", help="Local skills directory (default: .skills).")
@click.pass_context
@handle_errors
def skill_load(ctx, skill_name, skills_dir):
    """Load skill details (instruction + file list)."""
    from agentrun.integration.utils.skill_loader import SkillLoader

    loader = SkillLoader(skills_dir=skills_dir)
    detail = loader.load_skill(skill_name)
    if not detail:
        raise click.ClickException(f"Skill '{skill_name}' not found in {skills_dir}")
    result = {
        "name": detail.name,
        "description": detail.description,
        "version": detail.version,
        "path": detail.path,
        "instruction": detail.instruction,
        "files": detail.files,
    }
    format_output(ctx, result)


@skill_group.command("read-file")
@click.option("--name", "skill_name", required=True, help="Skill name.")
@click.option("--path", "relative_path", required=True, help="Relative path within skill directory.")
@click.option("--dir", "skills_dir", default=".skills", help="Local skills directory (default: .skills).")
@click.pass_context
@handle_errors
def skill_read_file(ctx, skill_name, relative_path, skills_dir):
    """Read a file from a skill's directory."""
    from agentrun.integration.utils.skill_loader import SkillLoader

    loader = SkillLoader(skills_dir=skills_dir)
    result_json = loader._read_skill_file_func(skill_name, relative_path)
    result = json.loads(result_json)
    if "error" in result:
        raise click.ClickException(result["error"])
    # Output raw content for piping
    content = result.get("content", result.get("entries", ""))
    if isinstance(content, list):
        click.echo(json.dumps(content, ensure_ascii=False, indent=2))
    else:
        click.echo(content)


@skill_group.command("exec")
@click.option("--name", "skill_name", required=True, help="Skill name.")
@click.option("--command", "cmd", required=True, help="Shell command to execute.")
@click.option("--dir", "skills_dir", default=".skills", help="Local skills directory (default: .skills).")
@click.option("--timeout", type=int, default=300, help="Timeout in seconds (default: 300).")
@click.pass_context
@handle_errors
def skill_exec(ctx, skill_name, cmd, skills_dir, timeout):
    """Execute a command in a skill's directory."""
    from agentrun.integration.utils.skill_loader import SkillLoader

    skill_dir = os.path.join(skills_dir, skill_name)
    if not os.path.isdir(skill_dir):
        raise click.ClickException(f"Skill directory not found: {skill_dir}")

    loader = SkillLoader(skills_dir=skills_dir)
    result_json = loader._execute_command_func(cmd, cwd=skill_dir, timeout=timeout)
    result = json.loads(result_json)
    format_output(ctx, result)
