"""Configuration file management for AgentRun CLI.

Handles reading and writing the CLI config file at ~/.agentrun/config.json.
Supports multiple named profiles with per-profile credentials and region settings.

Config file structure:
{
    "profiles": {
        "default": {
            "access_key_id": "...",
            "access_key_secret": "...",
            "account_id": "...",
            "region": "cn-hangzhou"
        }
    },
    "defaults": {
        "profile": "default",
        "output": "json"
    }
}
"""

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from agentrun.utils.config import Config

# Default config directory and file path
CONFIG_DIR = Path.home() / ".agentrun"
CONFIG_FILE = CONFIG_DIR / "config.json"


def _ensure_config_dir() -> None:
    """Create the config directory if it does not exist."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    """Load the config file. Returns an empty structure if the file is missing."""
    if not CONFIG_FILE.exists():
        return {"profiles": {}, "defaults": {"profile": "default", "output": "json"}}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config: dict) -> None:
    """Persist the config dict to disk."""
    _ensure_config_dir()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
        f.write("\n")


def get_profile(profile_name: Optional[str] = None) -> dict:
    """Return the settings dict for the given profile (or the default one)."""
    config = load_config()
    name = profile_name or config.get("defaults", {}).get("profile", "default")
    return config.get("profiles", {}).get(name, {})


def set_profile_value(key: str, value: str, profile_name: Optional[str] = None) -> None:
    """Set a single key inside a profile and save."""
    config = load_config()
    name = profile_name or config.get("defaults", {}).get("profile", "default")
    config.setdefault("profiles", {}).setdefault(name, {})[key] = value
    save_config(config)


def get_profile_value(key: str, profile_name: Optional[str] = None) -> Optional[str]:
    """Read a single key from the active profile."""
    return get_profile(profile_name).get(key)


def _env(*names: str) -> Optional[str]:
    """Return the first non-empty env var value, or None."""
    for name in names:
        val = os.getenv(name)
        if val:
            return val
    return None


def build_sdk_config(
    profile_name: Optional[str] = None,
    region: Optional[str] = None,
) -> "Config":
    """Build an ``agentrun.utils.config.Config`` from CLI context.

    Resolution order (highest priority first):
      1. Explicit ``--region`` CLI flag  (region_id only)
      2. Config-file profile values
      3. Environment variables  (AGENTRUN_*, ALIBABA_CLOUD_*, FC_*)

    Returns:
        A ready-to-use SDK ``Config`` instance.
    """
    from agentrun.utils.config import Config

    profile = get_profile(profile_name)

    ak = (profile.get("access_key_id")
          or _env("AGENTRUN_ACCESS_KEY_ID", "ALIBABA_CLOUD_ACCESS_KEY_ID")
          or None)
    sk = (profile.get("access_key_secret")
          or _env("AGENTRUN_ACCESS_KEY_SECRET", "ALIBABA_CLOUD_ACCESS_KEY_SECRET")
          or None)
    token = (profile.get("security_token")
             or _env("AGENTRUN_SECURITY_TOKEN", "ALIBABA_CLOUD_SECURITY_TOKEN")
             or None)
    account = (profile.get("account_id")
               or _env("AGENTRUN_ACCOUNT_ID", "FC_ACCOUNT_ID")
               or None)
    rid = (region
           or profile.get("region")
           or _env("AGENTRUN_REGION", "FC_REGION")
           or None)
    control_endpoint = (profile.get("control_endpoint")
                        or _env("AGENTRUN_CONTROL_ENDPOINT")
                        or None)
    data_endpoint = (profile.get("data_endpoint")
                     or _env("AGENTRUN_DATA_ENDPOINT")
                     or None)

    # Propagate resolved values to env vars so that SDK-internal Config()
    # instances (created without explicit config) also pick them up.
    # The SDK has a merge-order bug where its default Config (with empty-string
    # fields from missing env vars) can overwrite user-supplied values.
    _ENV_MAP = {
        "AGENTRUN_ACCESS_KEY_ID": ak,
        "AGENTRUN_ACCESS_KEY_SECRET": sk,
        "AGENTRUN_SECURITY_TOKEN": token,
        "AGENTRUN_ACCOUNT_ID": account,
        "AGENTRUN_REGION": rid,
        "AGENTRUN_CONTROL_ENDPOINT": control_endpoint,
        "AGENTRUN_DATA_ENDPOINT": data_endpoint,
    }
    for env_key, val in _ENV_MAP.items():
        if val and not os.getenv(env_key):
            os.environ[env_key] = val

    return Config(
        access_key_id=ak,
        access_key_secret=sk,
        security_token=token,
        account_id=account,
        region_id=rid,
        control_endpoint=control_endpoint,
        data_endpoint=data_endpoint,
    )
