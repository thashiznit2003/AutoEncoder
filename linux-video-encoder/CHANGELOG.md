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

## 1.0.3 - 2025-12-04
- NVIDIA toolkit prompt moved to the end of the installer; if selected, installs via the bundled helper after the stack is up and restarts the stack so Docker picks up the NVIDIA runtime.

## 1.0.4 - 2025-12-04
- Installer now optionally sets up Samba shares for lv_file and output (prompts for yes/no and SMB username/password; installs samba if missing) before the NVIDIA prompt.

## 1.0.5 - 2025-12-04
- Renamed Samba share to `input` (from `lv_file`) across installer/scripts; optional Samba setup now provisions `input` and `output`.
- Added `scripts/update_samba_shares.sh` to migrate existing hosts (removes legacy `lv_file`, prompts for SMB user/password).

## 1.0.6 - 2025-12-04
- Installer now prints the detected host IP (best effort) for the UI URL after the stack starts.

## 1.1.0 - 2025-12-04
- Added optional SMB browser panel (connect with URL/user/pass, browse mounts, queue files) before Logs.
- Backend supports SMB mount/list/unmount/queue via new APIs; manual queued files are processed by the main loop.
- Docker image now includes cifs-utils; SMB mount root at /mnt/smb tracked via StatusTracker.

## 1.1.1 - 2025-12-04
- SMB queue now copies the selected file into `/mnt/input` (preserves the source on the SMB share) and queues the local copy for encoding.

## 1.1.2 - 2025-12-04
- Encoding now runs one file at a time (FIFO), ignoring configured max_threads to avoid concurrent encodes.

## 1.1.3 - 2025-12-04
- Active list now shows queued jobs; jobs start as `queued` then move to `running`.
- Manual stop marks jobs as `canceled` and adds a Clear Canceled button in Recent Jobs; badges added for queued/canceled.

## 1.1.4 - 2025-12-04
- Fix: queued jobs now retain their eta/progress keys in snapshots (ensuring Active Encodes shows queued items reliably).

## 1.1.5 - 2025-12-04
- Stop API now honors delete_source and removes the source file when cancellation requests deletion.

## 1.1.6 - 2025-12-04
- Pre-register queued files into Active with a queued state and destination hint so they show up immediately while waiting.

## 1.1.7 - 2025-12-04
- Prevent fallback/success entries after user cancellation; honor delete-source during stop; queued pre-registration avoids duplicates.

## 1.1.8 - 2025-12-04
- SMB mount normalization now escapes spaces (`\040`) so shares/paths with multiple spaces connect correctly.

## 1.1.9 - 2025-12-04
- SMB URL normalization rolled back to avoid breaking mounts with spaces (subprocess arg list handles spaces without escaping).

## 1.2.0 - 2025-12-04
- UI polish with icons/gradients/panel styling while keeping layout; badges updated for queued/canceled; header branding tweaked.

## 1.2.1 - 2025-12-04
- Logs copy button now falls back to a hidden textarea when `navigator.clipboard` is unavailable.

## 1.2.2 - 2025-12-04
- Scanner now skips system paths (`/linux-video-encoder/src`, `/mnt/auto_media`) and avoids auto-mounting common system block devices (sd*/nvme*/vd*/dm*), reducing noisy mounts like /dev/sda1.

## 1.2.3 - 2025-12-04
- Added recommendations.txt to track future feature ideas (queue controls, presets, SMB staging, filters, MakeMKV options, etc.).

## 1.3.0 - 2025-12-04
- UI/Backend: HandBrake presets (save/load/delete) persisted in config; UI controls added.
- Audio/Subtitles: New options to include all audio tracks and copy/burn subtitles (none/copy-all/burn forced).
- Version bumped to 1.3.0.

## 1.3.1 - 2025-12-04
- Low-bitrate guard: jobs with source bitrate below target now require user confirmation (Proceed/Cancel) in Active; cancel stops without success entry.

## 1.3.2 - 2025-12-04
- Confirmation loop fix: proceeding marks the job as allowed (no repeat warning) and resumes queue; cancel clears confirm flags.
