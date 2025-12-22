#!/usr/bin/env bash
set -euo pipefail

# This script installs Samba and shares the app's File directory over SMB.
# Share path: /linux-video-encoder/AutoEncoder/linux-video-encoder/File
# Share name: input
# SMB user: joe (must exist on the host)

SHARE_PATH="/linux-video-encoder/AutoEncoder/linux-video-encoder/File"
SHARE_NAME="input"
SMB_USER="joe"

log() { printf '[smb-setup] %s\n' "$*"; }

log "Updating apt and installing Samba..."
sudo apt-get update
sudo apt-get install -y samba samba-common

log "Ensuring share directory exists with correct ownership..."
sudo mkdir -p "$SHARE_PATH"
sudo chown -R "$SMB_USER":"$SMB_USER" "$SHARE_PATH"
sudo chmod -R 775 "$SHARE_PATH"

if [ ! -f /etc/samba/smb.conf.bak ]; then
  log "Backing up /etc/samba/smb.conf to smb.conf.bak"
  sudo cp /etc/samba/smb.conf /etc/samba/smb.conf.bak
fi

log "Updating smb.conf with share [$SHARE_NAME] -> $SHARE_PATH"
# Remove existing block if present (and legacy lv_file)
sudo sed -i "/^\[$SHARE_NAME\]/,/^\[/d" /etc/samba/smb.conf
sudo sed -i "/^\[lv_file\]/,/^\[/d" /etc/samba/smb.conf

cat <<CONFIG | sudo tee -a /etc/samba/smb.conf >/dev/null

[$SHARE_NAME]
   path = $SHARE_PATH
   browseable = yes
   read only = no
   guest ok = no
   valid users = $SMB_USER
   force user = $SMB_USER
   create mask = 0664
   directory mask = 0775
CONFIG

log "Set/confirm Samba password for user $SMB_USER (will prompt)..."
sudo smbpasswd -a "$SMB_USER"

log "Restarting Samba services..."
sudo systemctl restart smbd nmbd || sudo systemctl restart smbd

log "Done. Connect from your Mac: smb://<ubuntu-host-ip>/$SHARE_NAME (user: $SMB_USER)."
