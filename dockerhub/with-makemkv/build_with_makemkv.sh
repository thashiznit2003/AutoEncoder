#!/usr/bin/env bash
set -euo pipefail

SUDO=""
if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  SUDO="sudo"
  if ! command -v sudo >/dev/null 2>&1; then
    printf '[with-makemkv] sudo not found; please install sudo or run as root.\n' >&2
    exit 1
  fi
fi

WORKDIR="${WORKDIR:-/linux-video-encoder}"
REPO_DIR="${REPO_DIR:-$WORKDIR/AutoEncoder}"
MAKEMKV_VERSION="${MAKEMKV_VERSION:-1.18.2}"
MAKEMKV_BASE_URL="${MAKEMKV_BASE_URL:-https://www.makemkv.com/download}"
IMAGE_TAG="${IMAGE_TAG:-linux-video-encoder:latest}"
BASE_IMAGE_TAG="${BASE_IMAGE_TAG:-thashiznit2003/autoencoder:beta}"

log() { printf '[with-makemkv] %s\n' "$*"; }

if ! command -v curl >/dev/null 2>&1 || ! command -v tar >/dev/null 2>&1; then
  log "Installing curl and tar..."
  $SUDO apt-get update
  $SUDO apt-get install -y curl tar
fi

$SUDO mkdir -p "$WORKDIR"
if [ ! -d "$REPO_DIR" ]; then
  log "Downloading repo tarball..."
  tmpdir="$(mktemp -d)"
  curl -fsSL "https://github.com/thashiznit2003/AutoEncoder/archive/refs/heads/main.tar.gz" -o "$tmpdir/repo.tar.gz"
  tar -xzf "$tmpdir/repo.tar.gz" -C "$tmpdir"
  extracted="$(find "$tmpdir" -maxdepth 1 -type d -name 'AutoEncoder*' | head -n 1)"
  if [ -z "$extracted" ] || [ ! -d "$extracted" ]; then
    log "Failed to find extracted repo folder in tarball."
    exit 1
  fi
  $SUDO rm -rf "$REPO_DIR"
  $SUDO mv "$extracted" "$REPO_DIR"
  rm -rf "$tmpdir"
fi

log "Downloading MakeMKV tarballs..."
cd "$REPO_DIR"
for f in "makemkv-bin-${MAKEMKV_VERSION}.tar.gz" "makemkv-oss-${MAKEMKV_VERSION}.tar.gz"; do
  url="${MAKEMKV_BASE_URL}/${f}"
  if [ -s "$f" ]; then
    log "$f already present; reusing."
    continue
  fi
  log "Downloading $f from $url"
  curl -fsSL "$url" -o "$f"
  $SUDO chmod 644 "$f" || true
done

log "Building local image with MakeMKV on top of Docker Hub image..."
$SUDO docker pull "$BASE_IMAGE_TAG"
$SUDO docker build \
  --build-arg MAKEMKV_VERSION="$MAKEMKV_VERSION" \
  -f "$REPO_DIR/dockerhub/with-makemkv/Dockerfile" \
  -t "$IMAGE_TAG" \
  "$REPO_DIR"

log "Build complete. Use image: $IMAGE_TAG"
