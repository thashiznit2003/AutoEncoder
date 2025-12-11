# Changelog

## 1.24.43 - 2025-12-12
- MakeMKV disc info now parses title details (duration/chapters/tracks) and returns a formatted summary alongside the raw log.
- Settings UI shows the formatted disc summary (and raw log) when refreshing disc info.
- Version bumped to 1.24.43.

## 1.24.44 - 2025-12-12
- MakeMKV “Refresh disc info” now persists fetched output (including errors) into status so the UI stops clearing to “No disc info.”
- Added fallback text when makemkvcon returns no stdout/stderr to surface something in the panel.
- Version bumped to 1.24.44.

## 1.24.45 - 2025-12-12
- Hardened MakeMKV info parsing: guard against empty/partial output so errors surface instead of throwing “list index out of range.”
- API now wraps parse errors and returns them in the payload so the UI can display the failure text.
- Version bumped to 1.24.45.

## 1.24.46 - 2025-12-12
- Disc info panel now shows a concise summary only (no raw log) and filters to the main/long titles.
- MakeMKV parser aggregates audio/subtitle languages, video stats, and trims noisy tracks so “Refresh disc info” isn’t overwhelming.
- Version bumped to 1.24.46.

## 1.24.35 - 2025-12-08
- Audio offset now applied via a pre-ffmpeg shift when a single file is queued (HandBrake then encodes the shifted temp); temporary file is cleaned up.
- Version bumped to 1.24.35.

## 1.24.36 - 2025-12-11
- Manual MakeMKV rip requests now run immediately even when no Blu-ray files are in the scan (detects disc, runs rip, and queues the output).
- Version bumped to 1.24.36.

## 1.24.37 - 2025-12-11
- MakeMKV rip now passes language filters with the correct flags (`--alang/--slang`) instead of the unsupported `--audio` switch.
- Version bumped to 1.24.37.

## 1.24.38 - 2025-12-11
- Removed MakeMKV language selector flags (unsupported in this build) to prevent rip failures; rips now run without language switches.
- Version bumped to 1.24.38.

## 1.24.39 - 2025-12-11
- MakeMKV rips now run in robot mode with progress streaming (`-r --progress=-same`) to avoid UI hangs/prompts and mirror the working CLI command.
- Ripping is now tracked in Active Encodes with a "ripping" state, progress updates, and badges; when ripping finishes, HandBrake picks up the queued MKV as before.
- Version bumped to 1.24.39.

## 1.24.40 - 2025-12-11
- MakeMKV “Refresh disc info” now invokes makemkvcon info, stores disc info in status, and returns the raw output so the UI panel can display it.
- Version bumped to 1.24.40.

## 1.24.41 - 2025-12-11
- MakeMKV disc info endpoint now also returns a concise summary (drive/label/title count) alongside raw logs for cleaner display.
- Version bumped to 1.24.41.

## 1.24.42 - 2025-12-11
- Added a Copy Disc Info button in MakeMKV settings to quickly copy the fetched disc info/summary.
- Version bumped to 1.24.42.

## 1.24.34 - 2025-12-08
- Fixed audio offset flag to use HandBrakeCLI's supported `--audio-delay` so offsets apply correctly.
- Version bumped to 1.24.34.

## 1.24.33 - 2025-12-08
- Guard against false-success encodes: if HandBrake exits 0 but the output file is missing/empty, treat as failure so it doesn’t silently pass.
- Version bumped to 1.24.33.

## 1.24.32 - 2025-12-08
- Added HandBrake audio offset (ms) control in Settings; applies only when a single file is queued, wired into HandBrakeCLI via --audio-offset.
- Version bumped to 1.24.32.

## 1.24.31 - 2025-12-08
- SMB Browser header now uses an inline 8-bit Mario-style icon (custom pixel SVG).
- Version bumped to 1.24.31.

## 1.24.30 - 2025-12-08
- Tightened Network metric text spacing so arrows stay on one line with their values.
- Version bumped to 1.24.30.

## 1.24.29 - 2025-12-08
- GPU metric splits percent and memory onto separate lines, Output drops the word "free", and Network uses arrow indicators (down/up) instead of rx/tx.
- Version bumped to 1.24.29.

## 1.24.28 - 2025-12-08
- Matched USB Controls icon background/shine to the other metric icons.
- Version bumped to 1.24.28.

## 1.24.27 - 2025-12-08
- Refined the USB Controls icon to resemble a USB-A cable end.
- Version bumped to 1.24.27.

