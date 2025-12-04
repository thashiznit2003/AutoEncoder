#!/usr/bin/env bash
set -euo pipefail

# This script reconfigures Samba shares to use "input" and "output" and removes the legacy "lv_file" share.
# It will prompt for Samba username and password, install samba if missing, and restart smbd/nmbd.
# Usage: curl -fsSL https://raw.githubusercontent.com/thashiznit2003/AutoEncoder/main/linux-video-encoder/scripts/update_samba_shares.sh -o /tmp/update_samba_shares.sh && sudo bash /tmp/update_samba_shares.sh

SUDO=""
if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  SUDO="sudo"
fi

log() { printf '[smb-update] %s\n' "$*"; }

FILE_SHARE_PATH="/linux-video-encoder/AutoEncoder/linux-video-encoder/File"
OUTPUT_SHARE_PATH="/linux-video-encoder/AutoEncoder/linux-video-encoder/Output"

prompt_user_pass() {
  printf "Enter Samba username (will be created if missing): "
  read -r SMB_USER
  if [ -z "${SMB_USER:-}" ]; then
    log "No Samba user provided; aborting."
    exit 1
  fi
  printf "Enter Samba password for %s: " "$SMB_USER"
  read -rs SMB_PASS
  printf "\n"
  if [ -z "${SMB_PASS:-}" ]; then
    log "No Samba password provided; aborting."
    exit 1
  fi
}

install_samba() {
  if ! command -v smbd >/dev/null 2>&1; then
    log "Installing Samba..."
    $SUDO apt-get update
    $SUDO apt-get install -y samba samba-common
  fi
}

ensure_user() {
  if ! id -u "$SMB_USER" >/dev/null 2>&1; then
    log "Creating system user $SMB_USER..."
    $SUDO useradd -m "$SMB_USER"
  fi
  log "Setting Samba password for $SMB_USER..."
  printf "%s\n%s\n" "$SMB_PASS" "$SMB_PASS" | $SUDO smbpasswd -a "$SMB_USER" -s
}

configure_shares() {
  log "Preparing share directories..."
  $SUDO mkdir -p "$FILE_SHARE_PATH" "$OUTPUT_SHARE_PATH"
  $SUDO chown -R "$SMB_USER":"$SMB_USER" "$FILE_SHARE_PATH" "$OUTPUT_SHARE_PATH"
  $SUDO chmod -R 775 "$FILE_SHARE_PATH" "$OUTPUT_SHARE_PATH"

  log "Backing up /etc/samba/smb.conf to /etc/samba/smb.conf.bak (once)..."
  if [ ! -f /etc/samba/smb.conf.bak ]; then
    $SUDO cp /etc/samba/smb.conf /etc/samba/smb.conf.bak
  fi

  # Remove legacy and current blocks
  for share in lv_file input output; do
    $SUDO sed -i "/^\[$share\]/,/^\[/d" /etc/samba/smb.conf
  done

  cat <<CONFIG | $SUDO tee -a /etc/samba/smb.conf >/dev/null

[input]
   path = $FILE_SHARE_PATH
   browseable = yes
   read only = no
   guest ok = no
   valid users = $SMB_USER
   force user = $SMB_USER
   create mask = 0664
   directory mask = 0775

[output]
   path = $OUTPUT_SHARE_PATH
   browseable = yes
   read only = no
   guest ok = no
   valid users = $SMB_USER
   force user = $SMB_USER
   create mask = 0664
   directory mask = 0775
CONFIG
}

restart_samba() {
  log "Restarting Samba services..."
  $SUDO systemctl restart smbd nmbd || $SUDO systemctl restart smbd || true
}

main() {
  prompt_user_pass
  install_samba
  ensure_user
  configure_shares
  restart_samba
  log "Done. New shares: input (File) and output (Output). Connect via smb://<host>/input and smb://<host>/output."
}

main "$@"
