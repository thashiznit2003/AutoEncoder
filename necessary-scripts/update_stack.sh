#!/usr/bin/env bash
# Update the linux-video-encoder stack to the latest main branch and restart it.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/thashiznit2003/AutoEncoder/main/necessary-scripts/update_stack.sh -o /tmp/update_stack.sh
#   bash /tmp/update_stack.sh
#
# Tunables (env):
#   BASE_DIR       Base install dir (default: /linux-video-encoder)
#   REPO_URL       Git URL (default: https://github.com/thashiznit2003/AutoEncoder.git)
#   IMAGE_TAG      Image tag (default: linux-video-encoder:latest)
#   BUILD_ARGS     Extra docker build args (optional)
#   NO_CACHE=1     Build without cache

set -euo pipefail

BASE_DIR="${BASE_DIR:-/linux-video-encoder}"
REPO_URL="${REPO_URL:-https://github.com/thashiznit2003/AutoEncoder.git}"
REPO_DIR="${REPO_DIR:-$BASE_DIR/AutoEncoder}"
STACK_DIR="${STACK_DIR:-$REPO_DIR/linux-video-encoder}"
IMAGE_TAG="${IMAGE_TAG:-linux-video-encoder:latest}"
BUILD_ARGS="${BUILD_ARGS:-}"
NO_CACHE="${NO_CACHE:-0}"

log() { printf '[update-stack] %s\n' "$*"; }

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    log "Missing required command: $1"
    exit 1
  fi
}

require_cmd git
require_cmd docker

mkdir -p "$BASE_DIR"

if [ -d "$REPO_DIR/.git" ]; then
  log "Repo exists; pulling latest..."
  git -C "$REPO_DIR" fetch --all
  git -C "$REPO_DIR" reset --hard origin/main
else
  log "Cloning repo..."
  git clone "$REPO_URL" "$REPO_DIR"
fi

cd "$STACK_DIR"

# Ensure media dirs exist for compose mounts
mkdir -p USB DVD Bluray File Output Ripped

log "Stopping stack..."
docker compose down || true

log "Building image $IMAGE_TAG ..."
cache_flag=""
[ "$NO_CACHE" = "1" ] && cache_flag="--no-cache"
docker compose build $cache_flag ${BUILD_ARGS:+--build-arg $BUILD_ARGS}

log "Starting stack..."
docker compose up -d

log "Done. Web UI should be available on port 5959."