## 1.24.26 - 2025-12-08
- Replaced System Metrics emoji icons with inline SVGs for CPU, GPU, Memory, Disk, Output, Network, and USB controls.
- Version bumped to 1.24.26.

## 1.24.25 - 2025-12-08
- Updated System Metrics labels/icons: CPU/GPU/Memory/Disk/Output/Network renamed as requested and icons swapped (USB uses plug icon).
- Version bumped to 1.24.25.

## 1.24.24 - 2025-12-08
- Further reduced System Metrics card padding/height (non-USB) and grid gap to eliminate scroll and keep USB Controls in view.
- Version bumped to 1.24.24.

## 1.24.23 - 2025-12-08
- Tightened System Metrics card padding/height (non-USB) to reduce vertical whitespace so USB controls stay visible without scrolling.
- Version bumped to 1.24.23.

## 1.24.22 - 2025-12-08
- Restyled System Metrics cards (excluding USB Controls): softer gradients, larger icons, and cleaner spacing while keeping values compact.
- Version bumped to 1.24.22.

## 1.24.21 - 2025-12-08
- System Metrics cards doubled in height with enlarged icons and titles (value text unchanged) for clearer KPI-style sizing.
- Version bumped to 1.24.21.

## 1.24.20 - 2025-12-08
- USB Controls card tightened: buttons stay on one line, shrink text/padding, status sits on its own line underneath.
- Version bumped to 1.24.20.

## 1.24.19 - 2025-12-08
- System Metrics now shows Disk and Memory in GB; GPU label trimmed (drops “util”); USB controls buttons auto-shrink to fit.
- Version bumped to 1.24.19.

## 1.24.18 - 2025-12-08
- Halved System Metrics card dimensions again (smaller padding, icons, and text) for the skinnier KPI-style look.
- Version bumped to 1.24.18.

## 1.24.17 - 2025-12-08
- Further shrunk System Metrics cards (half-size icons/text/spacing) to reduce unused space; text still wraps within cards.
- Version bumped to 1.24.17.

## 1.24.16 - 2025-12-08
- Redesigned System Metrics cards to a compact icon+value/label layout (skinnier cards, tight padding, wrapped text) matching the requested look.
- Version bumped to 1.24.16.

## 1.24.15 - 2025-12-08
- Further reduced System Metrics card height (tighter padding/line-height/gap) while keeping text/icons the same size; wrapping retained.
- Version bumped to 1.24.15.

## 1.24.14 - 2025-12-08
- Further reduced System Metrics card height (tighter padding/line-height) while keeping text/icons the same size; wrapping retained.
- Version bumped to 1.24.14.

## 1.24.13 - 2025-12-08
- System Metrics cards shrunk ~50% (tighter padding/grid) while keeping text/icons same size; metric text now wraps within the card.
- Version bumped to 1.24.13.

## 1.24.12 - 2025-12-08
- Preserve USB status color/text when re-rendering the System Metrics grid to avoid color flashing.
- Version bumped to 1.24.12.

## 1.24.11 - 2025-12-08
- USB card now lives inside the System Metrics grid, full-width, alongside other metric cards (Disk/Output FS/Net), with buttons/status embedded.
- Version bumped to 1.24.11.

## 1.24.10 - 2025-12-08
- Moved USB buttons/status back inside the System Metrics panel (single card) instead of a standalone panel.
- Version bumped to 1.24.10.

## 1.24.9 - 2025-12-08
- Fixed indentation error in USB helper logging path that caused container restart loop.
- Version bumped to 1.24.9.

## 1.24.8 - 2025-12-08
- Installer now installs the USB host helper service before NVIDIA toolkit setup; helper uses repo USB mount by default.
- Version bumped to 1.24.8.

## 1.24.7 - 2025-12-08
- USB helper mount/lsblk summaries now log to the Logs panel instead of Status Messages; status still updates USB state text.
- Version bumped to 1.24.7.

## 1.24.6 - 2025-12-08
- Added a dedicated “USB Metrics” card in System Metrics spanning full width, housing Refresh/Force Remount/Eject buttons and status text.
- Version bumped to 1.24.6.

## 1.24.5 - 2025-12-07
- USB helper now records video_count after mount and returns it to the UI; force-remount skips partitions with zero video files.
- Refresh/force-remount status messages include the number of video files detected.
- Added /usb/eject endpoint to helper; UI eject stays host-driven.
- Version bumped to 1.24.5.

