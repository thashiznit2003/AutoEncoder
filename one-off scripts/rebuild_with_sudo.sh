#!/usr/bin/env bash
set -euo pipefail
REPO_DIR="${REPO_DIR:-/linux-video-encoder/AutoEncoder/linux-video-encoder}"
cd "$REPO_DIR"

sudo docker compose down
sudo git fetch origin
sudo git reset --hard origin/main
sudo git clean -fdx
sudo docker compose build --no-cache
sudo docker compose up -d
