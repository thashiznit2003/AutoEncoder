#!/usr/bin/env bash
set -euo pipefail

# Helper to remount the USB stick on the host and restart the container so it sees the fresh mount.
# Usage:
#   DEV=/dev/sdd1 bash refresh_usb_mount.sh
# If DEV is omitted, it defaults to /dev/sdd1 (adjust to your actual device).

DEV="${DEV:-/dev/sdd1}"
MNT="/linux-video-encoder/AutoEncoder/linux-video-encoder/USB"
REPO="/linux-video-encoder/AutoEncoder/linux-video-encoder"

cd "$REPO"
echo "[refresh-usb] Ensuring mountpoint exists..."
sudo mkdir -p "$MNT"

echo "[refresh-usb] Unmounting $MNT (if mounted)..."
sudo umount "$MNT" 2>/dev/null || true

echo "[refresh-usb] Binding mountpoint to itself (for shared propagation)..."
sudo mount --bind "$MNT" "$MNT" 2>/dev/null || true

echo "[refresh-usb] Marking mountpoint shared..."
sudo mount --make-rshared "$MNT" 2>/dev/null || true

echo "[refresh-usb] Mounting $DEV -> $MNT ..."
sudo mount -t exfat -o uid=1000,gid=1000,fmask=0022,dmask=0022,iocharset=utf8 "$DEV" "$MNT"

echo "[refresh-usb] Host view:"
ls -al "$MNT" | head

echo "[refresh-usb] Restarting container..."
docker compose down
docker compose up -d

echo "[refresh-usb] Container view of /mnt/usb:"
docker compose exec autoencoder ls -al /mnt/usb | head

echo "[refresh-usb] Done."