## 1.24.4 - 2025-12-07
- Added UI “Eject USB” button in System Metrics (host-helper driven) to cleanly unmount before swapping drives.
- Host helper unmounts both the target mount and `/mnt/usb` before mounting to avoid stacked mounts; Web UI passes helper mountpoint consistently.
- Version bumped to 1.24.4.

## 1.24.3 - 2025-12-07
- USB helper now unmounts both the host USB target and `/mnt/usb` before mounting to avoid stacked/broken mounts, and iterates helper mountpoint explicitly.
- Web UI refresh/force-remount now targets the host mount path (not the container bind) and shares the helper mountpoint, reducing stale mount mismatches.
- Version bumped to 1.24.3.

## 1.24.2 - 2025-12-07
- Refresh endpoint now iterates all removable/USB candidates per attempt and requires actual entries (beyond . and ..) before succeeding; returns detailed attempts when it fails to find files.

## 1.24.1 - 2025-12-07
- Helper now bind-mounts the USB mountpoint and marks it shared to improve propagation into the container when re-mounted.

## 1.24.0 - 2025-12-07
- Force remount now iterates all USB candidates per attempt and always returns attempts even on error (200 with ok=false), avoiding 500s; UI now reads HTTP error bodies to surface helper details in Events.
- Version bump to 1.24.0.

## 1.23.9 - 2025-12-07
- Force remount endpoint now iterates all removable/USB candidates per attempt, recording them, and only succeeds when a mount yields real entries; returns detailed attempts when failing.
- Version bumped to 1.23.9.

## 1.23.8 - 2025-12-07
- Helper now iterates over all removable/USB partitions (skipping system mounts) and uses the first candidate, recording candidates in response; avoids single-partition assumptions.
- Version bumped to 1.23.8.

## 1.23.7 - 2025-12-07
- Scanner now keeps /mnt/usb in scan list when mounted even if a read error occurs, only dropping it when not mounted; still logs USB errors and immediate scans on ready.
- Version bumped to 1.23.7.

## 1.23.6 - 2025-12-07
- USB helper mount flow now unmounts first, retries mounts, runs fsck.exfat when needed, and revalidates readability to recover from transient I/O errors automatically.
- Version bumped to 1.23.6.

## 1.23.5 - 2025-12-07
- USB helper now ignores partitions already mounted to system paths (/, /boot, /boot/efi) and prefers removable/USB partitions that are unmounted or at the target mountpoint, reducing mis-detection of the wrong device.
- Version bumped to 1.23.5.

## 1.23.4 - 2025-12-07
- USB force remount endpoint now guards logger initialization to avoid exceptions when helper returns errors (e.g., 404 from outdated helper); version bumped.

## 1.23.3 - 2025-12-07
- Hooked up USB buttons in the main template to the correct endpoints (refresh/force remount) so clicks execute and log attempts.
- Version bumped to 1.23.3.

## 1.23.2 - 2025-12-07
- Fixed template so USB controls (Force Remount + Refresh USB + status) appear in the System Metrics panel.
- Version bumped to 1.23.2.

## 1.23.1 - 2025-12-07
- Moved Force Remount/Refresh USB buttons into the System Metrics panel alongside USB status for easier access.
- Version bumped to 1.23.1.

## 1.23.0 - 2025-12-07
- UI: added a "Force Remount" button above Refresh USB that asks the host helper to unmount/rescan/remount multiple times until it finds real files, logging attempts to the Events panel.
- API: new `/api/usb/force_remount` endpoint.
- Helper: new `/usb/force_remount` that unmounts, rescans block devices, retries mount with/without fstype, and stops when non-dot entries are seen (or after retry budget).
- Version bump to 1.23.0.

## 1.22.6 - 2025-12-07
- Scanner now skips /mnt/usb when USB status is missing/error and triggers an immediate (near-zero delay) scan when USB transitions to ready, while still requiring stable files before queueing.
- Version bump to 1.22.6.

## 1.22.5 - 2025-12-07
- Host helper mount routine now always unmounts first, retries with/without fstype, rescans block devices, and retries once more to avoid transient mount failures; version bumped.

## 1.22.4 - 2025-12-07
- Host helper now defaults to listen on 0.0.0.0 (configurable via HELPER_LISTEN_ADDR/PORT/MOUNTPOINT) so the container can always reach it; installer updated accordingly.
- Docs/version updated to 1.22.4.

## 1.22.3 - 2025-12-07
- Fix lsblk invocation flags (use -nP, avoid raw+pairs conflict) in both helper and container refresh so parsing always works.
- Version bump to 1.22.3.

