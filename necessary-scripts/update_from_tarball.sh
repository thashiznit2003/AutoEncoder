#!/usr/bin/env bash
set -euo pipefail

SUDO=""
if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  SUDO="sudo"
  if ! command -v sudo >/dev/null 2>&1; then
    printf '[update-tarball] sudo not found; please install sudo or run as root.\n' >&2
    exit 1
  fi
fi

BASE_DIR="${BASE_DIR:-/linux-video-encoder}"
REPO_DIR="${REPO_DIR:-$BASE_DIR/AutoEncoder}"
REPO_TARBALL_URL="${REPO_TARBALL_URL:-https://github.com/thashiznit2003/AutoEncoder/archive/refs/heads/main.tar.gz}"
IMAGE_TAG="${IMAGE_TAG:-linux-video-encoder:latest}"
COMPOSE_FILE="${COMPOSE_FILE:-$REPO_DIR/linux-video-encoder/docker-compose.yml}"

log() { printf '[update-tarball] %s\n' "$*"; }

if ! command -v curl >/dev/null 2>&1 || ! command -v tar >/dev/null 2>&1; then
  log "Installing curl and tar..."
  $SUDO apt-get update
  $SUDO apt-get install -y curl tar
fi

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

log "Downloading repo tarball..."
curl -fsSL "$REPO_TARBALL_URL" -o "$tmpdir/repo.tar.gz"
tar -xzf "$tmpdir/repo.tar.gz" -C "$tmpdir"
extracted="$(find "$tmpdir" -maxdepth 1 -type d -name 'AutoEncoder*' | head -n 1)"
if [ -z "$extracted" ] || [ ! -d "$extracted" ]; then
  log "Failed to find extracted repo folder in tarball."
  exit 1
fi

log "Replacing $REPO_DIR with fresh download..."
if [ -d "$REPO_DIR" ]; then
  $SUDO rm -rf "$REPO_DIR"
fi
$SUDO mv "$extracted" "$REPO_DIR"

log "Building image $IMAGE_TAG from repo root..."
$SUDO docker build \
  --build-arg MAKEMKV_VERSION="${MAKEMKV_VERSION:-1.18.2}" \
  --build-arg MAKEMKV_BASE_URL="${MAKEMKV_BASE_URL:-https://www.makemkv.com/download}" \
  -f "$REPO_DIR/linux-video-encoder/Dockerfile" \
  -t "$IMAGE_TAG" "$REPO_DIR"

log "Restarting stack (no-build)..."
IMAGE_TAG="$IMAGE_TAG" $SUDO docker compose -f "$COMPOSE_FILE" up -d --no-build

log "Update complete."
