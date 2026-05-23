"""Tests for Agent Runtime cloud build helpers."""

from __future__ import annotations

import os
import stat
import sys
from types import SimpleNamespace

import pytest

from agentrun_cli._utils import cloud_build as cloud_build_mod
from agentrun_cli._utils.agentruntime_yaml import (
    ParsedAgentRuntime,
    ParsedCloudBuild,
    ParsedCloudBuildRegistry,
    ParsedContainer,
)
from agentrun_cli._utils.cloud_build import (
    BUILDER_RELEASE_TAG,
    CloudBuildError,
    build_builder_args,
    build_builder_env,
    build_runtime_image,
    ensure_builder_binary,
    load_dotenv,
    serialize_cloud_build_plan,
    serialize_cloud_build_result,
)


def _runtime(cloud_build: ParsedCloudBuild | None = None):
    return ParsedAgentRuntime(
        name="my-agent",
        container=ParsedContainer(
            image="registry.example.com/ns/app:v1",
            cloud_build=cloud_build,
        ),
    )


def test_build_builder_env_uses_cfg_and_yaml_registry(monkeypatch):
    monkeypatch.delenv("DOCKER_IMAGE_BUILDER_UID", raising=False)
    cfg = SimpleNamespace(
        get_account_id=lambda: "123",
        get_access_key_id=lambda: "ak",
        get_access_key_secret=lambda: "sk",
        get_region_id=lambda: "cn-hangzhou",
    )
    cloud_build = ParsedCloudBuild(
        registry=ParsedCloudBuildRegistry("yaml-u", "yaml-p")
    )
    env = build_builder_env(
        cfg,
        cloud_build,
    )
    assert env["DOCKER_IMAGE_BUILDER_UID"] == "123"
    assert env["DOCKER_IMAGE_BUILDER_AK"] == "ak"
    assert env["DOCKER_IMAGE_BUILDER_SK"] == "sk"
    assert env["DOCKER_IMAGE_BUILDER_REGION"] == "cn-hangzhou"
    assert env["DOCKER_IMAGE_BUILDER_USERNAME"] == "yaml-u"
    assert env["DOCKER_IMAGE_BUILDER_PASSWORD"] == "yaml-p"


