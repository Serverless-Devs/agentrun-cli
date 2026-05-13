"""Unit tests for agentrun_cli._utils.config — build_sdk_config."""

import os
from unittest.mock import MagicMock, patch

from agentrun_cli._utils.config import build_sdk_config

# All env vars that build_sdk_config may read — must be cleared in tests
# to avoid cross-contamination from the real user profile.
_ALL_ENV_KEYS = [
    "AGENTRUN_ACCESS_KEY_ID",
    "ALIBABA_CLOUD_ACCESS_KEY_ID",
    "AGENTRUN_ACCESS_KEY_SECRET",
    "ALIBABA_CLOUD_ACCESS_KEY_SECRET",
    "AGENTRUN_SECURITY_TOKEN",
    "ALIBABA_CLOUD_SECURITY_TOKEN",
    "AGENTRUN_ACCOUNT_ID",
    "FC_ACCOUNT_ID",
    "AGENTRUN_REGION",
    "FC_REGION",
    "AGENTRUN_CONTROL_ENDPOINT",
    "AGENTRUN_DATA_ENDPOINT",
]


def _clean_env():
    """Return env dict with all AGENTRUN/ALIBABA_CLOUD/FC vars removed."""
    return {k: v for k, v in os.environ.items() if k not in _ALL_ENV_KEYS}


def _sdk_modules(mock_config):
    return {
        "agentrun": MagicMock(),
        "agentrun.utils": MagicMock(),
        "agentrun.utils.config": MagicMock(Config=mock_config),
    }


