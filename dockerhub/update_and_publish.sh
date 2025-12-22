#!/usr/bin/env bash
set -euo pipefail

SUDO=""
if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  SUDO="sudo"
  if ! command -v sudo >/dev/null 2>&1; then
    printf '[dockerhub-update] sudo not found; please install sudo or run as root.\n' >&2
    exit 1
  fi
fi

REPO_DIR="${REPO_DIR:-/linux-video-encoder/AutoEncoder}"
IMAGE_TAG="${IMAGE_TAG:-thashiznit2003/autoencoder}"
VERSION_TAG="${VERSION_TAG:-}"
FORCE_MAKEMKV_DOWNLOAD="${FORCE_MAKEMKV_DOWNLOAD:-0}"

log() { printf '[dockerhub-update] %s\n' "$*"; }

log "Updating repo..."
cd "$REPO_DIR"
$SUDO git pull --ff-only

if [ -z "$VERSION_TAG" ]; then
  version_file="$REPO_DIR/linux-video-encoder/src/version.py"
  if [ ! -f "$version_file" ]; then
    log "version.py not found at $version_file"
    exit 1
  fi
  VERSION_TAG="$(awk -F '\"' '/VERSION/{print $2; exit}' "$version_file" || true)"
  if [ -z "$VERSION_TAG" ]; then
    VERSION_TAG="$(grep -oE '[0-9]+\\.[0-9]+\\.[0-9]+' "$version_file" | head -n 1 || true)"
  fi
  if [ -z "$VERSION_TAG" ] && command -v python3 >/dev/null 2>&1; then
    VERSION_TAG="$(python3 - <<PY
import re
path="${version_file}"
with open(path, "r", encoding="utf-8") as f:
    m=re.search(r'VERSION\\s*=\\s*\\"([^\\"]+)\\"', f.read())
print(m.group(1) if m else "")
PY
)"
  fi
fi

if [ -z "$VERSION_TAG" ]; then
  log "Could not determine VERSION_TAG. Set VERSION_TAG explicitly."
  exit 1
fi

log "Building Docker Hub image..."
$SUDO docker build -f "$REPO_DIR/dockerhub/Dockerfile" -t "${IMAGE_TAG}:beta" -t "${IMAGE_TAG}:${VERSION_TAG}" "$REPO_DIR"

log "Pushing Docker Hub image..."
$SUDO docker push "${IMAGE_TAG}:beta"
$SUDO docker push "${IMAGE_TAG}:${VERSION_TAG}"

log "Rebuilding local MakeMKV image (no re-download by default)..."
curl -fsSL https://raw.githubusercontent.com/thashiznit2003/AutoEncoder/main/dockerhub/with-makemkv/build_with_makemkv.sh -o /tmp/build_with_makemkv.sh
chmod +x /tmp/build_with_makemkv.sh
if [ "$FORCE_MAKEMKV_DOWNLOAD" = "1" ]; then
  FORCE_MAKEMKV_DOWNLOAD=1 $SUDO /tmp/build_with_makemkv.sh
else
  $SUDO /tmp/build_with_makemkv.sh
fi

log "Done. In Portainer, update & redeploy the stack to use the new image."