## 1.22.2 - 2025-12-07
- Host helper now auto-rescans block devices (udevadm/partprobe) and retries lsblk up to 3 times before giving up, then returns all attempts in the response.
- UI still surfaces helper attempts in Status Messages.
- Version bump to 1.22.2.

## 1.22.1 - 2025-12-07
- USB refresh now forwards host-helper lsblk/mount info into the app Events panel so users see what the helper tried (success/failure) directly in the UI.
- Version bump to 1.22.1.

## 1.22.0 - 2025-12-07
- Host USB helper service: new `usb_host_helper.py` + `install_usb_host_helper.sh` installs a host-side HTTP helper (systemd) that performs USB refresh/mount outside the container.
- Container USB refresh now calls the host helper first via `host.docker.internal:8765` (compose adds host-gateway); falls back to in-container logic if unreachable.
- Compose: added host-gateway extra_hosts so the container can reach the helper.
- Docs/version updated to 1.22.0 with helper install instructions.

## 1.21.25 - 2025-12-07
- USB refresh: handle empty lsblk output by retrying without `-P`, emit clear error/status when nothing is returned, and continue logging attempts.
- Version bump to 1.21.25.

## 1.21.24 - 2025-12-07
- USB refresh parsing made resilient: uses key/value lsblk output and inherits parent-disk transport so USB HDDs/flash drives that report `rm=0` are still mounted; keeps logging lsblk output and mount attempts.
- Version bump to 1.21.24.

## 1.21.23 - 2025-12-07
- UI: USB Status panel now has a working Refresh USB button that issues the `/api/usb/refresh` POST, shows progress, and triggers a status reload.
- Frontend: fetch helper accepts request options (POST) so refresh and future actions can call APIs without custom wrappers.
- Version bump to 1.21.23.

## 1.21.22 - 2025-12-06
- USB refresh: explicitly treat USB-transport partitions (even with rm=0) as mount candidates; logs still show lsblk output and mount attempts.

## 1.21.21 - 2025-12-06
- USB refresh: include transport in lsblk parsing and accept USB devices even if they report non-removable (rm=0); logs still show lsblk output and mount attempts.

## 1.21.20 - 2025-12-06
- UI: fetch helper now supports POST options so Refresh USB calls reach the backend; keeps USB refresh button functional.

## 1.21.19 - 2025-12-06
- USB refresh: added lsblk output and logging of mount attempts/errors to app logs for visibility when clicking Refresh USB.

## 1.21.18 - 2025-12-06
- USB refresh now logs attempts/errors, makes the mountpoint shared even when no device is present, scans removable partitions, and retries mounts (with/without fstype) before reporting failure. Logged output is visible in app logs/Status Messages.

## 1.21.17 - 2025-12-06
- USB refresh endpoint now scans removable partitions, sets mountpoint shared, unmounts/retries mount (with fs-type detection) up to 2 attempts and reports errors; improved consistency for hotplug/refresh.

## 1.21.16 - 2025-12-06
- UI: added a "Refresh USB" button in System Metrics that calls a backend refresh endpoint.
- API: new `/api/usb/refresh` best-effort trigger (calls helper/udevadm if present) and tracks USB status state for the UI.

## 1.21.15 - 2025-12-06
- UI: USB status now lives inside the System Metrics panel (dropped the standalone panel) to save space.

## 1.21.14 - 2025-12-06
- USB automount: make mountpoint shared and retry mount up to 3 times (with fs-type detection) to improve consistency across devices.

## 1.21.13 - 2025-12-06
- UI: USB status panel wired into the main template and refresh loop (shows ready/missing/error and message).

## 1.21.12 - 2025-12-06
- UI: added USB status indicator (ready/missing/error) fed by backend health checks.
- Backend: status API now includes USB status for UI display.

## 1.21.11 - 2025-12-06
- USB: track encoded USB sources (size/mtime) in state and skip staging if already encoded; map staged files back to their origins to prevent re-queueing while the stick remains plugged in.

## 1.21.10 - 2025-12-06
- Scanner: ignore common trash/system dirs (`.Trashes`, `.Spotlight-V100`, `.fseventsd`, `.Trash*`) to avoid re-queuing deleted USB files.

## 1.21.9 - 2025-12-06
- USB automount: detect filesystem type, log detailed mount failures, and retry with auto type before giving up (better visibility in journalctl -t autoencoder-usb).

## 1.21.8 - 2025-12-06
- USB automount: use absolute paths in helper and skip non-block devices to improve reliability when triggered from udev; version bumped.

## 1.21.7 - 2025-12-06
- USB automount: helper now logs attempts/failures, and udev rules also match removable partitions (not just ID_BUS=usb) to better catch devices; version bumped.

