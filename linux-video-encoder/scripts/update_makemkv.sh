#!/usr/bin/env bash
set -euo pipefail

# Update MakeMKV by rebuilding the container image with a specified version and restarting the stack.
# Defaults:
#   BASE_DIR=/linux-video-encoder
#   REPO_DIR=$BASE_DIR/AutoEncoder/linux-video-encoder
#   MAKEMKV_VERSION (env override, default 1.18.2)
#   IMAGE_TAG=linux-video-encoder:latest

SUDO=""
if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  SUDO="sudo"
  if ! command -v sudo >/dev/null 2>&1; then
    printf '[update-makemkv] sudo not found; please run as root.\n' >&2
    exit 1
  fi
fi

BASE_DIR="${BASE_DIR:-/linux-video-encoder}"
REPO_DIR="${REPO_DIR:-$BASE_DIR/AutoEncoder/linux-video-encoder}"
MAKEMKV_VERSION="${MAKEMKV_VERSION:-1.18.2}"
IMAGE_TAG="${IMAGE_TAG:-linux-video-encoder:latest}"

log() { printf '[update-makemkv] %s\n' "$*"; }

if [ ! -d "$REPO_DIR" ]; then
  log "Repo dir not found at $REPO_DIR"
  exit 1
fi

log "Pulling latest repository..."
if command -v git >/dev/null 2>&1; then
  git -C "$REPO_DIR" pull --ff-only || true
else
  log "git not available; skipping git pull."
fi

log "Rebuilding image with MAKEMKV_VERSION=${MAKEMKV_VERSION} ..."
(cd "$REPO_DIR" && IMAGE_TAG="$IMAGE_TAG" $SUDO docker compose build --no-cache --build-arg MAKEMKV_VERSION="$MAKEMKV_VERSION")

log "Restarting stack..."
(cd "$REPO_DIR" && IMAGE_TAG="$IMAGE_TAG" $SUDO docker compose down && IMAGE_TAG="$IMAGE_TAG" $SUDO docker compose up -d --force-recreate)

log "Done. Web UI at http://<host>:5959"
