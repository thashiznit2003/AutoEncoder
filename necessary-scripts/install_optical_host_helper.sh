#!/usr/bin/env bash
set -euo pipefail

# Install the host-side optical helper as a systemd service.
# It listens on 0.0.0.0:8767 by default.

SUDO=""
if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  SUDO="sudo"
  if ! command -v sudo >/dev/null 2>&1; then
    echo "[optical-helper] sudo not found; please run as root." >&2
    exit 1
  fi
fi

HELPER_URL="https://raw.githubusercontent.com/thashiznit2003/AutoEncoder/main/necessary-scripts/optical_host_helper.py"
TARGET_DIR="/usr/local/lib/autoencoder"
HELPER_PATH="${TARGET_DIR}/optical_host_helper.py"
SERVICE_PATH="/etc/systemd/system/autoencoder-optical-helper.service"
LISTEN_ADDR="${OPTICAL_HELPER_LISTEN_ADDR:-0.0.0.0}"
LISTEN_PORT="${OPTICAL_HELPER_LISTEN_PORT:-8767}"

echo "[optical-helper] Installing helper to ${HELPER_PATH}"
$SUDO mkdir -p "${TARGET_DIR}"
$SUDO curl -fsSL "${HELPER_URL}" -o "${HELPER_PATH}"
$SUDO chmod 755 "${HELPER_PATH}"

PYTHON_BIN="$(command -v python3 || true)"
if [[ -z "${PYTHON_BIN}" ]]; then
  echo "python3 not found. Please install python3." >&2
  exit 1
fi

echo "[optical-helper] Writing systemd service ${SERVICE_PATH}"
$SUDO tee "${SERVICE_PATH}" >/dev/null <<EOF
[Unit]
Description=AutoEncoder Optical Host Helper
After=network.target

[Service]
Type=simple
ExecStart=${PYTHON_BIN} ${HELPER_PATH} --listen ${LISTEN_ADDR} --port ${LISTEN_PORT}
Restart=on-failure
User=root

[Install]
WantedBy=multi-user.target
EOF

echo "[optical-helper] Reloading and enabling service"
$SUDO systemctl daemon-reload
$SUDO systemctl enable --now autoencoder-optical-helper.service
$SUDO systemctl status --no-pager autoencoder-optical-helper.service || true

echo "[optical-helper] Done. Helper listening on ${LISTEN_ADDR}:${LISTEN_PORT}"
