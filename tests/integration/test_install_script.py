"""Integration tests for the Unix installer script."""

import os
import stat
import subprocess
from pathlib import Path


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def test_install_sh_parses_latest_release_tag_on_posix_sed(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    install_dir = tmp_path / "install"

    calls = tmp_path / "curl-calls.txt"
    _write_executable(
        fake_bin / "curl",
        f"""#!/usr/bin/env sh
set -eu
url="${{@:$#}}"
printf '%s\\n' "$url" >> "{calls}"
case "$url" in
  *"/releases/latest")
    printf '%s\\n' '{{'
    printf '%s\\n' '  "tag_name": "v0.1.0",'
    printf '%s\\n' '}}'
    ;;
  *".sha256")
    printf '%s\\n' 'expected-sha  agentrun-0.1.0-darwin-arm64.tar.gz'
    ;;
  *)
    printf '%s\\n' 'fake archive'
    ;;
esac
""",
    )
    _write_executable(
        fake_bin / "uname",
        """#!/usr/bin/env sh
case "${1:-}" in
  -s) printf '%s\n' Darwin ;;
  -m) printf '%s\n' arm64 ;;
  *) printf '%s\n' Darwin ;;
esac
""",
    )
    _write_executable(
        fake_bin / "tar",
        """#!/usr/bin/env sh
while [ "$#" -gt 0 ]; do
  if [ "$1" = "-C" ]; then
    shift
    install_dir="$1"
    break
  fi
  shift
done
printf '%s\n' '#!/usr/bin/env sh' > "$install_dir/agentrun"
chmod +x "$install_dir/agentrun"
""",
    )
    _write_executable(
        fake_bin / "shasum",
        """#!/usr/bin/env sh
printf '%s\n' 'expected-sha  agentrun-0.1.0-darwin-arm64.tar.gz'
""",
    )

    env = {
        **os.environ,
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "AGENTRUN_INSTALL": str(install_dir),
        "AGENTRUN_REPO": "Serverless-Devs/agentrun-cli",
    }

    result = subprocess.run(
        ["sh", str(repo_root / "scripts" / "install.sh")],
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Version: v0.1.0" in result.stdout
    assert "Downloading agentrun-0.1.0-darwin-arm64.tar.gz" in result.stdout
    assert (install_dir / "agentrun").exists()
    assert (
        "https://github.com/Serverless-Devs/agentrun-cli/releases/download/"
        "v0.1.0/agentrun-0.1.0-darwin-arm64.tar.gz"
    ) in calls.read_text()