## 1.21.6 - 2025-12-06
- USB: added mount/readability health check that posts Status Messages on state change (ready/missing/I/O error) to make hot-plug issues visible.

## 1.21.5 - 2025-12-06
- Bugfix: staged USB files under `/mnt/usb_staging` are now explicitly deleted (plus sidecars) after successful encodes to avoid leftovers.

## 1.21.4 - 2025-12-06
- `setup_usbstaging_share.sh` now always prompts for Samba credentials (ignores env) to avoid accidental reuse of incorrect env vars.

## 1.21.3 - 2025-12-06
- Samba: installer now also shares `USBStaging` (usbstaging) alongside input/output/smbstaging. Added `scripts/setup_usbstaging_share.sh` for on-demand share setup.

## 1.21.2 - 2025-12-06
- USB automount: added `scripts/setup_usb_automount.sh` (udev + helper) to mount any USB partition to `./USB` automatically; installer now runs it. Media dirs ensure `USBStaging` exists.

## 1.21.1 - 2025-12-06
- Config persistence: config now lives in the state volume (`/var/lib/autoencoder/state/config.json`), seeded from repo `config.json` on first run, so UI settings survive pulls/rebuilds.

## 1.21.0 - 2025-12-06
- USB staging: USB-sourced files are copied to `/mnt/usb_staging` (bind-mounted) before encoding so originals stay on the stick; staging copies are removed after success.
- Compose: added `./USBStaging -> /mnt/usb_staging` bind; USB bind remains `rw,rslave`.
- Config/docs: new `usb_staging_dir` option, README/Version updated to 1.21.0.

## 1.20.5 - 2025-12-06
- Compose: USB bind now uses `rslave` propagation so host USB mounts appear inside the container without restarting the stack.

## 1.20.4 - 2025-12-06
- Documentation: README versioning section updated to match 1.20.x (current version, SMB staging/sidecar handling, version bump policy).

## 1.20.3 - 2025-12-06
- Added chat6.txt transition notes (workflow, update commands, feature/security status).

## 1.20.2 - 2025-12-06
- Added low-bitrate auto-proceed/auto-skip status to HandBrake summaries (main and settings), and persisted checkboxes across navigation.

## 1.20.1 - 2025-12-06
- Fix: low-bitrate auto-proceed/skip settings now persist (config update handles the new flags), and checkboxes reflect saved values.

## 1.20.0 - 2025-12-06
- Settings: added “auto-proceed” and “auto-skip” options for low-bitrate detections with saved state.
- Encoding: low-bitrate auto-proceed skips confirmation; auto-skip removes staged files and records an event.

## 1.19.0 - 2025-12-06
- Active Encodes: queued items now show “Queued for” and can be removed (deletes staged files/allowlist) via a Remove button.
- SMB Browser: file list now filters to video and subtitle extensions; mounts remain clickable.

## 1.18.6 - 2025-12-06
- Active Encodes: queued items now show “Queued for:” with the elapsed queue time instead of “Encode elapsed.”

## 1.18.5 - 2025-12-06
- Cleanup staged source + sidecar .srt files after successful encode and drop allowlist entries to avoid blocking future SMB copies.

## 1.18.4 - 2025-12-06
- Fix: SMB queue handler now imports Path so sidecar subtitle staging no longer errors.

## 1.18.3 - 2025-12-06
- Status Messages panel: added buttons to copy the last event or last 10 events to the clipboard (helps when auto-refresh makes manual select/copy difficult).

## 1.18.2 - 2025-12-06
- Canceling a queued/confirm job now deletes the staged file and removes it from the SMB allowlist to avoid leftover files.

## 1.18.1 - 2025-12-06
- SMB queue errors are now surfaced (events + JSON) to avoid silent failures when staging sidecars and videos.

## 1.18.0 - 2025-12-06
- SMB queue now also copies matching sidecar .srt files (immediate or deferred) and allowlists them so external subtitles survive staging cleanup.

## 1.17.0 - 2025-12-06
- External .srt subtitles: when a matching sidecar .srt exists (same stem or stem.lang), it is auto-included in HandBrake encodes and marked default; event logged.

## 1.16.1 - 2025-12-06
- SMB UI: mounts list is now clickable to re-select and browse an existing mount; selection is highlighted.

## 1.16.0 - 2025-12-06
- SMB queue now defers copying when an encode is running or staging is non-empty; pending SMB copies are staged once idle. Active panel shows queued entries. Unmount handling fixed.

