#!/usr/bin/env sh
#
# AgentRun CLI installer for Linux and macOS.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/Serverless-Devs/agentrun-cli/main/scripts/install.sh | sh
#
# Environment overrides:
#   AGENTRUN_VERSION   Pin to a specific version (e.g. v0.1.0). Default: latest release.
#   AGENTRUN_INSTALL   Install directory. Default: $HOME/.local/bin
#   AGENTRUN_REPO      owner/repo slug. Default: Serverless-Devs/agentrun-cli

set -eu

REPO="${AGENTRUN_REPO:-Serverless-Devs/agentrun-cli}"
INSTALL_DIR="${AGENTRUN_INSTALL:-$HOME/.local/bin}"
VERSION="${AGENTRUN_VERSION:-}"

BIN_NAME="agentrun"

# ---------- helpers ----------
err()  { printf "\033[31merror:\033[0m %s\n" "$*" >&2; exit 1; }
info() { printf "\033[34m==>\033[0m %s\n" "$*"; }
warn() { printf "\033[33mwarn:\033[0m %s\n" "$*" >&2; }

need() { command -v "$1" >/dev/null 2>&1 || err "'$1' is required but not installed"; }

need uname
need tar
need mkdir
if command -v curl >/dev/null 2>&1; then
    DOWNLOAD="curl -fsSL"
elif command -v wget >/dev/null 2>&1; then
    DOWNLOAD="wget -qO-"
else
    err "need curl or wget"
fi

# ---------- detect platform ----------
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
case "$OS" in
    linux)  OS=linux ;;
    darwin) OS=darwin ;;
    *)      err "unsupported OS: $OS (this installer is for Linux/macOS; use install.ps1 on Windows)" ;;
esac

ARCH=$(uname -m)
case "$ARCH" in
    x86_64|amd64)       ARCH=amd64 ;;
    arm64|aarch64)      ARCH=arm64 ;;
    *)                  err "unsupported arch: $ARCH" ;;
esac

TARGET="${OS}-${ARCH}"
info "Detected target: $TARGET"

# ---------- resolve version ----------
if [ -z "$VERSION" ]; then
    info "Resolving latest release from github.com/${REPO}"
    VERSION=$($DOWNLOAD "https://api.github.com/repos/${REPO}/releases/latest" \
        | grep '"tag_name"' | head -1 | sed -E 's/.*"tag_name":[[:space:]]*"([^"]+)".*/\1/')
    [ -n "$VERSION" ] || err "could not resolve latest release tag"
fi
info "Version: $VERSION"

# Strip leading v for the asset filename component.
VERSION_NUM="${VERSION#v}"
ASSET="agentrun-${VERSION_NUM}-${TARGET}.tar.gz"
URL="https://github.com/${REPO}/releases/download/${VERSION}/${ASSET}"
SHA_URL="${URL}.sha256"

# ---------- download ----------
TMP=$(mktemp -d 2>/dev/null || mktemp -d -t agentrun-install)
trap 'rm -rf "$TMP"' EXIT

info "Downloading $ASSET"
$DOWNLOAD "$URL"     > "$TMP/$ASSET"     || err "download failed: $URL"
$DOWNLOAD "$SHA_URL" > "$TMP/$ASSET.sha256" || err "checksum download failed: $SHA_URL"

# ---------- verify checksum ----------
if command -v shasum >/dev/null 2>&1; then
    SUM_CMD="shasum -a 256"
elif command -v sha256sum >/dev/null 2>&1; then
    SUM_CMD="sha256sum"
else
    warn "no shasum/sha256sum available, skipping checksum verification"
    SUM_CMD=""
fi

if [ -n "$SUM_CMD" ]; then
    EXPECTED=$(awk '{print $1}' "$TMP/$ASSET.sha256")
    ACTUAL=$(cd "$TMP" && $SUM_CMD "$ASSET" | awk '{print $1}')
    [ "$EXPECTED" = "$ACTUAL" ] || err "checksum mismatch (expected $EXPECTED, got $ACTUAL)"
    info "Checksum OK"
fi

# ---------- extract & install ----------
tar -xzf "$TMP/$ASSET" -C "$TMP"
[ -f "$TMP/$BIN_NAME" ] || err "archive did not contain '$BIN_NAME'"

mkdir -p "$INSTALL_DIR"
mv "$TMP/$BIN_NAME" "$INSTALL_DIR/$BIN_NAME"
chmod +x "$INSTALL_DIR/$BIN_NAME"

# Provide short alias `ar` by symlink; skip if target exists (system `ar` binutils).
if [ ! -e "$INSTALL_DIR/ar" ]; then
    ln -s "$INSTALL_DIR/$BIN_NAME" "$INSTALL_DIR/ar"
fi

info "Installed $BIN_NAME → $INSTALL_DIR/$BIN_NAME"

# ---------- PATH hint ----------
case ":$PATH:" in
    *":$INSTALL_DIR:"*)
        info "Run: $BIN_NAME --version"
        ;;
    *)
        warn "$INSTALL_DIR is not in your PATH."
        cat <<EOF
  Add this line to your shell profile (~/.bashrc, ~/.zshrc, or equivalent):

    export PATH="$INSTALL_DIR:\$PATH"

  Then reload the shell and run: $BIN_NAME --version
EOF
        ;;
esac
