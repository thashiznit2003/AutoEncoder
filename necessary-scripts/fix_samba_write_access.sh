#!/usr/bin/env bash
set -euo pipefail

# Ensure Samba shares are writable for the specified user.
# Usage: curl -fsSL https://raw.githubusercontent.com/thashiznit2003/AutoEncoder/main/necessary-scripts/fix_samba_write_access.sh -o /tmp/fix_samba_write_access.sh && sudo bash /tmp/fix_samba_write_access.sh

SUDO=""
if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  SUDO="sudo"
fi

SMB_CONF="/etc/samba/smb.conf"
BASE_DIR="/linux-video-encoder/AutoEncoder/linux-video-encoder"
BACKUP_SUFFIX="$(date +%Y%m%d-%H%M%S)"

SHARES=(
  "input:$BASE_DIR/File"
  "output:$BASE_DIR/Output"
  "smbstaging:$BASE_DIR/SMBStaging"
  "usbstaging:$BASE_DIR/USBStaging"
  "ripped:$BASE_DIR/Ripped"
)

log() { printf '[smb-fix] %s\n' "$*"; }

if ! command -v smbd >/dev/null 2>&1; then
  log "Installing Samba..."
  $SUDO apt-get update
  $SUDO apt-get install -y samba samba-common
fi

printf "Enter Samba username to grant write access: "
read -r SMB_USER
if [ -z "${SMB_USER:-}" ]; then
  log "No username provided; aborting."
  exit 1
fi

printf "Enter Samba password for %s: " "$SMB_USER"
read -rs SMB_PASS
printf "\n"
if [ -z "${SMB_PASS:-}" ]; then
  log "No password provided; aborting."
  exit 1
fi

if ! id -u "$SMB_USER" >/dev/null 2>&1; then
  log "Creating local user $SMB_USER..."
  $SUDO useradd -m "$SMB_USER"
fi

log "Setting Samba password for $SMB_USER..."
printf "%s\n%s\n" "$SMB_PASS" "$SMB_PASS" | $SUDO smbpasswd -a "$SMB_USER" -s

log "Preparing share directories..."
for entry in "${SHARES[@]}"; do
  share_path="${entry#*:}"
  $SUDO mkdir -p "$share_path"
  $SUDO chown -R "$SMB_USER":"$SMB_USER" "$share_path"
  $SUDO chmod -R 2775 "$share_path"
done

log "Backing up $SMB_CONF to $SMB_CONF.bak.$BACKUP_SUFFIX"
if [ -f "$SMB_CONF" ]; then
  $SUDO cp "$SMB_CONF" "$SMB_CONF.bak.$BACKUP_SUFFIX"
fi

tmp_conf="$(mktemp)"
if [ -f "$SMB_CONF" ]; then
  cat "$SMB_CONF" > "$tmp_conf"
fi

for entry in "${SHARES[@]}"; do
  share_name="${entry%%:*}"
  $SUDO sed -i "/^\\[$share_name\\]/,/^\\[/d" "$tmp_conf"
done

for entry in "${SHARES[@]}"; do
  share_name="${entry%%:*}"
  share_path="${entry#*:}"
  cat >> "$tmp_conf" <<EOF

[$share_name]
   path = $share_path
   browseable = yes
   read only = no
   writable = yes
   guest ok = no
   valid users = $SMB_USER
   force user = $SMB_USER
   force group = $SMB_USER
   create mask = 0664
   directory mask = 2775
   inherit permissions = yes
EOF
done

cat "$tmp_conf" | $SUDO tee "$SMB_CONF" >/dev/null
rm -f "$tmp_conf"

log "Restarting Samba services..."
$SUDO systemctl restart smbd nmbd || $SUDO systemctl restart smbd || true

log "Done. Shares are writable for user $SMB_USER."
