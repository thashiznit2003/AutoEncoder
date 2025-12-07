#!/usr/bin/env bash
set -euo pipefail

# Install the host-side USB helper as a systemd service.
# It listens on 127.0.0.1:8765 and mounts to the repo USB path by default.

HELPER_URL="https://raw.githubusercontent.com/thashiznit2003/AutoEncoder/main/linux-video-encoder/scripts/usb_host_helper.py"
TARGET_DIR="/usr/local/lib/autoencoder"
HELPER_PATH="${TARGET_DIR}/usb_host_helper.py"
SERVICE_PATH="/etc/systemd/system/autoencoder-usb-helper.service"
LISTEN_ADDR="${HELPER_LISTEN_ADDR:-0.0.0.0}"
LISTEN_PORT="${HELPER_LISTEN_PORT:-8765}"
MOUNTPOINT="${HELPER_MOUNTPOINT:-/linux-video-encoder/AutoEncoder/linux-video-encoder/USB}"

echo "[usb-helper] Installing helper to ${HELPER_PATH}"
sudo mkdir -p "${TARGET_DIR}"
sudo curl -fsSL "${HELPER_URL}" -o "${HELPER_PATH}"
sudo chmod 755 "${HELPER_PATH}"

PYTHON_BIN="$(command -v python3 || true)"
if [[ -z "${PYTHON_BIN}" ]]; then
  echo "python3 not found. Please install python3." >&2
  exit 1
fi

echo "[usb-helper] Writing systemd service ${SERVICE_PATH}"
sudo tee "${SERVICE_PATH}" >/dev/null <<EOF
[Unit]
Description=AutoEncoder USB Host Helper
After=network.target

[Service]
Type=simple
ExecStart=${PYTHON_BIN} ${HELPER_PATH} --listen ${LISTEN_ADDR} --port ${LISTEN_PORT} --mountpoint ${MOUNTPOINT}
Restart=on-failure
User=root

[Install]
WantedBy=multi-user.target
EOF

echo "[usb-helper] Reloading and enabling service"
sudo systemctl daemon-reload
sudo systemctl enable --now autoencoder-usb-helper.service
sudo systemctl status --no-pager autoencoder-usb-helper.service || true

echo "[usb-helper] Done. Helper listening on ${LISTEN_ADDR}:${LISTEN_PORT}"