## 1.15.8 - 2025-12-06
- SMB staging: queueing now allowlists the destination before copying, and enforcement no longer prunes missing entries to avoid deleting in-progress copies.

## 1.15.7 - 2025-12-06
- SMB mount helper now allows parentheses in paths (removed them from the disallowed character set).

## 1.15.6 - 2025-12-06
- Fixed SMB UNC normalization to avoid double slashes in paths and fixed SMB unmount when mount entries include labels.

## 1.15.5 - 2025-12-06
- SMB mount helper now normalizes paths more strictly and retries with SMB versions 3.0 → 2.1 → 2.0 to avoid mount error(22) defaults.

## 1.15.4 - 2025-12-06
- SMB mount helper now strips trailing slashes from UNC roots and returns sanitized diagnostics (UNC/options, no creds) to help troubleshoot mount error(22) cases.

## 1.15.3 - 2025-12-06
- Fix: SMB mount now imports sys and logs sanitized mount failures instead of returning empty 400s.

## 1.15.2 - 2025-12-04
- Added SMB mount helper with validation and credential-file handling; web app now calls the helper (no shell), and creds are kept out of logs. Staging allowlist unchanged.

## 1.15.1 - 2025-12-04
- Fixed circular import crash by moving SMB allowlist helpers into a dedicated module.

## 1.15.0 - 2025-12-04
- Added SMB staging allowlist: only files copied via the app are permitted in `/mnt/smb_staging`; foreign files are removed, and the allowlist persists in a named volume (`autoencoder_state`).

## 1.14.5 - 2025-12-04
- Added documentation that the UI is intended for LAN/VPN use and should not be exposed directly to the public internet; recommend accessing via a LAN reverse proxy (e.g., Nginx Proxy Manager).

## 1.14.4 - 2025-12-04
- Enlarged the header icon to better fill the top bar.

## 1.14.3 - 2025-12-04
- Swapped header logo to the updated `linux-video-encoder-icon.svg`, baked into the image (assets now copied in Dockerfile; compose bind removed).

## 1.14.2 - 2025-12-04
- Added the new SVG logo to the dashboard and settings headers; static assets are now served from `/assets` and mounted via compose.

## 1.14.1 - 2025-12-04
- Added a lightweight SVG logo (DVD + shrinking file motif) at `assets/logo.svg` for branding use.

## 1.14.0 - 2025-12-04
- Split UI into a main dashboard and a dedicated `/settings` page for HandBrake, MakeMKV, and Authentication panels (Settings link in header).
- Web server now serves templates from `src/templates.py` so the settings layout stays separate from the main status view.

## 1.13.1 - 2025-12-04
- Added chat5.txt transition notes for next chat (summaries, preferences, pending UI split).

## 1.13.0 - 2025-12-04
- Added HTTP Basic auth for UI/API (configurable user/pass) with an Authentication panel to update credentials.

## 1.12.2 - 2025-12-04
- Added copy button for the host MakeMKV update command in the MakeMKV panel.

## 1.12.1 - 2025-12-04
- MakeMKV update check UI now only reports “installed version checked” (drops noisy makemkvcon messages).

## 1.12.0 - 2025-12-04
- MakeMKV panel now shows the installed version, lets you enter the latest version from makemkv.com, and generates a host update command accordingly; update check parses version line instead of dumping full output.

## 1.11.3 - 2025-12-04
- MakeMKV update check now surfaces only the version line (truncates noisy output) for a clearer status message.

## 1.11.2 - 2025-12-04
- Fix: MakeMKV update check now uses a version-bearing info call (avoids unsupported flags) and still surfaces stdout/stderr.

## 1.11.1 - 2025-12-04
- Fix: update check now uses makemkvcon --version (since --update isn’t supported) and UI button label clarified.

## 1.11.0 - 2025-12-04
- MakeMKV update check endpoint/button added (runs makemkvcon --update and surfaces the message in UI).
- Added host-side helper script `scripts/update_makemkv.sh` to rebuild/restart with a chosen MakeMKV version.

## 1.10.4 - 2025-12-04
- MakeMKV registration now strips surrounding quotes from pasted keys to avoid invalid key errors.

## 1.10.3 - 2025-12-04
- MakeMKV registration failure messages now include stderr/stdout and exit code for clearer diagnostics in Status Messages.

## 1.10.2 - 2025-12-04
- MakeMKV registration now always reports failure on non-zero makemkvcon exit (still writes key to settings.conf for persistence), avoiding false-success messages.

