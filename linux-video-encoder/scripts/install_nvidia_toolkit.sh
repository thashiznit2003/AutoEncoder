#!/usr/bin/env bash
# Install NVIDIA Container Toolkit via NVIDIA APT repo (pinned to ubuntu22.04 packages, which work on 24.04).
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/thashiznit2003/AutoEncoder/main/linux-video-encoder/scripts/install_nvidia_toolkit.sh -o /tmp/install_nvidia_toolkit.sh
#   sudo bash /tmp/install_nvidia_toolkit.sh
#
# Tunables:
#   RUN_NVIDIA_TEST=1  Run a test container after install: docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi

set -euo pipefail
SUDO=""
if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  SUDO="sudo"
fi

log() { printf '[nvidia-ctk] %s\n' "$*"; }

ensure_tools() {
  if ! command -v curl >/dev/null 2>&1; then
    log "Installing curl..."
    $SUDO apt-get update
    $SUDO apt-get install -y curl
  fi
  if ! command -v gpg >/dev/null 2>&1; then
    log "Installing gpg..."
    $SUDO apt-get update
    $SUDO apt-get install -y gpg
  fi
}

add_repo() {
  # Force repo path to ubuntu22.04 because NVIDIA has not published ubuntu24.04 yet.
  local distribution="ubuntu22.04"
  local list="/etc/apt/sources.list.d/nvidia-container-toolkit.list"
  log "Removing any bad/old repo list..."
  $SUDO rm -f "$list"
  log "Adding NVIDIA key..."
  curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
    | $SUDO gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
  log "Adding repo list for ${distribution}..."
  curl -fsSL https://nvidia.github.io/libnvidia-container/${distribution}/libnvidia-container.list \
    | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#' \
    | $SUDO tee "$list" >/dev/null
}

install_toolkit() {
  log "Installing nvidia-container-toolkit (via apt)..."
  $SUDO apt-get update
  $SUDO apt-get install -y nvidia-container-toolkit
}

configure_docker() {
  if ! command -v nvidia-ctk >/dev/null 2>&1; then
    log "nvidia-ctk not found after install; aborting runtime configuration."
    return 1
  fi
  log "Configuring Docker runtime for NVIDIA..."
  $SUDO nvidia-ctk runtime configure --runtime=docker
  log "Restarting Docker..."
  if command -v systemctl >/dev/null 2>&1; then
    $SUDO systemctl restart docker
  else
    $SUDO service docker restart
  fi
}

test_gpu() {
  if [ "${RUN_NVIDIA_TEST:-0}" != "1" ]; then
    log "Skipping GPU test (set RUN_NVIDIA_TEST=1 to enable)."
    return
  fi
  log "Running test container (docker run --gpus all ... nvidia-smi)..."
  docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
}

ensure_tools
add_repo
install_toolkit
configure_docker
test_gpu

log "Done. If you want to test inside your container, run: docker exec -it linux-video-encoder nvidia-smi"