class TestBuildSdkConfig:
    def test_from_profile(self, tmp_path):
        """Profile values are used when no env vars are set."""
        config_file = tmp_path / "config.json"

        with (
            patch("agentrun_cli._utils.config.CONFIG_FILE", config_file),
            patch("agentrun_cli._utils.config.CONFIG_DIR", tmp_path),
            patch.dict("os.environ", _clean_env(), clear=True),
        ):
            from agentrun_cli._utils.config import set_profile_value

            set_profile_value("access_key_id", "LTAI5tABC")
            set_profile_value("access_key_secret", "secret123")
            set_profile_value("account_id", "1234567890")
            set_profile_value("region", "cn-shanghai")

            mock_cfg = MagicMock()
            with patch.dict("sys.modules", _sdk_modules(mock_cfg)):
                build_sdk_config()
                kw = mock_cfg.call_args.kwargs
                assert kw["access_key_id"] == "LTAI5tABC"
                assert kw["access_key_secret"] == "secret123"
                assert kw["account_id"] == "1234567890"
                assert kw["region_id"] == "cn-shanghai"

    def test_profile_beats_env_vars(self, tmp_path):
        """Profile has higher priority than environment variables."""
        config_file = tmp_path / "config.json"

        with (
            patch("agentrun_cli._utils.config.CONFIG_FILE", config_file),
            patch("agentrun_cli._utils.config.CONFIG_DIR", tmp_path),
            patch.dict("os.environ", _clean_env(), clear=True),
        ):
            from agentrun_cli._utils.config import set_profile_value

            set_profile_value("access_key_id", "PROFILE_AK")
            set_profile_value("access_key_secret", "PROFILE_SK")
            set_profile_value("account_id", "PROFILE_ACCT")
            set_profile_value("region", "cn-shanghai")

            # Set env vars that should be overridden by profile
            os.environ["AGENTRUN_ACCESS_KEY_ID"] = "ENV_AK"
            os.environ["AGENTRUN_ACCESS_KEY_SECRET"] = "ENV_SK"
            os.environ["AGENTRUN_ACCOUNT_ID"] = "ENV_ACCT"
            os.environ["AGENTRUN_REGION"] = "cn-beijing"

            mock_cfg = MagicMock()
            with patch.dict("sys.modules", _sdk_modules(mock_cfg)):
                build_sdk_config()
                kw = mock_cfg.call_args.kwargs
                assert kw["access_key_id"] == "PROFILE_AK"
                assert kw["access_key_secret"] == "PROFILE_SK"
                assert kw["account_id"] == "PROFILE_ACCT"
                assert kw["region_id"] == "cn-shanghai"

    def test_env_vars_fallback_when_no_profile(self, tmp_path):
        """Env vars are used when profile has no values."""
        config_file = tmp_path / "config.json"

        with (
            patch("agentrun_cli._utils.config.CONFIG_FILE", config_file),
            patch("agentrun_cli._utils.config.CONFIG_DIR", tmp_path),
            patch.dict("os.environ", _clean_env(), clear=True),
        ):
            os.environ["AGENTRUN_ACCESS_KEY_ID"] = "ENV_AK"
            os.environ["AGENTRUN_ACCESS_KEY_SECRET"] = "ENV_SK"
            os.environ["AGENTRUN_ACCOUNT_ID"] = "ENV_ACCT"
            os.environ["AGENTRUN_REGION"] = "cn-beijing"

            mock_cfg = MagicMock()
            with patch.dict("sys.modules", _sdk_modules(mock_cfg)):
                build_sdk_config()
                kw = mock_cfg.call_args.kwargs
                assert kw["access_key_id"] == "ENV_AK"
                assert kw["access_key_secret"] == "ENV_SK"
                assert kw["account_id"] == "ENV_ACCT"
                assert kw["region_id"] == "cn-beijing"

    def test_alibaba_cloud_env_fallback(self, tmp_path):
        """ALIBABA_CLOUD_* and FC_* env vars work as fallback."""
        config_file = tmp_path / "config.json"

        with (
            patch("agentrun_cli._utils.config.CONFIG_FILE", config_file),
            patch("agentrun_cli._utils.config.CONFIG_DIR", tmp_path),
            patch.dict("os.environ", _clean_env(), clear=True),
        ):
            os.environ["ALIBABA_CLOUD_ACCESS_KEY_ID"] = "ALI_AK"
            os.environ["ALIBABA_CLOUD_ACCESS_KEY_SECRET"] = "ALI_SK"
            os.environ["ALIBABA_CLOUD_SECURITY_TOKEN"] = "ALI_TOKEN"
            os.environ["FC_ACCOUNT_ID"] = "FC_ACCT"
            os.environ["FC_REGION"] = "cn-shenzhen"

            mock_cfg = MagicMock()
            with patch.dict("sys.modules", _sdk_modules(mock_cfg)):
                build_sdk_config()
                kw = mock_cfg.call_args.kwargs
                assert kw["access_key_id"] == "ALI_AK"
                assert kw["access_key_secret"] == "ALI_SK"
                assert kw["security_token"] == "ALI_TOKEN"
                assert kw["account_id"] == "FC_ACCT"
                assert kw["region_id"] == "cn-shenzhen"

    def test_agentrun_env_beats_alibaba_env(self, tmp_path):
        """AGENTRUN_* env vars take precedence over ALIBABA_CLOUD_*/FC_*."""
        config_file = tmp_path / "config.json"

        with (
            patch("agentrun_cli._utils.config.CONFIG_FILE", config_file),
            patch("agentrun_cli._utils.config.CONFIG_DIR", tmp_path),
            patch.dict("os.environ", _clean_env(), clear=True),
        ):
            os.environ["AGENTRUN_ACCESS_KEY_ID"] = "AR_AK"
            os.environ["ALIBABA_CLOUD_ACCESS_KEY_ID"] = "ALI_AK"
            os.environ["AGENTRUN_ACCOUNT_ID"] = "AR_ACCT"
            os.environ["FC_ACCOUNT_ID"] = "FC_ACCT"

            mock_cfg = MagicMock()
            with patch.dict("sys.modules", _sdk_modules(mock_cfg)):
                build_sdk_config()
                kw = mock_cfg.call_args.kwargs
                assert kw["access_key_id"] == "AR_AK"
                assert kw["account_id"] == "AR_ACCT"

    def test_region_param_highest_priority(self, tmp_path):
        """--region flag beats both profile and env vars."""
        config_file = tmp_path / "config.json"

        with (
            patch("agentrun_cli._utils.config.CONFIG_FILE", config_file),
            patch("agentrun_cli._utils.config.CONFIG_DIR", tmp_path),
            patch.dict("os.environ", _clean_env(), clear=True),
        ):
            from agentrun_cli._utils.config import set_profile_value

            set_profile_value("region", "cn-shanghai")
            os.environ["AGENTRUN_REGION"] = "cn-beijing"

            mock_cfg = MagicMock()
            with patch.dict("sys.modules", _sdk_modules(mock_cfg)):
                build_sdk_config(region="cn-shenzhen")
                kw = mock_cfg.call_args.kwargs
                assert kw["region_id"] == "cn-shenzhen"

    def test_none_when_nothing_configured(self, tmp_path):
        """All values are None when nothing is configured."""
        config_file = tmp_path / "config.json"

        with (
            patch("agentrun_cli._utils.config.CONFIG_FILE", config_file),
            patch("agentrun_cli._utils.config.CONFIG_DIR", tmp_path),
            patch.dict("os.environ", _clean_env(), clear=True),
        ):
            mock_cfg = MagicMock()
            with patch.dict("sys.modules", _sdk_modules(mock_cfg)):
                build_sdk_config()
                kw = mock_cfg.call_args.kwargs
                assert kw["access_key_id"] is None
                assert kw["access_key_secret"] is None
                assert kw["security_token"] is None
                assert kw["account_id"] is None
                assert kw["region_id"] is None

    def test_env_propagation(self, tmp_path):
        """Profile values are propagated to env vars for SDK compatibility."""
        config_file = tmp_path / "config.json"

        with (
            patch("agentrun_cli._utils.config.CONFIG_FILE", config_file),
            patch("agentrun_cli._utils.config.CONFIG_DIR", tmp_path),
            patch.dict("os.environ", _clean_env(), clear=True),
        ):
            from agentrun_cli._utils.config import set_profile_value

            set_profile_value("access_key_id", "PROP_AK")
            set_profile_value("account_id", "PROP_ACCT")

            mock_cfg = MagicMock()
            with patch.dict("sys.modules", _sdk_modules(mock_cfg)):
                build_sdk_config()
                assert os.environ["AGENTRUN_ACCESS_KEY_ID"] == "PROP_AK"
                assert os.environ["AGENTRUN_ACCOUNT_ID"] == "PROP_ACCT"

    def test_endpoints_from_profile(self, tmp_path):
        """Custom endpoints stored in profile flow into the SDK Config."""
        config_file = tmp_path / "config.json"
        ctrl = "agentrun-pre.cn-hangzhou.aliyuncs.com"
        data = "https://acct.funagent-data-pre.cn-hangzhou.aliyuncs.com"

        with (
            patch("agentrun_cli._utils.config.CONFIG_FILE", config_file),
            patch("agentrun_cli._utils.config.CONFIG_DIR", tmp_path),
            patch.dict("os.environ", _clean_env(), clear=True),
        ):
            from agentrun_cli._utils.config import set_profile_value

            set_profile_value("control_endpoint", ctrl)
            set_profile_value("data_endpoint", data)

            mock_cfg = MagicMock()
            with patch.dict("sys.modules", _sdk_modules(mock_cfg)):
                build_sdk_config()
                kw = mock_cfg.call_args.kwargs
                assert kw["control_endpoint"] == ctrl
                assert kw["data_endpoint"] == data
                # And propagated to env so SDK-internal Config() picks them up too.
                assert os.environ["AGENTRUN_CONTROL_ENDPOINT"] == ctrl
                assert os.environ["AGENTRUN_DATA_ENDPOINT"] == data

    def test_endpoints_env_fallback(self, tmp_path):
        """Endpoint env vars are used when profile has none."""
        config_file = tmp_path / "config.json"

        with (
            patch("agentrun_cli._utils.config.CONFIG_FILE", config_file),
            patch("agentrun_cli._utils.config.CONFIG_DIR", tmp_path),
            patch.dict("os.environ", _clean_env(), clear=True),
        ):
            os.environ["AGENTRUN_CONTROL_ENDPOINT"] = "env-ctrl.example.com"
            os.environ["AGENTRUN_DATA_ENDPOINT"] = "env-data.example.com"

            mock_cfg = MagicMock()
            with patch.dict("sys.modules", _sdk_modules(mock_cfg)):
                build_sdk_config()
                kw = mock_cfg.call_args.kwargs
                assert kw["control_endpoint"] == "env-ctrl.example.com"
                assert kw["data_endpoint"] == "env-data.example.com"

    def test_endpoints_profile_beats_env(self, tmp_path):
        """Profile endpoints beat env vars, mirroring AK/region resolution."""
        config_file = tmp_path / "config.json"

        with (
            patch("agentrun_cli._utils.config.CONFIG_FILE", config_file),
            patch("agentrun_cli._utils.config.CONFIG_DIR", tmp_path),
            patch.dict("os.environ", _clean_env(), clear=True),
        ):
            from agentrun_cli._utils.config import set_profile_value

            set_profile_value("control_endpoint", "profile-ctrl.example.com")
            set_profile_value("data_endpoint", "profile-data.example.com")
            os.environ["AGENTRUN_CONTROL_ENDPOINT"] = "env-ctrl.example.com"
            os.environ["AGENTRUN_DATA_ENDPOINT"] = "env-data.example.com"

            mock_cfg = MagicMock()
            with patch.dict("sys.modules", _sdk_modules(mock_cfg)):
                build_sdk_config()
                kw = mock_cfg.call_args.kwargs
                assert kw["control_endpoint"] == "profile-ctrl.example.com"
                assert kw["data_endpoint"] == "profile-data.example.com"