def test_load_dotenv_sets_missing_values(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "DOCKER_IMAGE_BUILDER_UID=123",
                "QUOTED='value'",
                "EXISTING=from-file",
                "# ignored",
                "invalid-line",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("DOCKER_IMAGE_BUILDER_UID", raising=False)
    monkeypatch.delenv("QUOTED", raising=False)
    monkeypatch.setenv("EXISTING", "from-env")

    load_dotenv(env_file)

    assert os.environ["DOCKER_IMAGE_BUILDER_UID"] == "123"
    assert os.environ["QUOTED"] == "value"
    assert os.environ["EXISTING"] == "from-env"


def test_build_builder_args_do_not_include_secrets_or_registry_mode():
    cloud_build = ParsedCloudBuild(
        dir=".",
        setup_script="",
        timeout_minutes="30",
        cpu="8c",
        memory="16384",
        registry=ParsedCloudBuildRegistry("u", "secret"),
    )
    args = build_builder_args("/bin/docker-image-builder", "reg/ns/app:v1", cloud_build)
    joined = " ".join(args)
    assert "--image=reg/ns/app:v1" in args
    assert "--setup-script=" in args
    assert "secret" not in joined
    assert "registry-mode" not in joined


def test_build_builder_args_include_base_container_image():
    cloud_build = ParsedCloudBuild(
        base_container_image="registry.example.com/ns/worker:tag"
    )
    args = build_builder_args("/bin/docker-image-builder", "reg/ns/app:v1", cloud_build)
    assert "--base-image=registry.example.com/ns/worker:tag" in args


def test_build_builder_args_include_region():
    cloud_build = ParsedCloudBuild(region="cn-shanghai")
    args = build_builder_args("/bin/docker-image-builder", "reg/ns/app:v1", cloud_build)
    assert "--region=cn-shanghai" in args


def test_serialize_cloud_build_plan_and_result():
    cloud_build = ParsedCloudBuild(
        base_container_image="registry.example.com/ns/worker:tag"
    )
    plan = serialize_cloud_build_plan(_runtime(cloud_build))
    assert plan and plan["baseContainerConfig"]["image"] == (
        "registry.example.com/ns/worker:tag"
    )
    result = serialize_cloud_build_result(
        cloud_build_mod.CloudBuildResult(
            name="my-agent",
            image="registry.example.com/ns/app:v1",
            build_status="completed",
            elapsed_seconds=0.1,
        )
    )
    assert result == {
        "name": "my-agent",
        "image": "registry.example.com/ns/app:v1",
        "buildStatus": "completed",
        "elapsedSeconds": 0.1,
    }
    assert serialize_cloud_build_plan(_runtime(None)) is None


def test_ensure_builder_binary_uses_binpath(monkeypatch, tmp_path):
    binary = tmp_path / "docker-image-builder"
    binary.write_text("#!/bin/sh\n", encoding="utf-8")
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("DOCKER_IMAGE_BUILDER_BINPATH", str(binary))
    assert ensure_builder_binary() == str(binary)


def test_ensure_builder_binary_rejects_bad_binpath(monkeypatch, tmp_path):
    bad_path = tmp_path / "missing"
    monkeypatch.setenv("DOCKER_IMAGE_BUILDER_BINPATH", str(bad_path))
    with pytest.raises(CloudBuildError, match="BINPATH"):
        ensure_builder_binary()


def test_ensure_builder_binary_downloads_fixed_tag(monkeypatch, tmp_path):
    monkeypatch.delenv("DOCKER_IMAGE_BUILDER_BINPATH", raising=False)
    monkeypatch.delenv("DOCKER_IMAGE_BUILDER_BINTAG", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(
        "agentrun_cli._utils.cloud_build._artifact_name",
        lambda: "docker-image-builder-linux-amd64",
    )

    def fake_download(url, target):
        assert f"/{BUILDER_RELEASE_TAG}/" in url
        target.write_text("#!/bin/sh\n", encoding="utf-8")

    monkeypatch.setattr(
        "agentrun_cli._utils.cloud_build._download_binary",
        fake_download,
    )
    binary = ensure_builder_binary()
    expected_suffix = (
        f".docker-image-builder/{BUILDER_RELEASE_TAG}/docker-image-builder"
    )
    assert binary.endswith(expected_suffix)
    assert os.access(binary, os.X_OK)


def test_ensure_builder_binary_uses_cached_bintag(monkeypatch, tmp_path):
    monkeypatch.delenv("DOCKER_IMAGE_BUILDER_BINPATH", raising=False)
    monkeypatch.setenv("DOCKER_IMAGE_BUILDER_BINTAG", "custom-tag")
    monkeypatch.setenv("HOME", str(tmp_path))
    cached = tmp_path / ".docker-image-builder" / "custom-tag" / "docker-image-builder"
    cached.parent.mkdir(parents=True)
    cached.write_text("#!/bin/sh\n", encoding="utf-8")
    cached.chmod(cached.stat().st_mode | stat.S_IXUSR)
    assert ensure_builder_binary() == str(cached)


def test_ensure_builder_binary_download_failure(monkeypatch, tmp_path):
    monkeypatch.delenv("DOCKER_IMAGE_BUILDER_BINPATH", raising=False)
    monkeypatch.delenv("DOCKER_IMAGE_BUILDER_BINTAG", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(
        "agentrun_cli._utils.cloud_build._artifact_name",
        lambda: "docker-image-builder-linux-amd64",
    )
    monkeypatch.setattr(
        "agentrun_cli._utils.cloud_build._download_binary",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    with pytest.raises(CloudBuildError, match="download docker-image-builder failed"):
        ensure_builder_binary()


def test_download_binary(monkeypatch, tmp_path):
    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b"bin"

    target = tmp_path / "docker-image-builder"
    monkeypatch.setattr("urllib.request.urlopen", lambda *_a, **_k: Resp())
    cloud_build_mod._download_binary("https://example.com/bin", target)
    assert target.read_bytes() == b"bin"


def test_build_runtime_image_runs_builder(monkeypatch):
    calls = {}
    cloud_build = ParsedCloudBuild()
    monkeypatch.setattr(
        "agentrun_cli._utils.cloud_build.ensure_builder_binary",
        lambda: "/bin/dib",
    )

    def fake_run(args, env, stdout, stderr, check):
        calls["args"] = args
        calls["env"] = env
        calls["stdout"] = stdout
        calls["stderr"] = stderr
        calls["check"] = check
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("subprocess.run", fake_run)
    result = build_runtime_image(_runtime(cloud_build), SimpleNamespace())
    assert result and result.build_status == "completed"
    assert calls["args"][0] == "/bin/dib"
    assert calls["args"][1] == "build"
    assert calls["stdout"] is sys.stderr
    assert calls["stderr"] is sys.stderr
    assert calls["check"] is False


def test_build_runtime_image_without_cloud_build_returns_none():
    assert build_runtime_image(_runtime(None), SimpleNamespace()) is None


def test_build_runtime_image_failure_raises(monkeypatch):
    cloud_build = ParsedCloudBuild()
    monkeypatch.setattr(
        "agentrun_cli._utils.cloud_build.ensure_builder_binary",
        lambda: "/bin/dib",
    )
    monkeypatch.setattr(
        "subprocess.run",
        lambda *_a, **_k: SimpleNamespace(returncode=7),
    )
    with pytest.raises(CloudBuildError, match="code 7"):
        build_runtime_image(_runtime(cloud_build), SimpleNamespace())


def test_platform_and_arch_helpers(monkeypatch):
    monkeypatch.setattr(cloud_build_mod.sys, "platform", "darwin")
    assert cloud_build_mod._go_platform() == "darwin"
    monkeypatch.setattr(cloud_build_mod.sys, "platform", "win32")
    assert cloud_build_mod._go_platform() == "windows"
    assert cloud_build_mod._executable_name() == "docker-image-builder.exe"
    assert cloud_build_mod._artifact_name().endswith(".exe")
    monkeypatch.setattr(cloud_build_mod.sys, "platform", "plan9")
    with pytest.raises(CloudBuildError, match="unsupported platform"):
        cloud_build_mod._go_platform()

    monkeypatch.setattr(cloud_build_mod.platform, "machine", lambda: "arm64")
    assert cloud_build_mod._go_arch() == "arm64"
    monkeypatch.setattr(cloud_build_mod.platform, "machine", lambda: "sparc")
    with pytest.raises(CloudBuildError, match="unsupported arch"):
        cloud_build_mod._go_arch()


def test_cfg_value_and_set_env_helpers():
    assert cloud_build_mod._cfg_value(SimpleNamespace(account_id="123"), "account_id")
    assert (
        cloud_build_mod._cfg_value(SimpleNamespace(account_id=""), "account_id") is None
    )
    env = {"KEY": "old"}
    cloud_build_mod._set_env_if_present(env, "KEY", "new")
    cloud_build_mod._set_env_if_present(env, "EMPTY", None)
    assert env == {"KEY": "old"}
