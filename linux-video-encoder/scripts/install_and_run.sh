#!/usr/bin/env bash
set -euo pipefail

# This script installs Docker, Docker Compose plugin, NVIDIA Container Toolkit,
# then builds and runs the linux-video-encoder stack.
# Tunable vars (override with env):
#   REPO_URL  - Git URL to clone (set to your fork if publishing)
#   REPO_DIR  - directory to clone into
#   IMAGE_TAG - image name:tag to build

REPO_URL="${REPO_URL:-https://github.com/thashiznit2003/AutoEncoder.git}"
REPO_DIR="${REPO_DIR:-$HOME/AutoEncoder/linux-video-encoder}"
IMAGE_TAG="${IMAGE_TAG:-linux-video-encoder:latest}"

SUDO=""
if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  SUDO="sudo"
fi

log() { printf '[installer] %s\n' "$*"; }

install_docker() {
  if command -v docker >/dev/null 2>&1; then
    log "Docker already installed."
    return
  fi
  log "Installing Docker..."
  $SUDO apt-get update
  $SUDO apt-get install -y ca-certificates curl gnupg lsb-release
  $SUDO install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | $SUDO gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
    $(lsb_release -cs) stable" | $SUDO tee /etc/apt/sources.list.d/docker.list >/dev/null
  $SUDO apt-get update
  $SUDO apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  log "Docker installed."
}

install_nvidia_toolkit() {
  if dpkg -s nvidia-container-toolkit >/dev/null 2>&1; then
    log "NVIDIA Container Toolkit already installed."
  else
    log "Installing NVIDIA Container Toolkit..."
    $SUDO apt-get update
    $SUDO apt-get install -y curl gnupg
    distribution=$(. /etc/os-release; echo "$ID$VERSION_ID")
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | $SUDO gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
    curl -s -L "https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list" | \
      sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
      $SUDO tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
    $SUDO apt-get update
    $SUDO apt-get install -y nvidia-container-toolkit
    $SUDO nvidia-ctk runtime configure --runtime=docker || true
    log "NVIDIA Container Toolkit installed."
  fi
  log "Restarting Docker to pick up NVIDIA runtime..."
  $SUDO systemctl restart docker
}

clone_repo() {
  if [ -d "$REPO_DIR" ]; then
    log "Repo already present at $REPO_DIR; pulling latest..."
    git -C "$REPO_DIR" pull --ff-only || true
  else
    log "Cloning repo from $REPO_URL..."
    git clone "$REPO_URL" "$REPO_DIR"
  fi
}

build_and_run() {
  cd "$REPO_DIR/linux-video-encoder" || cd "$REPO_DIR"
  log "Building image $IMAGE_TAG ..."
  $SUDO docker build -t "$IMAGE_TAG" .
  log "Starting stack with docker compose..."
  IMAGE_TAG="$IMAGE_TAG" $SUDO docker compose up -d
  log "Stack is running. Web UI: http://<host>:5959"
}

main() {
  install_docker
  install_nvidia_toolkit
  clone_repo
  build_and_run
}

main "$@"