## 1.10.1 - 2025-12-04
- MakeMKV registration now also writes the key to settings.conf as a fallback when makemkvcon reg returns an error, and reports the underlying error/warning.

## 1.10.0 - 2025-12-04
- Added MakeMKV registration input/button; backend endpoint calls `makemkvcon reg` and logs success/failure.

## 1.9.4 - 2025-12-04
- Fix: SMB listing/queue now handles labeled mounts correctly so share contents show up again.

## 1.9.3 - 2025-12-04
- SMB mounts now carry a readable label derived from the share path (instead of the UUID) and are displayed accordingly in the UI.

## 1.9.2 - 2025-12-04
- SMB connect now responds to Enter within the SMB form; mount list shows the share name (last path segment) instead of the UUID.
- Status Messages wrap long lines to avoid horizontal scrolling.

## 1.9.1 - 2025-12-04
- SMB browser copies now log as staged and the scanner includes the staging path so staged files are picked up.

## 1.9.0 - 2025-12-04
- Added SMB staging path (default /mnt/smb_staging) for SMB browser copies plus Samba share `smbstaging`; installer now provisions the share and compose mounts ./SMBStaging.
- SMB queue now respects the configurable staging path instead of hardcoding /mnt/input.
- Added helper script `scripts/setup_smbstaging_share.sh` to create the smbstaging share and restart the stack.

## 1.8.3 - 2025-12-04
- MakeMKV Save now posts a “settings saved” event and alert so the change is visible in Status Messages.

## 1.8.2 - 2025-12-04
- Fix: /api/config no longer crashes when HandBrake payload is omitted (guarded missing dict keys).

## 1.8.1 - 2025-12-04
- Fix: resolved an indentation error in autoencoder.py that caused container restart loops.

## 1.8.0 - 2025-12-04
- MakeMKV: added disc detection info fetch, configurable preferred audio/subtitle languages (default eng), commentary exclusion flag, surround preference, and auto-rip toggle.
- UI now shows disc status/info with a manual "Start rip" button when auto-rip is off; rip requests trigger on next scan.
- Rip flow uses preferred language lists when explicit lists are unset.

## 1.7.1 - 2025-12-04
- Clarified in the HandBrake UI that Audio mode overrides the Audio encoder when set.

## 1.7.0 - 2025-12-04
- Added HandBrake "Auto Dolby" audio mode: copy AC3/E-AC3 (all channel counts) and re-encode other codecs to E-AC3 (no upmix for sub-5.1 sources). UI option added alongside existing modes.

## 1.6.0 - 2025-12-04
- HandBrake audio controls expanded: encoder choice (AAC/HE-AAC/Opus/AC3/E-AC3/copy), mixdown, sample rate, DRC, gain, language filter, and track list; all wired into config, presets, and UI.

## 1.5.0 - 2025-12-04
- MakeMKV now supports per-rip title selection plus audio/subtitle language filters; UI fields added for titles and language codes.
- Added option to keep ripped MKVs after encoding (or reuse an existing rip instead of failing).
- Config fields normalized for MakeMKV titles/language/keep flags; rip events include selected options.

## 1.4.3 - 2025-12-04
- Updated chat4.txt with explicit versioning rules (patch/minor/major per user policy).

## 1.4.2 - 2025-12-04
- Added chat4.txt transition doc summarizing app state, preferences, and next steps.

## 1.4.1 - 2025-12-04
- Expanded bitrate ladder to 500–8000 kbps in 500 kbps steps (plus custom).

## 1.4.0 - 2025-12-04
- Added target bitrate options (High/Med/Low/custom) with optional two-pass; when set, overrides RF.
- Presets now include bitrate/two-pass settings; UI fields for bitrate ladder and two-pass.
- Low-bitrate check uses explicit target bitrate when provided.

## 1.3.4 - 2025-12-04
- Proceed now immediately marks jobs as `starting` (instead of queued) after low-bitrate confirmation to make state change visible.

## 1.3.3 - 2025-12-04
- Added interim `starting` state between queued and running to avoid apparent freezes after proceeding from low-bitrate warnings; badge added.

## 1.3.2 - 2025-12-04
- Confirmation loop fix: proceeding marks the job as allowed (no repeat warning) and resumes queue; cancel clears confirm flags.

## 1.3.1 - 2025-12-04
- Low-bitrate guard: jobs with source bitrate below target now require user confirmation (Proceed/Cancel) in Active; cancel stops without success entry.

