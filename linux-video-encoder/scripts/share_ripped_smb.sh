#!/usr/bin/env bash
set -euo pipefail

# Share /mnt/ripped over SMB. Prompts for SMB username/password and
# creates/updates a Samba share named [ripped].
#
# Usage: sudo ./share_ripped_smb.sh

SHARE_NAME="ripped"
SHARE_PATH="/mnt/ripped"
SMB_CONF="/etc/samba/smb.conf"
BACKUP_SUFFIX="$(date +%Y%m%d-%H%M%S)"

if [[ $EUID -ne 0 ]]; then
  echo "Please run as root (sudo ./share_ripped_smb.sh)." >&2
  exit 1
fi

if ! command -v smbd >/dev/null 2>&1; then
  echo "Installing Samba..." >&2
  apt-get update -y
  apt-get install -y samba
fi

if [[ ! -d "$SHARE_PATH" ]]; then
  echo "Creating $SHARE_PATH ..." >&2
  mkdir -p "$SHARE_PATH"
  chown root:root "$SHARE_PATH"
  chmod 0775 "$SHARE_PATH"
fi

read -r -p "SMB username to create/use: " SMB_USER
if [[ -z "$SMB_USER" ]]; then
  echo "Username required." >&2
  exit 1
fi

# Ensure a local user exists for Samba auth (no shell, no home).
if ! id "$SMB_USER" >/dev/null 2>&1; then
  useradd -M -s /usr/sbin/nologin "$SMB_USER"
fi

echo "Set SMB password for $SMB_USER:"
if ! smbpasswd -a "$SMB_USER"; then
  echo "Failed to set SMB password." >&2
  exit 1
fi

if [[ -f "$SMB_CONF" ]]; then
  cp "$SMB_CONF" "$SMB_CONF.bak.$BACKUP_SUFFIX"
  echo "Backed up smb.conf to $SMB_CONF.bak.$BACKUP_SUFFIX"
fi

# Append/replace the share definition.
tmp_conf="$(mktemp)"
if grep -q "^\[$SHARE_NAME\]" "$SMB_CONF"; then
  # Remove existing block for a clean replace.
  awk '
    BEGIN {skip=0}
    /^\['"$SHARE_NAME"'\]/ {skip=1}
    skip && /^\[/ && $0 !~ /^\['"$SHARE_NAME"'\]/ {skip=0}
    !skip {print}
  ' "$SMB_CONF" > "$tmp_conf"
else
  cat "$SMB_CONF" > "$tmp_conf"
fi

cat >> "$tmp_conf" <<EOF

[$SHARE_NAME]
   path = $SHARE_PATH
   browseable = yes
   read only = no
   guest ok = no
   valid users = $SMB_USER
   create mask = 0664
   directory mask = 0775
EOF

cat "$tmp_conf" > "$SMB_CONF"
rm -f "$tmp_conf"

systemctl restart smbd nmbd || systemctl restart smbd || true

echo
echo "SMB share [$SHARE_NAME] is configured for $SHARE_PATH"
echo "Access using SMB credentials: $SMB_USER (password you entered)."
