"""``ar sandbox {create,get,list,stop,delete,health}`` — instance lifecycle."""

import click

from agentrun_cli._utils.error import handle_errors
from agentrun_cli._utils.output import format_output

from ._helpers import _build_cfg, _load_json_option


def register_lifecycle_commands(sandbox_group: click.Group):
    """Register lifecycle commands directly on the sandbox group."""

    @sandbox_group.command("create")
    @click.option("--template", "template_name", required=True, help="Template name.")
    @click.option(
        "--type",
        "sandbox_type",
        required=True,
        help="Sandbox type: CodeInterpreter / Browser / AllInOne / CustomImage.",
    )
    @click.option("--id", "sandbox_id", default=None, help="Custom sandbox ID.")
    @click.option(
        "--idle-timeout", type=int, default=600, help="Idle timeout (seconds)."
    )
    @click.option("--nas-server-addr", default=None, help="NAS server address.")
    @click.option("--nas-mount-dir", default=None, help="NAS mount directory.")
    @click.option("--oss-bucket", default=None, help="OSS bucket name.")
    @click.option("--oss-mount-dir", default=None, help="OSS mount directory.")
    @click.option("--from-file", "from_file", default=None, help="Path to JSON file.")
    @click.pass_context
    @handle_errors
    def sandbox_create(
        ctx,
        template_name,
        sandbox_type,
        sandbox_id,
        idle_timeout,
        nas_server_addr,
        nas_mount_dir,
        oss_bucket,
        oss_mount_dir,
        from_file,
    ):
        """Create a sandbox instance."""
        from agentrun.sandbox import NASConfig, OSSMountConfig, Sandbox, TemplateType

        cfg = _build_cfg(ctx)

        if from_file:
            from agentrun.sandbox import SandboxInput

            payload = _load_json_option(from_file)
            inp = SandboxInput(**payload)
            sb = Sandbox.create(
                template_type=TemplateType(sandbox_type),
                template_name=inp.template_name,
                sandbox_idle_timeout_seconds=inp.sandbox_idle_timeout_seconds,
                sandbox_id=inp.sandbox_id,
                nas_config=inp.nas_config,
                oss_mount_config=inp.oss_mount_config,
                config=cfg,
            )
        else:
            nas_config = None
            if nas_server_addr:
                nas_config = NASConfig(
                    server_addr=nas_server_addr,
                    mount_dir=nas_mount_dir or "/mnt/nas",
                )

            oss_config = None
            if oss_bucket:
                oss_config = OSSMountConfig(
                    bucket_name=oss_bucket,
                    mount_dir=oss_mount_dir or "/mnt/oss",
                )

            sb = Sandbox.create(
                template_type=TemplateType(sandbox_type),
                template_name=template_name,
                sandbox_idle_timeout_seconds=idle_timeout,
                sandbox_id=sandbox_id,
                nas_config=nas_config,
                oss_mount_config=oss_config,
                config=cfg,
            )

        format_output(ctx, sb.model_dump(by_alias=False), quiet_field="sandbox_id")

    @sandbox_group.command("get")
    @click.argument("sandbox_id")
    @click.pass_context
    @handle_errors
    def sandbox_get(ctx, sandbox_id):
        """Get sandbox instance details."""
        from agentrun.sandbox import Sandbox

        cfg = _build_cfg(ctx)
        sb = Sandbox.connect(sandbox_id, config=cfg)
        format_output(ctx, sb.model_dump(by_alias=False), quiet_field="sandbox_id")

    @sandbox_group.command("list")
    @click.option("--max-results", type=int, default=10, help="Max results.")
    @click.option("--next-token", default=None, help="Pagination token.")
    @click.option("--status", default=None, help="Filter by status.")
    @click.option(
        "--template", "template_name", default=None, help="Filter by template name."
    )
    @click.option("--type", "sandbox_type", default=None, help="Filter by type.")
    @click.pass_context
    @handle_errors
    def sandbox_list(ctx, max_results, next_token, status, template_name, sandbox_type):
        """List sandbox instances."""
        from agentrun.sandbox import ListSandboxesInput, Sandbox, TemplateType

        cfg = _build_cfg(ctx)
        inp = ListSandboxesInput(
            max_results=max_results,
            next_token=next_token,
            status=status,
            template_name=template_name,
            template_type=TemplateType(sandbox_type) if sandbox_type else None,
        )
        result = Sandbox.list(inp, config=cfg)
        data = {
            "sandboxes": [s.model_dump(by_alias=False) for s in result.sandboxes],
        }
        if result.next_token:
            data["next_token"] = result.next_token
        format_output(ctx, data)

    @sandbox_group.command("stop")
    @click.argument("sandbox_id")
    @click.pass_context
    @handle_errors
    def sandbox_stop(ctx, sandbox_id):
        """Stop a sandbox instance."""
        from agentrun.sandbox import Sandbox

        cfg = _build_cfg(ctx)
        Sandbox.stop_by_id(sandbox_id, config=cfg)
        format_output(
            ctx,
            {"sandbox_id": sandbox_id, "status": "Stopped"},
            quiet_field="sandbox_id",
        )

    @sandbox_group.command("delete")
    @click.argument("sandbox_id")
    @click.pass_context
    @handle_errors
    def sandbox_delete(ctx, sandbox_id):
        """Delete a sandbox instance."""
        from agentrun.sandbox import Sandbox

        cfg = _build_cfg(ctx)
        Sandbox.delete_by_id(sandbox_id, config=cfg)
        format_output(
            ctx,
            {"sandbox_id": sandbox_id, "status": "Deleted"},
            quiet_field="sandbox_id",
        )

    @sandbox_group.command("health")
    @click.argument("sandbox_id")
    @click.pass_context
    @handle_errors
    def sandbox_health(ctx, sandbox_id):
        """Check sandbox health."""
        from agentrun.sandbox import Sandbox

        cfg = _build_cfg(ctx)
        sb = Sandbox.connect(sandbox_id, config=cfg)
        result = sb.check_health()
        format_output(ctx, result)