## 1.3.0 - 2025-12-04
- UI/Backend: HandBrake presets (save/load/delete) persisted in config; UI controls added.
- Audio/Subtitles: New options to include all audio tracks and copy/burn subtitles (none/copy-all/burn forced).
- Version bumped to 1.3.0.

## 1.2.3 - 2025-12-04
- Added recommendations.txt to track future feature ideas (queue controls, presets, SMB staging, filters, MakeMKV options, etc.).

## 1.2.2 - 2025-12-04
- Scanner now skips system paths (`/linux-video-encoder/src`, `/mnt/auto_media`) and avoids auto-mounting common system block devices (sd*/nvme*/vd*/dm*), reducing noisy mounts like /dev/sda1.

## 1.2.1 - 2025-12-04
- Logs copy button now falls back to a hidden textarea when `navigator.clipboard` is unavailable.

## 1.2.0 - 2025-12-04
- UI polish with icons/gradients/panel styling while keeping layout; badges updated for queued/canceled; header branding tweaked.

## 1.1.9 - 2025-12-04
- SMB URL normalization rolled back to avoid breaking mounts with spaces (subprocess arg list handles spaces without escaping).

## 1.1.8 - 2025-12-04
- SMB mount normalization now escapes spaces (`\040`) so shares/paths with multiple spaces connect correctly.

## 1.1.7 - 2025-12-04
- Prevent fallback/success entries after user cancellation; honor delete-source during stop; queued pre-registration avoids duplicates.

## 1.1.6 - 2025-12-04
- Pre-register queued files into Active with a queued state and destination hint so they show up immediately while waiting.

## 1.1.5 - 2025-12-04
- Stop API now honors delete_source and removes the source file when cancellation requests deletion.

## 1.1.4 - 2025-12-04
- Fix: queued jobs now retain their eta/progress keys in snapshots (ensuring Active Encodes shows queued items reliably).

## 1.1.3 - 2025-12-04
- Active list now shows queued jobs; jobs start as `queued` then move to `running`.
- Manual stop marks jobs as `canceled` and adds a Clear Canceled button in Recent Jobs; badges added for queued/canceled.

## 1.1.2 - 2025-12-04
- Encoding now runs one file at a time (FIFO), ignoring configured max_threads to avoid concurrent encodes.

## 1.1.1 - 2025-12-04
- SMB queue now copies the selected file into `/mnt/input` (preserves the source on the SMB share) and queues the local copy for encoding.

## 1.1.0 - 2025-12-04
- Added optional SMB browser panel (connect with URL/user/pass, browse mounts, queue files) before Logs.
- Backend supports SMB mount/list/unmount/queue via new APIs; manual queued files are processed by the main loop.
- Docker image now includes cifs-utils; SMB mount root at /mnt/smb tracked via StatusTracker.

## 1.0.6 - 2025-12-04
- Installer now prints the detected host IP (best effort) for the UI URL after the stack starts.

## 1.0.5 - 2025-12-04
- Renamed Samba share to `input` (from `lv_file`) across installer/scripts; optional Samba setup now provisions `input` and `output`.
- Added `scripts/update_samba_shares.sh` to migrate existing hosts (removes legacy `lv_file`, prompts for SMB user/password).

## 1.0.4 - 2025-12-04
- Installer now optionally sets up Samba shares for lv_file and output (prompts for yes/no and SMB username/password; installs samba if missing) before the NVIDIA prompt.

## 1.0.3 - 2025-12-04
- NVIDIA toolkit prompt moved to the end of the installer; if selected, installs via the bundled helper after the stack is up and restarts the stack so Docker picks up the NVIDIA runtime.

## 1.0.2 - 2025-12-04
- Installer now prompts to install the NVIDIA Container Toolkit and runs the bundled pinned helper when accepted (avoids failing stock apt flow).

## 1.0.1 - 2025-12-04
- Added Blu-ray passthrough notes for Proxmox: require real drive exposure (no virtual QEMU CD), recommend ASM1166 HBA, and documented IOMMU/hostpci steps.

## 1.0.0 - 2025-12-04
- Stable release of Linux Video Encoder with web UI (active encodes, recent jobs, logs, metrics, HandBrake/MakeMKV settings).
- Improved progress/ETA parsing for HandBrake output; Stop button wired to active job keys.
- Scanner avoids /mnt/output, temp “._*” files, and system paths; auto-mounts removable media with exfat support.
- Output naming reuses source names with collision suffixes; source is deleted after successful encode; Blu-ray ripping via MakeMKV supported.
- Docker Compose binds config/media dirs, runs privileged with optical devices and NVIDIA runtime; config persisted via /api/config.
