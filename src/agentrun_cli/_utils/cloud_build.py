"""Agent Runtime cloud image build helpers."""

from __future__ import annotations

import os
import platform
import stat
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from agentrun_cli._utils.agentruntime_yaml import ParsedAgentRuntime, ParsedCloudBuild

BUILDER_RELEASE_TAG = "latest"
BUILDER_BASE_URL = "https://images.devsapp.cn/docker-image-builder"


class CloudBuildError(RuntimeError):
    """Raised when cloud build fails."""


@dataclass
class CloudBuildResult:
    """Cloud build result for one runtime."""

    name: str
    image: str
    build_status: str
    elapsed_seconds: float


def load_dotenv(path: Path | None = None) -> None:
    """Load dotenv values into process environment.

    Args:
        path: Dotenv path. Defaults to `.env` under the current working directory.
    """
    env_path = path or Path.cwd() / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def build_runtime_image(
    parsed: ParsedAgentRuntime,
    cfg: Any,
) -> CloudBuildResult | None:
    """Build the runtime image according to `cloudBuild`.

    Args:
        parsed: Parsed runtime document.
        cfg: AgentRun SDK config or a test double.
    """
    cloud_build = parsed.container.cloud_build
    if cloud_build is None:
        return None

    started = time.monotonic()
    image = parsed.container.image
    binary_path = ensure_builder_binary()
    env = build_builder_env(cfg, cloud_build)
    args = build_builder_args(binary_path, image, cloud_build)
    completed = subprocess.run(  # noqa: S603
        args,
        env=env,
        stdout=sys.stderr,
        stderr=sys.stderr,
        check=False,
    )
    if completed.returncode != 0:
        raise CloudBuildError(
            f"docker-image-builder exited with code {completed.returncode}"
        )

    return CloudBuildResult(
        name=parsed.name,
        image=image,
        build_status="completed",
        elapsed_seconds=round(time.monotonic() - started, 3),
    )


def build_builder_env(
    cfg: Any,
    cloud_build: ParsedCloudBuild,
) -> dict[str, str]:
    """Build docker-image-builder subprocess environment variables.

    Args:
        cfg: AgentRun SDK config or a test double.
        cloud_build: Parsed build configuration.
    """
    env = os.environ.copy()
    _set_env_if_present(env, "DOCKER_IMAGE_BUILDER_UID", _cfg_value(cfg, "account_id"))
    _set_env_if_present(
        env,
        "DOCKER_IMAGE_BUILDER_AK",
        _cfg_value(cfg, "access_key_id"),
    )
    _set_env_if_present(
        env,
        "DOCKER_IMAGE_BUILDER_SK",
        _cfg_value(cfg, "access_key_secret"),
    )
    _set_env_if_present(
        env,
        "DOCKER_IMAGE_BUILDER_REGION",
        cloud_build.region or _cfg_value(cfg, "region_id"),
    )
    if cloud_build.registry and cloud_build.registry.username:
        env["DOCKER_IMAGE_BUILDER_USERNAME"] = cloud_build.registry.username
    if cloud_build.registry and cloud_build.registry.password:
        env["DOCKER_IMAGE_BUILDER_PASSWORD"] = cloud_build.registry.password
    return env


def build_builder_args(
    binary_path: str,
    image: str,
    cloud_build: ParsedCloudBuild,
) -> list[str]:
    """Build docker-image-builder CLI arguments.

    Args:
        binary_path: Path to the builder executable.
        image: Target image.
        cloud_build: Parsed build configuration.
    """
    args = [
        binary_path,
        "build",
        f"--image={image}",
        f"--dir={cloud_build.dir}",
        f"--setup-script={cloud_build.setup_script}",
        f"--timeout-minutes={cloud_build.timeout_minutes}",
        f"--cpu={cloud_build.cpu}",
        f"--memory={cloud_build.memory}",
    ]
    if cloud_build.region:
        args.append(f"--region={cloud_build.region}")
    if cloud_build.base_container_image:
        args.append(f"--base-image={cloud_build.base_container_image}")
    return args


def serialize_cloud_build_plan(parsed: ParsedAgentRuntime) -> dict | None:
    """Serialize `cloudBuild` configuration for render output.

    Args:
        parsed: Parsed runtime document.
    """
    cloud_build = parsed.container.cloud_build
    if cloud_build is None:
        return None
    plan: dict[str, Any] = {
        "image": parsed.container.image,
        "dir": cloud_build.dir,
        "setupScript": cloud_build.setup_script,
        "timeoutMinutes": cloud_build.timeout_minutes,
        "cpu": cloud_build.cpu,
        "memory": cloud_build.memory,
        "region": cloud_build.region,
    }
    if cloud_build.base_container_image:
        plan["baseContainerConfig"] = {"image": cloud_build.base_container_image}
    return plan


def serialize_cloud_build_result(result: CloudBuildResult) -> dict:
    """Serialize a build result for CLI output.

    Args:
        result: Cloud build result for one runtime.
    """
    return {
        "name": result.name,
        "image": result.image,
        "buildStatus": result.build_status,
        "elapsedSeconds": result.elapsed_seconds,
    }


