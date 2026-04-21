"""``ar config`` — manage CLI configuration profiles.

Stores credentials and preferences in ``~/.agentrun/config.json``.
Each profile holds an independent set of access keys, account ID, and region.

Examples::

    # Set credentials for the default profile
    ar config set access_key_id LTAI5tXXX
    ar config set access_key_secret yyy
    ar config set account_id 1234567890
    ar config set region cn-hangzhou

    # Read a single value
    ar config get region

    # List all values in the active profile
    ar config list

    # Use a named profile
    ar config set access_key_id LTAI5tZZZ --profile staging
    ar config list --profile staging
"""

import click

from agentrun_cli._utils.config import (
    get_profile,
    get_profile_value,
    load_config,
    set_profile_value,
)
from agentrun_cli._utils.output import echo_json


@click.group("config", help="Manage CLI configuration profiles.")
def config_group():
    pass


@config_group.command("set")
@click.argument("key")
@click.argument("value")
@click.option(
    "--profile",
    default=None,
    help="Profile name to write to (default: the active profile).",
)
def config_set(key: str, value: str, profile: str | None):
    """Set a configuration KEY to VALUE in the active profile.

    Common keys: access_key_id, access_key_secret, account_id, region,
    security_token, control_endpoint, data_endpoint.
    """
    set_profile_value(key, value, profile_name=profile)
    display_profile = profile or load_config().get("defaults", {}).get("profile", "default")
    click.echo(f"Set {key} in profile '{display_profile}'.")


@config_group.command("get")
@click.argument("key")
@click.option(
    "--profile",
    default=None,
    help="Profile name to read from (default: the active profile).",
)
def config_get(key: str, profile: str | None):
    """Print the value of a configuration KEY."""
    val = get_profile_value(key, profile_name=profile)
    if val is None:
        raise click.ClickException(f"Key '{key}' is not set.")
    click.echo(val)


@config_group.command("list")
@click.option(
    "--profile",
    default=None,
    help="Profile name to display (default: the active profile).",
)
@click.pass_context
def config_list(ctx: click.Context, profile: str | None):
    """Show all configuration values in the active profile."""
    data = get_profile(profile)
    if not data:
        name = profile or load_config().get("defaults", {}).get("profile", "default")
        click.echo(f"Profile '{name}' is empty. Run 'ar config set <key> <value>' to configure.")
        return

    # Mask secrets in display
    masked = dict(data)
    for secret_key in ("access_key_secret", "security_token"):
        if secret_key in masked and masked[secret_key]:
            val = masked[secret_key]
            masked[secret_key] = val[:4] + "***" + val[-4:] if len(val) > 8 else "***"

    echo_json(masked)
