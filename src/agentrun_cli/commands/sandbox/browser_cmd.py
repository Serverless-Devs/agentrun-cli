"""``ar sandbox browser`` — browser automation commands."""

import click

from agentrun_cli._utils.error import handle_errors
from agentrun_cli._utils.output import format_output

from ._helpers import _build_cfg


@click.group("browser", help="Browser automation commands.")
def browser_group():
    pass


@browser_group.command("cdp-url")
@click.argument("sandbox_id")
@click.option("--with-headers", is_flag=True, help="Include authentication headers.")
@click.pass_context
@handle_errors
def browser_cdp_url(ctx, sandbox_id, with_headers):
    """Get CDP WebSocket URL for browser automation."""
    from agentrun.sandbox import Sandbox

    cfg = _build_cfg(ctx)
    sb = Sandbox.connect(sandbox_id, config=cfg)
    result = sb.get_cdp_url(with_headers=with_headers)

    if with_headers:
        url, headers = result
        format_output(ctx, {"cdp_url": url, "headers": headers})
    else:
        format_output(ctx, {"cdp_url": result}, quiet_field="cdp_url")


@browser_group.command("vnc-url")
@click.argument("sandbox_id")
@click.option("--with-headers", is_flag=True, help="Include authentication headers.")
@click.pass_context
@handle_errors
def browser_vnc_url(ctx, sandbox_id, with_headers):
    """Get VNC WebSocket URL for live view."""
    from agentrun.sandbox import Sandbox

    cfg = _build_cfg(ctx)
    sb = Sandbox.connect(sandbox_id, config=cfg)
    result = sb.get_vnc_url(with_headers=with_headers)

    if with_headers:
        url, headers = result
        format_output(ctx, {"vnc_url": url, "headers": headers})
    else:
        format_output(ctx, {"vnc_url": result}, quiet_field="vnc_url")


@browser_group.command("screenshot")
@click.argument("sandbox_id")
@click.option("--save-path", default="./screenshot.png", help="Local save path.")
@click.option("--full-page", is_flag=True, help="Capture full page.")
@click.option(
    "--format",
    "img_format",
    default="png",
    type=click.Choice(["png", "jpeg"]),
    help="Image format.",
)
@click.option("--quality", type=int, default=80, help="JPEG quality (1-100).")
@click.pass_context
@handle_errors
def browser_screenshot(ctx, sandbox_id, save_path, full_page, img_format, quality):
    """Take a screenshot of the browser page."""
    from agentrun.sandbox import Sandbox

    cfg = _build_cfg(ctx)
    sb = Sandbox.connect(sandbox_id, config=cfg)
    pw = sb.sync_playwright()

    screenshot_kwargs = {
        "path": save_path,
        "full_page": full_page,
        "type": img_format,
    }
    if img_format == "jpeg":
        screenshot_kwargs["quality"] = quality

    page = pw.pages[0] if pw.pages else pw.new_page()
    page.screenshot(**screenshot_kwargs)
    pw.close()

    import os

    format_output(
        ctx,
        {
            "saved_path": save_path,
            "size": os.path.getsize(save_path),
            "format": img_format,
        },
        quiet_field="saved_path",
    )


@browser_group.command("navigate")
@click.argument("sandbox_id")
@click.argument("url")
@click.option(
    "--wait-until",
    default="load",
    type=click.Choice(["load", "domcontentloaded", "networkidle"]),
    help="Wait condition.",
)
@click.option("--timeout", type=int, default=30, help="Navigation timeout (seconds).")
@click.pass_context
@handle_errors
def browser_navigate(ctx, sandbox_id, url, wait_until, timeout):
    """Navigate the browser to a URL."""
    from agentrun.sandbox import Sandbox

    cfg = _build_cfg(ctx)
    sb = Sandbox.connect(sandbox_id, config=cfg)
    pw = sb.sync_playwright()

    page = pw.pages[0] if pw.pages else pw.new_page()
    response = page.goto(url, wait_until=wait_until, timeout=timeout * 1000)
    title = page.title()
    pw.close()

    format_output(
        ctx,
        {
            "url": url,
            "title": title,
            "status": response.status if response else None,
        },
        quiet_field="url",
    )
