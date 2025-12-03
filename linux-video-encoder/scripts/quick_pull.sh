#!/usr/bin/env bash
# Pull latest code and restart the stack without rebuild (bind mounts keep code live).
# Usage:
#   cd /linux-video-encoder/AutoEncoder/linux-video-encoder
#   bash scripts/quick_pull.sh

set -euo pipefail

log() { printf '[quick-pull] %s\n' "$*"; }

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    log "Missing required command: $1"
    exit 1
  fi
}

require_cmd git
require_cmd docker

log "Pulling latest from origin/main..."
git pull --ff-only

log "Restarting stack (no rebuild)..."
docker compose down
docker compose up -d --force-recreate

log "Done. If code changes don't apply, ensure src/scripts are bind-mounted in docker-compose.yml."