def ensure_builder_binary() -> str:
    """Return an executable docker-image-builder path."""
    configured = os.getenv("DOCKER_IMAGE_BUILDER_BINPATH", "").strip()
    if configured:
        if _is_executable(Path(configured)):
            return configured
        raise CloudBuildError(
            "DOCKER_IMAGE_BUILDER_BINPATH does not exist or is not executable: "
            f"{configured}"
        )

    tag = os.getenv("DOCKER_IMAGE_BUILDER_BINTAG", "").strip() or BUILDER_RELEASE_TAG
    install_dir = Path.home() / ".docker-image-builder" / tag
    target = install_dir / _executable_name()

    install_dir.mkdir(parents=True, exist_ok=True)
    tmp = install_dir / f"{_executable_name()}.tmp-{os.getpid()}"
    artifact = _artifact_name()
    url = f"{BUILDER_BASE_URL}/{tag}/{artifact}"
    try:
        expected_sha256 = _download_sha256(f"{url}.sha256", artifact)
        if _is_executable(target) and _sha256_file(target) == expected_sha256:
            return str(target)
        _download_binary(url, tmp)
        _verify_sha256(tmp, expected_sha256)
        tmp.chmod(tmp.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        tmp.replace(target)
    except Exception as exc:
        tmp.unlink(missing_ok=True)
        raise CloudBuildError(f"download docker-image-builder failed: {exc}") from exc
    return str(target)


def _download_binary(url: str, target: Path) -> None:
    """Download a binary to a temporary local path.

    Args:
        url: Download URL.
        target: Target file path.
    """
    with urllib.request.urlopen(url, timeout=120) as resp:  # noqa: S310
        target.write_bytes(resp.read())


def _download_sha256(url: str, artifact_name: str) -> str:
    """Download and parse a SHA256 checksum file.

    Args:
        url: Checksum URL.
        artifact_name: Expected release artifact name.
    """
    with urllib.request.urlopen(url, timeout=30) as resp:  # noqa: S310
        text = resp.read().decode("utf-8")
    return _parse_sha256(text, artifact_name)


def _parse_sha256(text: str, artifact_name: str) -> str:
    """Parse a SHA256 checksum file.

    Args:
        text: Checksum file content.
        artifact_name: Expected release artifact name.
    """
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        digest = parts[0].lower()
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            continue
        if len(parts) == 1 or parts[-1].lstrip("*") == artifact_name:
            return digest
    raise CloudBuildError(f"invalid sha256 checksum file for {artifact_name}")


def _verify_sha256(path: Path, expected_sha256: str) -> None:
    """Verify a local file against an expected SHA256 digest.

    Args:
        path: File path to verify.
        expected_sha256: Expected SHA256 digest.
    """
    actual_sha256 = _sha256_file(path)
    if actual_sha256 != expected_sha256:
        raise CloudBuildError(
            "checksum mismatch for docker-image-builder: "
            f"expected {expected_sha256}, got {actual_sha256}"
        )


def _sha256_file(path: Path) -> str:
    """Compute the SHA256 digest of a local file.

    Args:
        path: File path to hash.
    """
    digest = sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_executable(path: Path) -> bool:
    """Return whether the path is an executable file.

    Args:
        path: Path to inspect.
    """
    return path.is_file() and os.access(path, os.X_OK)


def _executable_name() -> str:
    """Return the executable filename for the current platform."""
    if sys.platform == "win32":
        return "docker-image-builder.exe"
    return "docker-image-builder"


def _artifact_name() -> str:
    """Return the release artifact name on OSS."""
    os_name = _go_platform()
    arch = _go_arch()
    suffix = ".exe" if os_name == "windows" else ""
    return f"docker-image-builder-{os_name}-{arch}{suffix}"


def _go_platform() -> str:
    """Convert a Python platform name to a Go release platform name."""
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "darwin"
    if sys.platform.startswith("linux"):
        return "linux"
    raise CloudBuildError(f"unsupported platform: {sys.platform}")


def _go_arch() -> str:
    """Convert a Python architecture name to a Go release architecture name."""
    machine = platform.machine().lower()
    if machine in ("x86_64", "amd64"):
        return "amd64"
    if machine in ("aarch64", "arm64"):
        return "arm64"
    raise CloudBuildError(f"unsupported arch: {platform.machine()}")


def _cfg_value(cfg: Any, name: str) -> str | None:
    """Read a field value from an SDK Config object.

    Args:
        cfg: SDK Config object or test double.
        name: Field name without the `get_` prefix.
    """
    method_name = f"get_{name}"
    for candidate in (method_name, name):
        if not hasattr(cfg, candidate):
            continue
        value = getattr(cfg, candidate)
        if callable(value):
            value = value()
        if value:
            return str(value)
    return None


def _set_env_if_present(env: dict[str, str], key: str, value: str | None) -> None:
    """Set a non-empty environment value when the key is missing.

    Args:
        env: Child process environment mapping.
        key: Environment variable name.
        value: Candidate value.
    """
    if value and not env.get(key):
        env[key] = value
