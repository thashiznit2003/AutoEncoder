# Changelog

## 1.0.0 - 2025-12-04
- Stable release of Linux Video Encoder with web UI (active encodes, recent jobs, logs, metrics, HandBrake/MakeMKV settings).
- Improved progress/ETA parsing for HandBrake output; Stop button wired to active job keys.
- Scanner avoids /mnt/output, temp “._*” files, and system paths; auto-mounts removable media with exfat support.
- Output naming reuses source names with collision suffixes; source is deleted after successful encode; Blu-ray ripping via MakeMKV supported.
- Docker Compose binds config/media dirs, runs privileged with optical devices and NVIDIA runtime; config persisted via /api/config.

## 1.0.1 - 2025-12-04
- Added Blu-ray passthrough notes for Proxmox: require real drive exposure (no virtual QEMU CD), recommend ASM1166 HBA, and documented IOMMU/hostpci steps.

## 1.0.2 - 2025-12-04
- Installer now prompts to install the NVIDIA Container Toolkit and runs the bundled pinned helper when accepted (avoids failing stock apt flow).
