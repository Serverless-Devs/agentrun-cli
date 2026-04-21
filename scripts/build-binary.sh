#!/usr/bin/env bash
# Build the agentrun CLI as a single-file binary using Nuitka --onefile.
#
# Called by `make build` and by .github/workflows/release.yml.
# Output: ./dist/agentrun (or ./dist/agentrun.exe on Windows).
#
# Exit codes: 0 success, non-zero = Nuitka failure (propagates).

set -euo pipefail

# ----- Config -----------------------------------------------------------
# EXCLUDES: 1:1 port of the old agentrun.spec EXCLUDES list.
# Any transitive dep of agentrun-sdk[core] that the CLI does NOT use at
# runtime goes here. Keep sorted for review clarity.
EXCLUDES="\
agentrun_mem0,\
agentrun_mem0ai,\
alibabacloud_bailian20231229,\
alibabacloud_gpdb20160503,\
Crypto,\
fsspec,\
future,\
google,\
grpcio,\
h2,\
hf_xet,\
huggingface_hub,\
jinja2,\
litellm,\
markdown_it,\
matplotlib,\
MySQLdb,\
mysql,\
numpy,\
oss2,\
pandas,\
PIL,\
posthog,\
pycryptodome,\
pygments,\
pytz,\
qdrant_client,\
regex,\
rich,\
sklearn,\
scipy,\
sqlalchemy,\
tablestore,\
tensorflow,\
tiktoken,\
tokenizers,\
torch,\
transformers"

# Version: read from setuptools-scm generated file if present, else fall
# back to git describe, else "0.0.0+unknown".
VERSION=$(python3 -c "from src.agentrun_cli import __version__; print(__version__)" 2>/dev/null \
  || git describe --tags --always --dirty 2>/dev/null \
  || echo "0.0.0+unknown")

# Nuitka's --product-version requires a strict N(.N)* form with all numeric
# components. Derive a sanitized variant by stripping PEP 440 pre-release /
# dev / local suffixes and padding to 3 components, so
# "0.1.0rc5.dev2+g1713d9f79.d20260421" normalizes to "0.1.0" and
# "0.3.0rc1" also normalizes to "0.3.0" (stable cache-dir naming).
PRODUCT_VERSION=$(python3 -c "
import re, sys
v = sys.argv[1]
# Drop local segment (anything after '+') and any non-numeric trailing
# components (rc, dev, a, b, post, ...).
v = v.split('+', 1)[0]
parts = v.split('.')
out = []
for p in parts:
    if re.fullmatch(r'[0-9]+', p):
        out.append(p)
    else:
        break
# Pad to 3 numeric components so '0.3.0', '0.3.0rc1', and '0.3.0.dev2'
# all normalize to '0.3.0' (stable cache-dir naming under ~/.agentrun/cache/).
out = (out + ['0', '0', '0'])[:3]
print('.'.join(out))
" "$VERSION")

# Cache directory (per design doc, co-located with ~/.agentrun/config.json).
# Nuitka expands {HOME} and {VERSION} at bootstrap time. Each binary
# version gets its own subdirectory so upgrades don't collide.
TEMPDIR_SPEC='{HOME}/.agentrun/cache/agentrun-{VERSION}'

# Output filename differs on Windows (.exe suffix handled by Nuitka).
mkdir -p dist

# ----- Build ------------------------------------------------------------
echo "=== Building agentrun (version: $VERSION) with Nuitka --onefile ==="
python3 -m nuitka \
  --onefile \
  --standalone \
  --assume-yes-for-downloads \
  --output-filename=agentrun \
  --output-dir=dist \
  --include-package=agentrun_cli \
  --include-package-data=certifi \
  --onefile-tempdir-spec="$TEMPDIR_SPEC" \
  --product-name=agentrun \
  --product-version="$PRODUCT_VERSION" \
  --python-flag=-O \
  --nofollow-import-to="$EXCLUDES" \
  --remove-output \
  src/agentrun_cli/main.py

# ----- Post-build report ------------------------------------------------
BINARY="dist/agentrun"
[ -f "${BINARY}.exe" ] && BINARY="${BINARY}.exe"
echo ""
echo "=== Build complete ==="
ls -lh "$BINARY"
