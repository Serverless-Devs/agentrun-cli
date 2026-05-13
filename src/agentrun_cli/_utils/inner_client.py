"""Low-level AgentRun SDK client construction.

Provides access to the ``alibabacloud_agentrun20250910.Client`` for control-plane
operations (create / list / update / delete) that are not yet exposed by the
high-level SDK resource classes.
"""

from agentrun_cli._utils.config import build_sdk_config


def get_agentrun_client(
    profile_name: str | None = None,
    region: str | None = None,
):
    """Build a low-level AgentRun API client from CLI context.

    Returns:
        A tuple of ``(client, headers, runtime)`` ready for ``*_with_options`` calls.
    """
    from alibabacloud_agentrun20250910.client import Client as AgentRunClient
    from alibabacloud_tea_openapi import utils_models as open_api_util_models
    from darabonba.runtime import RuntimeOptions

    cfg = build_sdk_config(profile_name=profile_name, region=region)

    endpoint = cfg.get_control_endpoint()
    if endpoint.startswith("http://") or endpoint.startswith("https://"):
        endpoint = endpoint.split("://", 1)[1]

    client = AgentRunClient(
        open_api_util_models.Config(
            access_key_id=cfg.get_access_key_id(),
            access_key_secret=cfg.get_access_key_secret(),
            security_token=cfg.get_security_token(),
            region_id=cfg.get_region_id(),
            endpoint=endpoint,
            connect_timeout=30000,
            read_timeout=30000,
        )
    )
    return client, {}, RuntimeOptions()
