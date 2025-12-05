from flask import Flask, jsonify, Response, request
import time
import subprocess
import os
from version import VERSION
import uuid
import pathlib
import shutil

SMB_MOUNT_ROOT = pathlib.Path("/mnt/smb")

HTML_PAGE_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Linux Video Encoder v__VERSION__</title>
  <style>
    :root { color-scheme: dark; font-family: "Inter", "Segoe UI", Arial, sans-serif; }
    body { margin: 0; background: radial-gradient(circle at 18% 20%, rgba(59,130,246,0.12), transparent 40%), radial-gradient(circle at 80% 10%, rgba(94,234,212,0.12), transparent 32%), #0b1220; color: #e2e8f0; }
    header { padding: 14px 16px; background: linear-gradient(120deg, #0f172a, #0c1425); border-bottom: 1px solid #1f2937; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 10px 28px rgba(0,0,0,0.35); }
    h1 { font-size: 18px; margin: 0; letter-spacing: 0.3px; display:flex; align-items:center; gap:10px; }
    .logo-dot { width: 10px; height: 10px; border-radius: 50%; background: linear-gradient(135deg,#60a5fa,#a78bfa); box-shadow: 0 0 10px rgba(96,165,250,0.8); }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); grid-auto-rows: minmax(240px, auto); gap: 12px; padding: 12px; }
    .panel { background: linear-gradient(145deg, #111827, #0d1528); border: 1px solid #1f2937; border-radius: 14px; padding: 12px; box-shadow: 0 16px 38px rgba(0,0,0,0.35), inset 0 0 0 1px rgba(255,255,255,0.03); }
    .panel h2 { margin: 0 0 10px 0; font-size: 15px; color: #a5b4fc; letter-spacing: 0.4px; display:flex; align-items:center; gap:8px; }
    form { display: grid; gap: 8px; margin-top: 8px; }
    label { font-size: 12px; color: #cbd5e1; display: grid; gap: 4px; }
    input, select { padding: 9px 11px; border-radius: 10px; border: 1px solid #1f2937; background: #0b1220; color: #e2e8f0; transition: border 0.2s ease, box-shadow 0.2s ease; }
    input:focus, select:focus { outline: none; border-color: #60a5fa; box-shadow: 0 0 0 1px rgba(96,165,250,0.5); }
    button { padding: 9px 12px; border: 0; border-radius: 10px; background: linear-gradient(135deg, #2563eb, #4f46e5); color: #fff; font-weight: 700; cursor: pointer; transition: transform 0.08s ease, box-shadow 0.2s; }
    button:hover { transform: translateY(-1px); box-shadow: 0 8px 20px rgba(79,70,229,0.35); }
    .log { font-family: "SFMono-Regular", Menlo, Consolas, monospace; font-size: 12px; background: #0b1220; border-radius: 12px; padding: 10px; overflow: auto; height: 320px; border: 1px solid #1f2937; white-space: pre-wrap; box-shadow: inset 0 0 0 1px rgba(255,255,255,0.02); }
    .log { word-break: break-word; overflow-wrap: anywhere; }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 11px; color: #0f172a; font-weight: 700; }
    .badge.running { background: #fde047; }
    .badge.starting { background: #fb923c; color:#0b1220; }
    .badge.success { background: #34d399; }
    .badge.error { background: #f87171; }
    .badge.queued { background: #60a5fa; color: #0b1220; }
    .badge.canceled { background: #cbd5e1; color: #0b1220; }
    .progress { background: #1f2937; border-radius: 8px; height: 9px; overflow: hidden; margin-top: 6px; box-shadow: inset 0 0 0 1px rgba(255,255,255,0.02); }
    .progress-bar { background: linear-gradient(90deg, #22c55e, #4ade80); height: 100%; transition: width 0.2s ease; }
    .item { padding: 9px; border-bottom: 1px solid #1f2937; }
    .item:last-child { border-bottom: 0; }
    .muted { color: #94a3b8; }
    .flex-between { display: flex; justify-content: space-between; gap: 8px; align-items: center; }
    .path { word-break: break-all; }
    .metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(100px, 1fr)); gap: 6px; }
    .metric-card { background: rgba(255,255,255,0.03); border: 1px solid #1f2937; border-radius: 10px; padding: 6px; box-shadow: inset 0 0 0 1px rgba(255,255,255,0.03); }
    .metric-label { font-size: 10px; color: #8ea0bd; text-transform: uppercase; letter-spacing: 0.8px; display: flex; align-items: center; gap: 6px; }
    .metric-value { font-size: 13px; font-weight: 700; color: #e5edff; margin-top: 2px; font-family: Arial, "Helvetica Neue", sans-serif; }
    .smb-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 8px; }
    .smb-list { max-height: 220px; overflow-y: auto; border: 1px solid #1f2937; border-radius: 10px; padding: 8px; background: #0b1220; box-shadow: inset 0 0 0 1px rgba(255,255,255,0.02); }
    .smb-item { padding: 6px 0; border-bottom: 1px solid #1f2937; display: flex; justify-content: space-between; gap: 8px; align-items: center; }
    .smb-item:last-child { border-bottom: 0; }
    .smb-btn { padding: 7px 10px; border: 0; border-radius: 8px; background: linear-gradient(135deg, #2563eb, #4f46e5); color: #fff; cursor: pointer; }
    .smb-path { word-break: break-all; flex: 1; }
    .icon { width: 16px; height: 16px; display:inline-block; }
  </style>
</head>
<body>
  <header>
    <h1><span class="logo-dot"></span> Linux Video Encoder v__VERSION__</h1>
    <div style="display:flex; gap:10px; align-items:center;">
      <button onclick="window.location.reload(true)">Hard Reload</button>
      <div id="clock" class="muted"></div>
    </div>
  </header>
  <div class="grid">
    <div class="panel">
      <h2>🟢 Active Encodes</h2>
      <div class="muted" id="hb-runtime"></div>
      <div id="active"></div>
    </div>
    <div class="panel">
      <h2>🕒 Recent Jobs</h2>
      <div id="recent" style="max-height: 260px; overflow-y: auto;"></div>
      <div style="margin-top:8px; display:flex; gap:6px; flex-wrap: wrap;">
        <button data-clear="success" class="clear-btn">Clear Success</button>
        <button data-clear="error" class="clear-btn">Clear Error</button>
        <button data-clear="running" class="clear-btn">Clear Running</button>
        <button data-clear="canceled" class="clear-btn">Clear Canceled</button>
        <button data-clear="all" class="clear-btn">Clear All</button>
      </div>
    </div>
    <div class="panel">
      <h2>📣 Status Messages</h2>
      <div id="events" class="log"></div>
    </div>
    <div class="panel">
      <h2>📊 System Metrics</h2>
      <div id="metrics" class="log"></div>
    </div>
    <div class="panel">
      <h2>🌐 SMB Browser</h2>
      <form id="smb-form" style="display:grid; gap:6px;">
        <input id="smb-url" placeholder="smb://server/share[/path]" />
        <input id="smb-user" placeholder="Username" />
        <input id="smb-pass" placeholder="Password" type="password" />
        <button type="button" id="smb-connect">Connect</button>
      </form>
      <div class="smb-grid" style="margin-top:8px;">
        <div>
          <div class="muted">Mounts</div>
          <div id="smb-mounts" class="smb-list"></div>
        </div>
        <div>
          <div class="muted">Browse</div>
          <div id="smb-browse" class="smb-list"></div>
        </div>
      </div>
      <div style="margin-top:8px; display:flex; gap:6px; flex-wrap:wrap;">
        <input id="smb-current-path" readonly placeholder="Path" style="flex:1;"/>
        <button class="smb-btn" id="smb-up">Up</button>
      </div>
      <div style="margin-top:8px; display:flex; gap:6px; flex-wrap:wrap;">
        <button class="smb-btn" id="smb-queue">Queue selected for encode</button>
        <button class="smb-btn" id="smb-refresh">Refresh</button>
      </div>
    </div>
    <div class="panel">
      <h2>🎛️ HandBrake Settings</h2>
      <div class="muted" id="hb-summary" style="margin-bottom:6px;"></div>
      <form id="handbrake-form">
        <label>Default encoder
          <select id="hb-encoder" name="encoder">
            <option value="x264">x264</option>
            <option value="x265">x265</option>
            <option value="qsv_h264">qsv_h264</option>
            <option value="qsv_h265">qsv_h265</option>
            <option value="nvenc_h264">nvenc_h264</option>
            <option value="nvenc_h265">nvenc_h265</option>
          </select>
        </label>
        <label>Default quality (constant quality RF, lower = higher quality)
          <select id="hb-quality" name="quality">
            <option value="16">RF 16 (~4000 kbps)</option>
            <option value="18">RF 18 (~3500 kbps)</option>
            <option value="20">RF 20 (~3000 kbps)</option>
            <option value="22">RF 22 (~2500 kbps)</option>
            <option value="24">RF 24 (~2000 kbps)</option>
            <option value="25">RF 25 (~1750 kbps)</option>
            <option value="26">RF 26 (~1500 kbps)</option>
            <option value="28">RF 28 (~1200 kbps)</option>
            <option value="30">RF 30 (~1000 kbps)</option>
          </select>
        </label>
        <label>Target bitrate (overrides RF when set)
          <select id="hb-bitrate">
            <option value="">None (use RF)</option>
            <option value="500">500 kbps</option>
            <option value="1000">1000 kbps</option>
            <option value="1500">1500 kbps</option>
            <option value="2000">2000 kbps</option>
            <option value="2500">Low ~2500 kbps</option>
            <option value="3000">3000 kbps</option>
            <option value="3500">3500 kbps</option>
            <option value="4000">4000 kbps</option>
            <option value="4500">4500 kbps</option>
            <option value="5000">Medium ~5000 kbps</option>
            <option value="5500">5500 kbps</option>
            <option value="6000">6000 kbps</option>
            <option value="6500">6500 kbps</option>
            <option value="7000">7000 kbps</option>
            <option value="7500">7500 kbps</option>
            <option value="8000">High ~8000 kbps</option>
            <option value="custom">Custom (enter below)</option>
          </select>
          <input id="hb-bitrate-custom" placeholder="Custom kbps" type="number" min="500" step="100" />
          <label style="display:flex; align-items:center; gap:6px;">
            <input type="checkbox" id="hb-two-pass" /> Two-pass when bitrate set
          </label>
        </label>
        <label>Audio tracks
          <select id="hb-audio-all">
            <option value="false">First track</option>
            <option value="true">All audio tracks</option>
          </select>
        </label>
        <label>Audio encoder (when encoding)
          <select id="hb-audio-encoder" name="audio_encoder">
            <option value="av_aac">AAC (av_aac)</option>
            <option value="av_aac_he">AAC HE</option>
            <option value="opus">Opus</option>
            <option value="ac3">AC3</option>
            <option value="eac3">E-AC3</option>
            <option value="copy">Copy (passthrough)</option>
          </select>
        </label>
        <label>Mixdown
          <select id="hb-audio-mix">
            <option value="">Auto</option>
            <option value="stereo">Stereo</option>
            <option value="dpl2">Dolby Surround</option>
            <option value="5point1">5.1</option>
            <option value="7point1">7.1</option>
          </select>
        </label>
        <label>Sample rate
          <select id="hb-audio-rate">
            <option value="">Auto</option>
            <option value="44100">44.1 kHz</option>
            <option value="48000">48 kHz</option>
          </select>
        </label>
        <label>DRC (0-4)
          <input id="hb-audio-drc" type="number" min="0" max="4" step="0.5" placeholder="0 (off)" />
        </label>
        <label>Gain (dB)
          <input id="hb-audio-gain" type="number" step="0.5" placeholder="0" />
        </label>
        <label>Language filter (comma codes, e.g., eng,fre)
          <input id="hb-audio-lang" placeholder="eng,fre" />
        </label>
        <label>Track list (comma indexes, blank=auto)
          <input id="hb-audio-tracks" placeholder="1,2" />
        </label>
        <label>DVD quality (constant quality RF, lower = higher quality)
          <select id="hb-dvd-quality" name="quality_dvd">
            <option value="16">RF 16 (~4000 kbps)</option>
            <option value="18">RF 18 (~3500 kbps)</option>
            <option value="20">RF 20 (~3000 kbps)</option>
            <option value="22">RF 22 (~2500 kbps)</option>
            <option value="24">RF 24 (~2000 kbps)</option>
            <option value="25">RF 25 (~1750 kbps)</option>
            <option value="26">RF 26 (~1500 kbps)</option>
            <option value="28">RF 28 (~1200 kbps)</option>
            <option value="30">RF 30 (~1000 kbps)</option>
          </select>
        </label>
        <label>Blu-ray quality (constant quality RF, lower = higher quality)
          <select id="hb-br-quality" name="quality_br">
            <option value="16">RF 16 (~4000 kbps)</option>
            <option value="18">RF 18 (~3500 kbps)</option>
            <option value="20">RF 20 (~3000 kbps)</option>
            <option value="22">RF 22 (~2500 kbps)</option>
            <option value="24">RF 24 (~2000 kbps)</option>
            <option value="25">RF 25 (~1750 kbps)</option>
            <option value="26">RF 26 (~1500 kbps)</option>
            <option value="28">RF 28 (~1200 kbps)</option>
            <option value="30">RF 30 (~1000 kbps)</option>
          </select>
        </label>
        <label>Output extension
          <select id="hb-ext" name="extension">
            <option value=".mkv">.mkv</option>
            <option value=".mp4">.mp4</option>
            <option value=".m4v">.m4v</option>
          </select>
        </label>
        <label>Subtitles
          <select id="hb-subs">
            <option value="none">None</option>
            <option value="copy_all">Copy all subtitles</option>
            <option value="burn_forced">Burn forced (first track)</option>
          </select>
        </label>
        <label>Audio mode (overrides Audio encoder when set)
          <select id="hb-audio-mode" name="audio_mode">
            <option value="encode">Encode (AAC)</option>
            <option value="copy">Copy original</option>
            <option value="auto_dolby">Auto Dolby (copy AC3/E-AC3; else E-AC3)</option>
          </select>
        </label>
        <label>Audio bitrate (if encoding)
          <select id="hb-audio-bitrate" name="audio_bitrate_kbps">
            <option value="128">128 kbps</option>
            <option value="160">160 kbps</option>
            <option value="192">192 kbps</option>
            <option value="256">256 kbps</option>
            <option value="320">320 kbps</option>
          </select>
        </label>
        <button type="button" id="hb-save">Save HandBrake</button>
        <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin-top:4px;">
          <select id="hb-preset-select" style="flex:1;">
            <option value="">Load preset...</option>
          </select>
          <input id="hb-preset-name" placeholder="Preset name" style="flex:1;"/>
          <button type="button" id="hb-preset-save">Save Preset</button>
          <button type="button" id="hb-preset-delete">Delete Preset</button>
        </div>
        <div class="muted">Applies: Default for regular files, DVD for VIDEO_TS, BR for BDMV/STREAM.</div>
      </form>
    </div>
    <div class="panel">
      <h2>📀 MakeMKV Settings</h2>
      <form id="makemkv-form">
        <label>Rip directory <input id="mk-ripdir" name="rip_dir" /></label>
        <label>Min title length (seconds) <input id="mk-minlen" name="min_length" type="number" step="60" /></label>
        <label>Titles to rip (comma-separated, blank = all) <input id="mk-titles" name="titles" placeholder="e.g. 0,1,2" /></label>
        <label>Audio languages to keep (comma codes, blank = all) <input id="mk-audio-langs" name="audio_langs" placeholder="e.g. eng,fre,jpn" /></label>
        <label>Subtitle languages to keep (comma codes, blank = all) <input id="mk-sub-langs" name="subtitle_langs" placeholder="e.g. eng,spa" /></label>
        <label style="display:flex; align-items:center; gap:6px;">
          <input type="checkbox" id="mk-keep" /> Keep ripped MKVs after encode
        </label>
        <label>Preferred audio language(s) <input id="mk-pref-audio" placeholder="eng" /></label>
        <label>Preferred subtitle language(s) <input id="mk-pref-sub" placeholder="eng" /></label>
        <label style="display:flex; align-items:center; gap:6px;">
          <input type="checkbox" id="mk-exclude-commentary" /> Exclude commentary tracks when choosing
        </label>
        <label style="display:flex; align-items:center; gap:6px;">
          <input type="checkbox" id="mk-prefer-surround" /> Prefer surround audio (5.1+) when available
        </label>
        <label style="display:flex; align-items:center; gap:6px;">
          <input type="checkbox" id="mk-auto-rip" /> Auto-start rip when disc detected
        </label>
        <button type="button" id="mk-save">Save MakeMKV</button>
      </form>
      <div style="margin-top:8px;">
        <div class="muted" id="mk-disc-status">Disc status: unknown</div>
        <div style="display:flex; gap:6px; margin:6px 0;">
          <button type="button" id="mk-refresh-info">Refresh disc info</button>
          <button type="button" id="mk-start-rip">Start rip</button>
        </div>
        <textarea id="mk-info" class="log" style="height:160px; margin-top:4px;" readonly placeholder="Disc info will appear here after detection."></textarea>
      </div>
      <div style="margin-top:8px; display:grid; gap:6px;">
        <label>MakeMKV registration key (paste monthly key)
          <input id="mk-key" placeholder="T-XXXX-..." />
        </label>
        <button type="button" id="mk-register">Register MakeMKV</button>
        <div style="display:flex; gap:6px; align-items:center; flex-wrap:wrap;">
          <button type="button" id="mk-update-check">Check for MakeMKV update</button>
          <span class="muted" id="mk-update-status">Update status: unknown</span>
        </div>
        <div class="muted">Installed MakeMKV: <span id="mk-installed">unknown</span></div>
        <label>Latest MakeMKV version (from makemkv.com)
          <input id="mk-latest" placeholder="e.g., 1.18.3" />
        </label>
        <label>Host update command (run on Ubuntu host)
          <textarea id="mk-update-cmd" class="log" style="height:70px;" readonly></textarea>
        </label>
      </div>
    </div>
    <div class="panel" style="grid-column: 1 / -1;">
      <div style="display:flex; align-items:center; gap:10px; margin-bottom:6px; justify-content: space-between;">
        <h2 style="margin:0;">🧾 Logs</h2>
        <button id="copy-logs" style="padding:6px 10px; background:#2563eb; color:#fff; border:0; border-radius:6px; cursor:pointer;">Copy last 300</button>
      </div>
      <div id="logs" class="log"></div>
    </div>
  </div>
  <script>
    let hbDirty = false;
    let mkDirty = false;
    loadPresets();
    const smbForm = document.getElementById("smb-form");
    function connectSmb() {
      document.getElementById("smb-connect").click();
    }

    async function fetchJSON(url) {
      const res = await fetch(url);
      return res.json();
    }

    function renderMetrics(metrics) {
      const el = document.getElementById("metrics");
      if (!metrics) {
        el.textContent = "Metrics unavailable.";
        return;
      }
      const cards = [];
      const cpuPct = (metrics.cpu_pct !== undefined && metrics.cpu_pct !== null) ? metrics.cpu_pct.toFixed(1) + "%" : "n/a";
      // Order: CPU, GPU, Memory, Disk, Output, Net
      cards.push({ icon: "🖥️", label: "CPU", value: cpuPct });
      if (metrics.gpu) {
        const g = metrics.gpu;
        cards.push({ icon: "🎞️", label: "GPU", value: g.util + "% util | " + g.mem_used_mb + " / " + g.mem_total_mb + " MB" });
      }
      if (metrics.mem) {
        cards.push({ icon: "💾", label: "Memory", value: metrics.mem.used_mb + " / " + metrics.mem.total_mb + " MB" });
      }
      if (metrics.block) {
        cards.push({ icon: "🗄️", label: "Disk", value: metrics.block.read_mb + " MB r / " + metrics.block.write_mb + " MB w" });
      }
      if (metrics.fs) {
        cards.push({ icon: "📂", label: "Output FS", value: metrics.fs.free_gb + " / " + metrics.fs.total_gb + " GB free" });
      }
      if (metrics.net) {
        cards.push({ icon: "🌐", label: "Net", value: metrics.net.rx_mb + " MB rx / " + metrics.net.tx_mb + " MB tx" });
      }
      el.innerHTML = '<div class="metric-grid">' + cards.map(c => `
        <div class="metric-card">
          <div class="metric-label">${c.icon} ${c.label}</div>
          <div class="metric-value">${c.value}</div>
        </div>
      `).join("") + '</div>';
    }

    function renderLogs(lines) {
      const el = document.getElementById("logs");
      const atBottom = (el.scrollTop + el.clientHeight) >= (el.scrollHeight - 20);
      el.textContent = (lines && lines.length ? lines : ["Ready to encode"]).join("\\n");
      if (atBottom) {
        el.scrollTop = el.scrollHeight;
      }
    }

    function fmtDuration(sec) {
      if (!sec && sec !== 0) return "";
      const s = Math.floor(sec % 60);
      const m = Math.floor(sec / 60) % 60;
      const h = Math.floor(sec / 3600);
      return [h, m, s].map(v => String(v).padStart(2, "0")).join(":");
    }

    function renderList(container, items, empty) {
      if (!items || items.length === 0) {
        container.innerHTML = '<div class="muted">' + empty + '</div>';
        return;
      }
      container.innerHTML = items.map(function(item) {
        const state = item.state || "";
        const badge = '<span class="badge ' + state + '">' + state.toUpperCase() + '</span>';
        const duration = item.duration_sec ? fmtDuration(item.duration_sec) : ((item.finished_at && item.started_at) ? fmtDuration(item.finished_at - (item.started_at || item.finished_at)) : "");
        const hasProgress = item.progress || item.progress === 0;
        const progress = hasProgress ? Math.min(100, Math.max(0, item.progress)).toFixed(0) : null;
        let etaText = "";
        if (item.eta_sec !== undefined && item.eta_sec !== null) {
          const eta = Math.max(0, Math.round(item.eta_sec));
          const h = Math.floor(eta / 3600);
          const m = Math.floor((eta % 3600) / 60);
          const s = eta % 60;
          const parts = [];
          if (h) parts.push(h + "h");
          if (m || h) parts.push(m + "m");
          parts.push(s + "s");
          etaText = "ETA " + parts.join(" ");
        }
        const progBar = progress !== null ? '<div class="progress"><div class="progress-bar" style="width:' + progress + '%"></div></div><div class="muted">Progress: ' + progress + '%</div>' : "";
        let controls = "";
        if (state === "running") {
          controls = '<button class="stop-btn" data-src="' + encodeURIComponent(item.source || "") + '">Stop</button>';
        } else if (state === "confirm") {
          controls = '<button class="confirm-btn" data-action="proceed" data-src="' + encodeURIComponent(item.source || "") + '">Proceed</button> '
                   + '<button class="confirm-btn" data-action="cancel" data-src="' + encodeURIComponent(item.source || "") + '">Cancel</button>';
        }
        const infoLine = item.info ? '<div class="muted">' + item.info + '</div>' : "";
        return [
          '<div class="item">',
          '  <div class="flex-between">',
          '    <div class="path">' + (item.source || "") + '</div>',
          '    <div>' + badge + ' ' + controls + '</div>',
          '  </div>',
          '  <div class="muted">-> ' + (item.destination || "") + '</div>',
          '  <div class="muted">' + (item.message || "") + '</div>',
          infoLine,
          '  <div class="muted">' + (etaText || (duration ? "Encode elapsed: " + duration : "")) + '</div>',
          '  ' + progBar,
          '</div>'
        ].join("");
      }).join("");
    }

    async function refresh() {
      try {
        const status = await fetchJSON("/api/status");
        renderList(document.getElementById("active"), status.active, "No active encodes.");
        renderList(document.getElementById("recent"), status.recent, "No recent jobs.");
        const hbCfg = status.handbrake_config || {};
        const hb = hbCfg.handbrake || {};
        const hbDvd = hbCfg.handbrake_dvd || {};
        const hbBr = hbCfg.handbrake_br || {};
        const hbExt = hb.extension || ".mkv";
        document.getElementById("hb-runtime").textContent =
          "Runtime HB settings: Encoder=" + (hb.encoder || "x264") +
          " | Default RF=" + (hb.quality ?? 20) +
          " | DVD RF=" + (hbDvd.quality ?? 20) +
          " | BR RF=" + (hbBr.quality ?? 25) +
          " | Ext=" + hbExt +
          " | Audio=" + ((hb.audio_mode === "copy") ? "copy" : ((hb.audio_bitrate_kbps || "128") + " kbps"));
        const discInfo = status.disc_info || {};
        const discPending = !!status.disc_pending;
        const discStatusEl = document.getElementById("mk-disc-status");
        const discInfoEl = document.getElementById("mk-info");
        discStatusEl.textContent = discPending ? ("Disc present (index " + (discInfo.disc_index ?? "?") + ")") : "No disc detected.";
        discInfoEl.value = discInfo.info && discInfo.info.raw ? discInfo.info.raw : (discPending ? "Disc detected; info not available yet." : "");
        const startBtn = document.getElementById("mk-start-rip");
        const autoRipEnabled = document.getElementById("mk-auto-rip").checked;
        startBtn.disabled = !discPending || autoRipEnabled;
      } catch (e) {
        document.getElementById("active").innerHTML = "<div class='muted'>Status unavailable.</div>";
        document.getElementById("recent").innerHTML = "<div class='muted'>Status unavailable.</div>";
      }
      try {
        const logs = await fetchJSON("/api/logs");
        const lines = Array.isArray(logs.lines) ? logs.lines : [];
        renderLogs(lines);
      } catch (e) {
        document.getElementById("logs").textContent = "Logs unavailable.";
      }
      try {
        const events = await fetchJSON("/api/events");
        const lines = (events || []).map(function(ev) {
          return "[" + new Date(ev.ts * 1000).toLocaleTimeString() + "] " + ev.message;
        });
        document.getElementById("events").textContent = lines.join("\\n") || "No recent events.";
      } catch (e) {
        document.getElementById("events").textContent = "Events unavailable.";
      }
      try {
        const metrics = await fetchJSON("/api/metrics");
        renderMetrics(metrics);
      } catch (e) {
        document.getElementById("metrics").textContent = "Metrics unavailable.";
      }
      try {
      const cfg = await fetchJSON("/api/config");
      if (!hbDirty) {
        populateHandbrakeForm(cfg);
      }
        if (!mkDirty) {
          document.getElementById("mk-ripdir").value = (cfg.rip_dir || "/mnt/ripped");
          document.getElementById("mk-minlen").value = (cfg.makemkv_minlength !== undefined && cfg.makemkv_minlength !== null) ? cfg.makemkv_minlength : 1200;
          document.getElementById("mk-titles").value = (cfg.makemkv_titles || []).join(", ");
          document.getElementById("mk-audio-langs").value = (cfg.makemkv_audio_langs || []).join(", ");
          document.getElementById("mk-sub-langs").value = (cfg.makemkv_subtitle_langs || []).join(", ");
          document.getElementById("mk-keep").checked = !!cfg.makemkv_keep_ripped;
          document.getElementById("mk-pref-audio").value = (cfg.makemkv_preferred_audio_langs || []).join(", ") || "eng";
          document.getElementById("mk-pref-sub").value = (cfg.makemkv_preferred_subtitle_langs || []).join(", ") || "eng";
          document.getElementById("mk-exclude-commentary").checked = !!cfg.makemkv_exclude_commentary;
          document.getElementById("mk-prefer-surround").checked = cfg.makemkv_prefer_surround !== false;
          document.getElementById("mk-auto-rip").checked = !!cfg.makemkv_auto_rip;
        }
        const hb = cfg.handbrake || {};
        const hbDvd = cfg.handbrake_dvd || {};
        const hbBr = cfg.handbrake_br || {};
        document.getElementById("hb-summary").textContent = "Encoder: " + (hb.encoder || "x264")
          + " | Default RF: " + (hb.quality !== undefined && hb.quality !== null ? hb.quality : 20)
          + " | DVD RF: " + (hbDvd.quality !== undefined && hbDvd.quality !== null ? hbDvd.quality : 20)
          + " | BR RF: " + (hbBr.quality !== undefined && hbBr.quality !== null ? hbBr.quality : 25)
          + " | Ext: " + (hb.extension || ".mkv");
      } catch (e) {
        console.error("Failed to load config", e);
      }
    }

    function tickClock() {
      const now = new Date();
      document.getElementById("clock").textContent = now.toLocaleString();
    }

    function setSelectValue(sel, value, fallback) {
      if (!sel) return;
      const val = (value === undefined || value === null) ? fallback : value;
      const valStr = val.toString();
      const has = Array.from(sel.options).some(o => o.value === valStr);
      sel.value = has ? valStr : fallback.toString();
    }

    function populateHandbrakeForm(cfg) {
      cfg = cfg || {};
      cfg.handbrake = cfg.handbrake || { encoder: "x264", quality: 20, extension: ".mkv", audio_mode: "encode", audio_bitrate_kbps: 128 };
      cfg.handbrake_dvd = cfg.handbrake_dvd || { quality: 20, audio_mode: "encode", audio_bitrate_kbps: 128 };
      cfg.handbrake_br = cfg.handbrake_br || { quality: 25, audio_mode: "encode", audio_bitrate_kbps: 128 };
      setSelectValue(document.getElementById("hb-encoder"), cfg.handbrake.encoder, "x264");
      setSelectValue(document.getElementById("hb-quality"), cfg.handbrake.quality, 20);
      const hbBitrate = cfg.handbrake.video_bitrate_kbps;
      if (hbBitrate === 8000 || hbBitrate === 5000 || hbBitrate === 2500) {
        document.getElementById("hb-bitrate").value = hbBitrate.toString();
        document.getElementById("hb-bitrate-custom").value = "";
      } else if (hbBitrate) {
        document.getElementById("hb-bitrate").value = "custom";
        document.getElementById("hb-bitrate-custom").value = hbBitrate;
      } else {
        document.getElementById("hb-bitrate").value = "";
        document.getElementById("hb-bitrate-custom").value = "";
      }
      document.getElementById("hb-two-pass").checked = !!cfg.handbrake.two_pass;
      setSelectValue(document.getElementById("hb-dvd-quality"), cfg.handbrake_dvd.quality, 20);
      setSelectValue(document.getElementById("hb-br-quality"), cfg.handbrake_br.quality, 25);
      setSelectValue(document.getElementById("hb-ext"), cfg.handbrake.extension, ".mkv");
      setSelectValue(document.getElementById("hb-audio-mode"), cfg.handbrake.audio_mode || "encode", "encode");
      setSelectValue(document.getElementById("hb-audio-bitrate"), cfg.handbrake.audio_bitrate_kbps || 128, 128);
      setSelectValue(document.getElementById("hb-audio-all"), cfg.handbrake.audio_all ? "true" : "false", "false");
      setSelectValue(document.getElementById("hb-subs"), cfg.handbrake.subtitle_mode || "none", "none");
      setSelectValue(document.getElementById("hb-audio-encoder"), cfg.handbrake.audio_encoder || "av_aac", "av_aac");
      setSelectValue(document.getElementById("hb-audio-mix"), cfg.handbrake.audio_mixdown || "", "");
      setSelectValue(document.getElementById("hb-audio-rate"), cfg.handbrake.audio_samplerate || "", "");
      document.getElementById("hb-audio-drc").value = (cfg.handbrake.audio_drc !== undefined && cfg.handbrake.audio_drc !== null) ? cfg.handbrake.audio_drc : "";
      document.getElementById("hb-audio-gain").value = (cfg.handbrake.audio_gain !== undefined && cfg.handbrake.audio_gain !== null) ? cfg.handbrake.audio_gain : "";
      document.getElementById("hb-audio-lang").value = (cfg.handbrake.audio_lang_list || []).join(", ");
      document.getElementById("hb-audio-tracks").value = cfg.handbrake.audio_track_list || "";
    }

    document.getElementById("hb-save").addEventListener("click", async (e) => {
      e.preventDefault();
      e.stopPropagation();
      const qDefault = parseInt(document.getElementById("hb-quality").value || "20", 10) || 20;
      const qDvd = parseInt(document.getElementById("hb-dvd-quality").value || "20", 10) || 20;
      const qBr = parseInt(document.getElementById("hb-br-quality").value || "25", 10) || 25;
      const ext = document.getElementById("hb-ext").value;
      const audioMode = document.getElementById("hb-audio-mode").value;
      const audioBitrate = parseInt(document.getElementById("hb-audio-bitrate").value || "128", 10) || 128;
      const audioAll = document.getElementById("hb-audio-all").value === "true";
      const subtitleMode = document.getElementById("hb-subs").value || "none";
      const audioEncoder = document.getElementById("hb-audio-encoder").value || "av_aac";
      const audioMix = document.getElementById("hb-audio-mix").value || "";
      const audioRate = document.getElementById("hb-audio-rate").value || "";
      const audioDrcRaw = document.getElementById("hb-audio-drc").value;
      const audioDrc = audioDrcRaw === "" ? null : Number(audioDrcRaw);
      const audioGainRaw = document.getElementById("hb-audio-gain").value;
      const audioGain = audioGainRaw === "" ? null : Number(audioGainRaw);
      const audioLang = (document.getElementById("hb-audio-lang").value || "").split(",").map(v => v.trim()).filter(Boolean);
      const audioTracks = document.getElementById("hb-audio-tracks").value || "";
      let targetBitrate = document.getElementById("hb-bitrate").value;
      const customBitrate = parseInt(document.getElementById("hb-bitrate-custom").value || "0", 10) || 0;
      if (targetBitrate === "custom" && customBitrate > 0) {
        targetBitrate = customBitrate;
      } else if (targetBitrate === "") {
        targetBitrate = null;
      } else {
        targetBitrate = parseInt(targetBitrate, 10) || null;
      }
      const twoPass = document.getElementById("hb-two-pass").checked;
      const body = {
        profile: "handbrake",
        handbrake: {
          encoder: document.getElementById("hb-encoder").value,
          quality: qDefault,
          video_bitrate_kbps: targetBitrate,
          two_pass: twoPass,
          extension: ext,
          audio_mode: audioMode,
          audio_bitrate_kbps: audioBitrate,
          audio_encoder: audioEncoder,
          audio_mixdown: audioMix,
          audio_samplerate: audioRate,
          audio_drc: audioDrc,
          audio_gain: audioGain,
          audio_lang_list: audioLang,
          audio_track_list: audioTracks,
          audio_all: audioAll,
          subtitle_mode: subtitleMode
        },
        handbrake_dvd: { quality: qDvd, extension: ext, audio_mode: audioMode, audio_bitrate_kbps: audioBitrate, audio_encoder: audioEncoder, audio_mixdown: audioMix, audio_samplerate: audioRate, audio_drc: audioDrc, audio_gain: audioGain, audio_lang_list: audioLang, audio_track_list: audioTracks, audio_all: audioAll, subtitle_mode: subtitleMode, video_bitrate_kbps: targetBitrate, two_pass: twoPass },
        handbrake_br: { quality: qBr, extension: ext, audio_mode: audioMode, audio_bitrate_kbps: audioBitrate, audio_encoder: audioEncoder, audio_mixdown: audioMix, audio_samplerate: audioRate, audio_drc: audioDrc, audio_gain: audioGain, audio_lang_list: audioLang, audio_track_list: audioTracks, audio_all: audioAll, subtitle_mode: subtitleMode, video_bitrate_kbps: targetBitrate, two_pass: twoPass }
      };
      await fetch("/api/config", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      hbDirty = false;
      refresh();
    });

    document.addEventListener("click", async (e) => {
      if (e.target.classList.contains("clear-btn")) {
        const status = e.target.getAttribute("data-clear");
        await fetch("/api/clear", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status }) });
        refresh();
      }
      if (e.target.classList.contains("confirm-btn")) {
        const src = decodeURIComponent(e.target.getAttribute("data-src"));
        const action = e.target.getAttribute("data-action");
        await fetch("/api/confirm", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ source: src, action }) });
        refresh();
      }
      if (e.target.classList.contains("stop-btn")) {
        const src = decodeURIComponent(e.target.getAttribute("data-src"));
        const ok = confirm("Stop this encode?\\nAre you sure?");
        if (!ok) return;
        let deleteSrc = false;
        if (confirm("Delete the source file too?\\nChoose OK to delete, Cancel to keep.")) {
          deleteSrc = true;
        }
        await fetch("/api/stop", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ source: src, delete_source: deleteSrc }) });
        refresh();
      }
    });

    document.getElementById("mk-save").addEventListener("click", async (e) => {
      e.preventDefault();
      e.stopPropagation();
      const csvToList = (val) => (val || "").split(",").map(v => v.trim()).filter(Boolean);
      const body = {
        rip_dir: document.getElementById("mk-ripdir").value,
        makemkv_minlength: Number(document.getElementById("mk-minlen").value),
        makemkv_titles: csvToList(document.getElementById("mk-titles").value),
        makemkv_audio_langs: csvToList(document.getElementById("mk-audio-langs").value),
        makemkv_subtitle_langs: csvToList(document.getElementById("mk-sub-langs").value),
        makemkv_keep_ripped: document.getElementById("mk-keep").checked,
        makemkv_preferred_audio_langs: csvToList(document.getElementById("mk-pref-audio").value || "eng"),
        makemkv_preferred_subtitle_langs: csvToList(document.getElementById("mk-pref-sub").value || "eng"),
        makemkv_exclude_commentary: document.getElementById("mk-exclude-commentary").checked,
        makemkv_prefer_surround: document.getElementById("mk-prefer-surround").checked,
        makemkv_auto_rip: document.getElementById("mk-auto-rip").checked,
      };
      await fetch("/api/config", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      try { await fetch("/api/events", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message: "MakeMKV settings saved", level: "info" }) }); } catch (err) {}
      alert("MakeMKV settings saved");
      mkDirty = false;
    });

    document.getElementById("handbrake-form").addEventListener("input", () => { hbDirty = true; });
    document.getElementById("makemkv-form").addEventListener("input", () => { mkDirty = true; });
    document.getElementById("makemkv-form").addEventListener("change", () => { mkDirty = true; });
    document.getElementById("handbrake-form").addEventListener("change", () => { hbDirty = true; });

    document.getElementById("copy-logs").addEventListener("click", async () => {
      try {
        const logs = await fetchJSON("/api/logs");
        const lines = (logs.lines || []).slice(-300);
        const text = lines.join("\\n");
        if (navigator.clipboard && navigator.clipboard.writeText) {
          await navigator.clipboard.writeText(text);
        } else {
          const ta = document.createElement("textarea");
          ta.value = text;
          document.body.appendChild(ta);
          ta.select();
          document.execCommand("copy");
          document.body.removeChild(ta);
        }
        alert("Copied last " + lines.length + " log lines to clipboard.");
      } catch (e) {
        alert("Failed to copy logs: " + e);
      }
    });

    // Presets
    async function loadPresets() {
      try {
        const res = await fetch("/api/presets");
        const data = await res.json();
        const sel = document.getElementById("hb-preset-select");
        const current = sel.value;
        sel.innerHTML = '<option value=\"\">Load preset...</option>' + (data.presets || []).map(p => '<option value=\"' + p.name + '\">' + p.name + '</option>').join(\"\\n\");
        if (current) { sel.value = current; }
      } catch (e) {
        console.error(\"Failed to load presets\", e);
      }
    }

    document.getElementById(\"hb-preset-save\").addEventListener(\"click\", async () => {
      const name = document.getElementById(\"hb-preset-name\").value.trim();
      if (!name) { alert(\"Enter a preset name\"); return; }
      // reuse save handler body composition
      const qDefault = parseInt(document.getElementById(\"hb-quality\").value || \"20\", 10) || 20;
      const qDvd = parseInt(document.getElementById(\"hb-dvd-quality\").value || \"20\", 10) || 20;
      const qBr = parseInt(document.getElementById(\"hb-br-quality\").value || \"25\", 10) || 25;
      const ext = document.getElementById(\"hb-ext\").value;
      const audioMode = document.getElementById(\"hb-audio-mode\").value;
      const audioBitrate = parseInt(document.getElementById(\"hb-audio-bitrate\").value || \"128\", 10) || 128;
      const audioAll = document.getElementById(\"hb-audio-all\").value === \"true\";
      const subtitleMode = document.getElementById(\"hb-subs\").value || \"none\";
      const audioEncoder = document.getElementById(\"hb-audio-encoder\").value || \"av_aac\";
      const audioMix = document.getElementById(\"hb-audio-mix\").value || \"\";
      const audioRate = document.getElementById(\"hb-audio-rate\").value || \"\";
      const audioLang = (document.getElementById(\"hb-audio-lang\").value || \"\").split(\",\").map(v => v.trim()).filter(Boolean);
      const audioTracks = document.getElementById(\"hb-audio-tracks\").value || \"\";
      const audioDrcRaw = document.getElementById(\"hb-audio-drc\").value;
      const audioDrc = audioDrcRaw === \"\" ? null : Number(audioDrcRaw);
      const audioGainRaw = document.getElementById(\"hb-audio-gain\").value;
      const audioGain = audioGainRaw === \"\" ? null : Number(audioGainRaw);
      const body = {
        name,
        handbrake: {
          encoder: document.getElementById(\"hb-encoder\").value,
          quality: qDefault,
          extension: ext,
          audio_mode: audioMode,
          audio_bitrate_kbps: audioBitrate,
          audio_encoder: audioEncoder,
          audio_mixdown: audioMix,
          audio_samplerate: audioRate,
          audio_drc: audioDrc,
          audio_gain: audioGain,
          audio_lang_list: audioLang,
          audio_track_list: audioTracks,
          audio_all: audioAll,
          subtitle_mode: subtitleMode
        },
        handbrake_dvd: { quality: qDvd, extension: ext, audio_mode: audioMode, audio_bitrate_kbps: audioBitrate, audio_encoder: audioEncoder, audio_mixdown: audioMix, audio_samplerate: audioRate, audio_drc: audioDrc, audio_gain: audioGain, audio_lang_list: audioLang, audio_track_list: audioTracks, audio_all: audioAll, subtitle_mode: subtitleMode },
        handbrake_br: { quality: qBr, extension: ext, audio_mode: audioMode, audio_bitrate_kbps: audioBitrate, audio_encoder: audioEncoder, audio_mixdown: audioMix, audio_samplerate: audioRate, audio_drc: audioDrc, audio_gain: audioGain, audio_lang_list: audioLang, audio_track_list: audioTracks, audio_all: audioAll, subtitle_mode: subtitleMode }
      };
      await fetch(\"/api/presets\", { method: \"POST\", headers: { \"Content-Type\": \"application/json\" }, body: JSON.stringify(body) });
      await loadPresets();
    });

    document.getElementById(\"hb-preset-delete\").addEventListener(\"click\", async () => {
      const sel = document.getElementById(\"hb-preset-select\");
      const name = sel.value;
      if (!name) { alert(\"Select a preset to delete\"); return; }
      await fetch(\"/api/presets\", { method: \"DELETE\", headers: { \"Content-Type\": \"application/json\" }, body: JSON.stringify({ name }) });
      document.getElementById(\"hb-preset-name\").value = \"\";
      await loadPresets();
    });

    document.getElementById(\"hb-preset-select\").addEventListener(\"change\", async () => {
      const sel = document.getElementById(\"hb-preset-select\");
      const name = sel.value;
      if (!name) return;
      const res = await fetch(\"/api/presets\");
      const data = await res.json();
      const preset = (data.presets || []).find(p => p.name === name);
      if (!preset) return;
      populateHandbrakeForm({ handbrake: preset.handbrake, handbrake_dvd: preset.handbrake_dvd, handbrake_br: preset.handbrake_br });
    });

    // SMB helpers
    let smbMountId = null;
    let smbPath = "/";
    let smbSelected = null;

    async function smbList(pathOverride) {
      if (!smbMountId) { return; }
      const path = pathOverride || smbPath || "/";
      const res = await fetch("/api/smb/list?mount_id=" + encodeURIComponent(smbMountId) + "&path=" + encodeURIComponent(path));
      const data = await res.json();
      smbPath = data.path || "/";
      document.getElementById("smb-current-path").value = smbPath;
      const entries = data.entries || [];
      smbSelected = null;
      document.getElementById("smb-browse").innerHTML = entries.map(e => {
        const icon = e.is_dir ? "📁" : "📄";
        return '<div class="smb-item" data-path="' + e.path + '" data-dir="' + (e.is_dir ? "1" : "0") + '"><span>' + icon + '</span><div class="smb-path">' + e.name + '</div></div>';
      }).join("");
    }

    async function smbRefreshMounts() {
      const res = await fetch("/api/smb/mounts");
      const data = await res.json();
      const mounts = data.mounts || {};
      const mountItems = Object.keys(mounts).map(id => {
        const m = mounts[id];
        const path = (m && m.path) ? m.path : m;
        const label = (m && m.label) ? m.label : (path ? path.split("/").filter(Boolean).pop() : id);
        return '<div class="smb-item"><div class="smb-path">' + (label || id) + '</div><button class="smb-btn smb-unmount" data-id="' + id + '">Unmount</button></div>';
      }).join("");
      document.getElementById("smb-mounts").innerHTML = mountItems || "<div class='muted'>No mounts</div>";
    }

    document.getElementById("smb-connect").addEventListener("click", async () => {
      const body = {
        url: document.getElementById("smb-url").value,
        username: document.getElementById("smb-user").value,
        password: document.getElementById("smb-pass").value
      };
      const res = await fetch("/api/smb/mount", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      const data = await res.json();
      smbMountId = data.mount_id;
      smbPath = "/";
      await smbRefreshMounts();
      await smbList("/");
    });
    smbForm.addEventListener("keydown", async (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        connectSmb();
      }
    });

    document.getElementById("smb-refresh").addEventListener("click", async () => {
      await smbRefreshMounts();
      await smbList();
    });

    document.getElementById("mk-refresh-info").addEventListener("click", async () => {
      try {
        const info = await fetchJSON("/api/makemkv/info");
        const discInfoEl = document.getElementById("mk-info");
        discInfoEl.value = (info && info.info && info.info.raw) ? info.info.raw : (info && info.raw) ? info.raw : "No disc info.";
      } catch (e) {
        alert("Failed to fetch disc info: " + e);
      }
    });

    document.getElementById("mk-register").addEventListener("click", async () => {
      const key = (document.getElementById("mk-key").value || "").trim();
      if (!key) { alert("Enter a MakeMKV key"); return; }
      try {
        const res = await fetch("/api/makemkv/register", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ key }) });
        const data = await res.json();
        if (data.registered) {
          alert("MakeMKV registered");
        } else {
          alert("Registration failed: " + (data.error || "unknown error"));
        }
      } catch (e) {
        alert("Failed to register: " + e);
      }
    });

    function refreshUpdateCommand() {
      const latest = (document.getElementById("mk-latest").value || "").trim();
      const cmdEl = document.getElementById("mk-update-cmd");
      if (!latest) {
        cmdEl.value = "";
        return;
      }
      cmdEl.value = 'curl -fsSL https://raw.githubusercontent.com/thashiznit2003/AutoEncoder/main/linux-video-encoder/scripts/update_makemkv.sh -o /tmp/update_makemkv.sh && chmod +x /tmp/update_makemkv.sh && MAKEMKV_VERSION=' + latest + ' /tmp/update_makemkv.sh';
    }

    document.getElementById("mk-latest").addEventListener("input", refreshUpdateCommand);

    document.getElementById("mk-update-check").addEventListener("click", async () => {
      const statusEl = document.getElementById("mk-update-status");
      statusEl.textContent = "Update status: checking...";
      try {
        const res = await fetch("/api/makemkv/update_check");
        const data = await res.json();
        const msg = data.message || data.stdout || data.error || "Unknown";
        statusEl.textContent = "MakeMKV: " + msg.slice(0, 200);
        if (data.installed_version) {
          document.getElementById("mk-installed").textContent = data.installed_version;
        }
      } catch (e) {
        statusEl.textContent = "Update status: failed to check";
      }
    });

    document.getElementById("mk-start-rip").addEventListener("click", async () => {
      try {
        await fetch("/api/makemkv/rip", { method: "POST" });
        alert("Rip requested. It will start on next scan if a disc is present.");
      } catch (e) {
        alert("Failed to request rip: " + e);
      }
    });

    document.getElementById("smb-up").addEventListener("click", async () => {
      if (!smbMountId || !smbPath || smbPath === "/") return;
      const up = smbPath.replace(/\\/+$/, "").split("/").slice(0, -1).join("/") || "/";
      await smbList(up);
    });

    document.getElementById("smb-browse").addEventListener("click", async (e) => {
      const item = e.target.closest(".smb-item");
      if (!item) return;
      const path = item.getAttribute("data-path");
      const isDir = item.getAttribute("data-dir") === "1";
      if (isDir) {
        await smbList(path);
      } else {
        smbSelected = path;
        document.querySelectorAll("#smb-browse .smb-item").forEach(el => el.style.background = "");
        item.style.background = "#1f2937";
      }
    });

    document.getElementById("smb-mounts").addEventListener("click", async (e) => {
      if (e.target.classList.contains("smb-unmount")) {
        const id = e.target.getAttribute("data-id");
        await fetch("/api/smb/unmount", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ mount_id: id }) });
        if (smbMountId === id) { smbMountId = null; smbSelected = null; smbPath = "/"; document.getElementById("smb-browse").innerHTML = ""; }
        await smbRefreshMounts();
      }
    });

    document.getElementById("smb-queue").addEventListener("click", async () => {
      if (!smbMountId || !smbSelected) { alert("Select a file first."); return; }
      await fetch("/api/smb/queue", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ mount_id: smbMountId, path: smbSelected }) });
      alert("Queued: " + smbSelected);
    });

    smbRefreshMounts();

    setInterval(refresh, 2000);
    setInterval(tickClock, 1000);
    refresh();
    tickClock();
  </script>
</body>
</html>
"""
HTML_PAGE = HTML_PAGE_TEMPLATE.replace("__VERSION__", VERSION)


def create_app(tracker, config_manager=None):
    app = Flask(__name__)
    SMB_MOUNT_ROOT.mkdir(parents=True, exist_ok=True)

    def normalize_smb_url(url: str) -> str:
        url = url.strip()
        if url.startswith("smb://"):
            url = "//" + url[len("smb://") :]
        return url

    def ensure_under(base: pathlib.Path, target: pathlib.Path) -> pathlib.Path:
        try:
            target = target.resolve()
            base = base.resolve()
            if base in target.parents or target == base:
                return target
        except Exception:
            pass
        return base

    def mount_smb(url: str, username: str = "", password: str = "") -> str:
        mid = uuid.uuid4().hex
        mnt = SMB_MOUNT_ROOT / mid
        mnt.mkdir(parents=True, exist_ok=True)
        label = url.rstrip("/").split("/")[-1] if url else mid
        opts = []
        if username:
            opts.append(f"username={username}")
        else:
            opts.append("guest")
        if password:
            opts.append(f"password={password}")
        cmd = ["mount", "-t", "cifs", normalize_smb_url(url), str(mnt), "-o", ",".join(opts)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            try:
                mnt.rmdir()
            except Exception:
                pass
            raise RuntimeError(f"Failed to mount SMB: {res.stderr.strip() or res.stdout.strip() or res.returncode}")
        tracker.add_smb_mount(mid, str(mnt), label=label)
        return mid

    def unmount_smb(mount_id: str):
        mounts = tracker.list_smb_mounts()
        mnt = mounts.get(mount_id)
        if not mnt:
            return
        subprocess.run(["umount", mnt], capture_output=True, text=True)
        try:
            shutil.rmtree(mnt, ignore_errors=True)
        except Exception:
            pass
        tracker.remove_smb_mount(mount_id)

    def list_smb(mount_id: str, rel_path: str = "/"):
        mounts = tracker.list_smb_mounts()
        entry = mounts.get(mount_id)
        mnt = entry.get("path") if isinstance(entry, dict) else entry
        if not mnt:
            raise FileNotFoundError("mount not found")
        base = pathlib.Path(mnt)
        target = ensure_under(base, base / rel_path.lstrip("/"))
        if not target.exists():
            target = base
        entries = []
        try:
            for entry in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                entries.append({
                    "name": entry.name,
                    "is_dir": entry.is_dir(),
                    "path": "/" + entry.relative_to(base).as_posix()
                })
        except Exception:
            pass
        return {"path": "/" + target.relative_to(base).as_posix() if target != base else "/", "entries": entries}

    def read_meminfo():
        mem = {"total_mb": None, "used_mb": None}
        try:
            info = {}
            with open("/proc/meminfo", "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.split(":")
                    if len(parts) < 2:
                        continue
                    key = parts[0].strip()
                    val = parts[1].strip().split()[0]
                    info[key] = int(val)
            total_kb = info.get("MemTotal", 0)
            avail_kb = info.get("MemAvailable", 0)
            used_kb = total_kb - avail_kb
            mem["total_mb"] = round(total_kb / 1024, 1)
            mem["used_mb"] = round(used_kb / 1024, 1)
        except Exception:
            pass
        return mem

    def read_netdev():
        rx = tx = 0
        try:
            with open("/proc/net/dev", "r", encoding="utf-8") as f:
                for line in f:
                    if ":" not in line:
                        continue
                    iface, rest = line.split(":", 1)
                    parts = rest.strip().split()
                    if len(parts) >= 8:
                        rx += int(parts[0])
                        tx += int(parts[8])
        except Exception:
            pass
        return {"rx_mb": round(rx / (1024 * 1024), 1), "tx_mb": round(tx / (1024 * 1024), 1)}

    def read_diskstats():
        rd = wr = 0
        try:
            with open("/proc/diskstats", "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) < 14:
                        continue
                    # sectors read at index 5, written at index 9
                    try:
                        sectors_rd = int(parts[5])
                        sectors_wr = int(parts[9])
                        rd += sectors_rd
                        wr += sectors_wr
                    except Exception:
                        continue
            # assume 512 bytes per sector
            rd_mb = round((rd * 512) / (1024 * 1024), 1)
            wr_mb = round((wr * 512) / (1024 * 1024), 1)
            return {"read_mb": rd_mb, "write_mb": wr_mb}
        except Exception:
            return None

    def read_gpu():
        try:
            res = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode != 0 or not res.stdout.strip():
                return None
            line = res.stdout.strip().splitlines()[0]
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 3:
                util = int(parts[0])
                mem_used = int(parts[1])
                mem_total = int(parts[2])
                return {"util": util, "mem_used_mb": mem_used, "mem_total_mb": mem_total}
        except Exception:
            pass
        return None

    def read_fs(path="/mnt/output"):
        try:
            st = os.statvfs(path)
            total = st.f_frsize * st.f_blocks
            free = st.f_frsize * st.f_bavail
            return {
                "path": path,
                "free_gb": round(free / (1024 ** 3), 1),
                "total_gb": round(total / (1024 ** 3), 1),
            }
        except Exception:
            return None

    @app.route("/")
    def index():
        return Response(HTML_PAGE, mimetype="text/html")

    @app.route("/api/status")
    def status():
        data = tracker.snapshot()
        data["version"] = VERSION
        if config_manager:
            cfg = config_manager.read()
            data["handbrake_config"] = {
                "profile": cfg.get("profile"),
                "handbrake": cfg.get("handbrake", {}),
                "handbrake_dvd": cfg.get("handbrake_dvd", {}),
                "handbrake_br": cfg.get("handbrake_br", {}),
            }
        return jsonify(data)

    @app.route("/api/logs")
    def logs():
        return jsonify({"lines": tracker.tail_logs()})

    @app.route("/api/events")
    def events():
        return jsonify(tracker.events())

    @app.route("/api/events", methods=["POST"])
    def add_event():
        payload = request.get_json(force=True) or {}
        msg = payload.get("message", "")
        level = payload.get("level", "info")
        if msg:
            tracker.add_event(msg, level=level)
            return jsonify({"added": True})
        return jsonify({"added": False}), 400

    @app.route("/api/metrics")
    def metrics():
        import os
        load1, load5, load15 = os.getloadavg()
        cores = os.cpu_count() or 1
        data = {
            "cpu_load": [round(load1, 2), round(load5, 2), round(load15, 2)],
            "cpu_pct": round((load1 / cores) * 100, 1),
            "mem": read_meminfo(),
            "net": read_netdev(),
            "block": read_diskstats(),
            "gpu": read_gpu(),
            "fs": read_fs(),
            "ts": time.time(),
        }
        return jsonify(data)

    if config_manager:
        @app.route("/api/config", methods=["GET", "POST"])
        def config():
            if request.method == "GET":
                return jsonify(config_manager.read())
            payload = request.get_json(force=True) or {}
            updated = config_manager.update(payload)
            return jsonify(updated)

    @app.route("/api/smb/mount", methods=["POST"])
    def smb_mount():
        payload = request.get_json(force=True) or {}
        url = payload.get("url", "")
        username = payload.get("username", "")
        password = payload.get("password", "")
        if not url:
            return jsonify({"error": "url required"}), 400
        try:
            mid = mount_smb(url, username, password)
            return jsonify({"mount_id": mid, "path": tracker.list_smb_mounts().get(mid)})
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    @app.route("/api/smb/mounts")
    def smb_mounts():
        return jsonify({"mounts": tracker.list_smb_mounts()})

    @app.route("/api/smb/unmount", methods=["POST"])
    def smb_unmount():
        payload = request.get_json(force=True) or {}
        mid = payload.get("mount_id")
        if not mid:
            return jsonify({"error": "mount_id required"}), 400
        unmount_smb(mid)
        return jsonify({"unmounted": mid})

    @app.route("/api/smb/list")
    def smb_list():
        mid = request.args.get("mount_id")
        path = request.args.get("path", "/")
        if not mid:
            return jsonify({"error": "mount_id required"}), 400
        try:
            data = list_smb(mid, path)
            return jsonify(data)
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    @app.route("/api/smb/queue", methods=["POST"])
    def smb_queue():
        payload = request.get_json(force=True) or {}
        mid = payload.get("mount_id")
        rel_path = payload.get("path", "/")
        if not mid:
            return jsonify({"error": "mount_id required"}), 400
        mounts = tracker.list_smb_mounts()
        entry = mounts.get(mid)
        mnt = entry.get("path") if isinstance(entry, dict) else entry
        if not mnt:
            return jsonify({"error": "mount not found"}), 400
        base = pathlib.Path(mnt)
        target = ensure_under(base, base / rel_path.lstrip("/"))
        if not target.is_file():
            return jsonify({"error": "file not found"}), 400
        staging_dir = "/mnt/smb_staging"
        if config_manager:
            try:
                cfg = config_manager.read()
                staging_dir = cfg.get("smb_staging_dir", staging_dir) or staging_dir
            except Exception:
                pass
        dest_root = pathlib.Path(staging_dir)
        dest_root.mkdir(parents=True, exist_ok=True)
        def unique_path(root: pathlib.Path, name: str) -> pathlib.Path:
            cand = root / name
            stem = cand.stem
            suffix = cand.suffix
            idx = 1
            while cand.exists():
                cand = root / f"{stem}({idx}){suffix}"
                idx += 1
            return cand
        dest = unique_path(dest_root, target.name)
        shutil.copy2(target, dest)
        tracker.add_manual_file(str(dest))
        tracker.add_event(f"Copied from SMB and staged: {target} -> {dest}")
        return jsonify({"queued": str(dest), "source": str(target)})

    @app.route("/api/makemkv/info")
    def makemkv_info():
        return jsonify(tracker.disc_info() or {})

    @app.route("/api/makemkv/rip", methods=["POST"])
    def makemkv_rip():
        tracker.request_disc_rip()
        tracker.add_event("Manual MakeMKV rip requested.")
        return jsonify({"requested": True})

    @app.route("/api/makemkv/register", methods=["POST"])
    def makemkv_register():
        payload = request.get_json(force=True) or {}
        raw_key = (payload.get("key") or "")
        def sanitize_key(k: str) -> str:
            s = (k or "").strip()
            if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
                s = s[1:-1].strip()
            return s
        key = sanitize_key(raw_key)
        if not key:
            return jsonify({"error": "key required"}), 400
        settings_path = pathlib.Path("/root/.MakeMKV/settings.conf")
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        def write_key_to_settings(k: str):
            try:
                lines = []
                if settings_path.exists():
                    for ln in settings_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                        if not ln.strip().startswith("app_Key"):
                            lines.append(ln)
                lines.append(f'app_Key = "{k}"')
                settings_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
                return True
            except Exception:
                return False
        try:
            res = subprocess.run(["makemkvcon", "reg", key], capture_output=True, text=True, check=False)
            if res.returncode == 0:
                tracker.add_event("MakeMKV registered successfully.")
                return jsonify({"registered": True})
            stderr = res.stderr.strip() if res.stderr else ""
            stdout = res.stdout.strip() if res.stdout else ""
            msg = "; ".join([p for p in [stderr, stdout] if p]) or f"exit code {res.returncode}"
            # Always persist key even if makemkvcon rejects it, but report failure
            write_key_to_settings(key)
            tracker.add_event(f"MakeMKV registration failed: {msg}", level="error")
            return jsonify({"registered": False, "error": msg}), 400
        except FileNotFoundError:
            tracker.add_event("MakeMKV registration failed: makemkvcon not found", level="error")
            return jsonify({"registered": False, "error": "makemkvcon not found"}), 500

    @app.route("/api/makemkv/update_check")
    def makemkv_update_check():
        try:
            res = subprocess.run(
                ["makemkvcon", "-r", "--cache=1", "info", "disc:0"],
                capture_output=True,
                text=True,
                check=False,
                timeout=15,
            )
            stdout = res.stdout.strip() if res.stdout else ""
            stderr = res.stderr.strip() if res.stderr else ""
            version_line = ""
            for ln in (stdout.splitlines() if stdout else []):
                if "MakeMKV v" in ln:
                    version_line = ln
                    break
            msg = version_line or (stderr or "") or (stdout or "") or f"exit code {res.returncode}"
            ok = res.returncode == 0 and bool(version_line)
            installed_version = None
            if version_line:
                try:
                    installed_version = version_line.split("MakeMKV")[1].strip().split()[0]
                except Exception:
                    installed_version = None
            return jsonify({"ok": ok, "stdout": stdout, "stderr": stderr, "message": msg, "returncode": res.returncode, "installed_version": installed_version})
        except FileNotFoundError:
            return jsonify({"ok": False, "error": "makemkvcon not found"}), 500
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500
    
    @app.route("/api/presets", methods=["GET", "POST", "DELETE"])
    def hb_presets():
        if not config_manager:
            return jsonify({"presets": []})
        if request.method == "GET":
            cfg = config_manager.read()
            return jsonify({"presets": cfg.get("handbrake_presets", [])})
        payload = request.get_json(force=True) or {}
        if request.method == "POST":
            name = (payload.get("name") or "").strip()
            if not name:
                return jsonify({"error": "name required"}), 400
            cfg = config_manager.read()
            presets = cfg.get("handbrake_presets", [])
            # replace if exists
            presets = [p for p in presets if p.get("name") != name]
            presets.append({
                "name": name,
                "handbrake": payload.get("handbrake", {}),
                "handbrake_dvd": payload.get("handbrake_dvd", {}),
                "handbrake_br": payload.get("handbrake_br", {}),
            })
            cfg["handbrake_presets"] = presets
            config_manager.update(cfg)
            return jsonify({"saved": name})
        if request.method == "DELETE":
            name = (payload.get("name") or "").strip()
            cfg = config_manager.read()
            presets = [p for p in cfg.get("handbrake_presets", []) if p.get("name") != name]
            cfg["handbrake_presets"] = presets
            config_manager.update(cfg)
            return jsonify({"deleted": name})

    @app.route("/api/stop", methods=["POST"])
    def stop():
        payload = request.get_json(force=True) or {}
        src = payload.get("source")
        delete_src = payload.get("delete_source", False)
        if src:
            tracker.stop_proc(src)
            tracker.add_event(f"Stopped encode: {src}")
            if delete_src:
                try:
                    os.remove(src)
                    tracker.add_event(f"Deleted source: {src}")
                except Exception:
                    tracker.add_event(f"Failed to delete source: {src}", level="error")
        return jsonify({"stopped": bool(src)})

    @app.route("/api/confirm", methods=["POST"])
    def confirm_job():
        payload = request.get_json(force=True) or {}
        src = payload.get("source")
        action = payload.get("action", "cancel")
        if not src:
            return jsonify({"error": "source required"}), 400
        if action == "proceed":
            tracker.clear_confirm_required(src)
            tracker.add_confirm_ok(src)
            tracker.set_state(src, "starting")
            tracker.set_message(src, "")
            tracker.add_event(f"Proceeding with encode: {src}")
            return jsonify({"proceeded": src})
        else:
            tracker.stop_proc(src)
            tracker.clear_confirm_required(src)
            tracker.clear_confirm_ok(src)
            tracker.add_event(f"Canceled encode after warning: {src}")
            return jsonify({"canceled": src})

    @app.route("/api/clear", methods=["POST"])
    def clear():
        payload = request.get_json(force=True) or {}
        status = payload.get("status")
        if status == "all":
            tracker.clear_history(None)
        else:
            tracker.clear_history(status)
        return jsonify({"cleared": status or "all"})

    return app


def start_web_server(tracker, config_manager=None, port: int = 5959):
    app = create_app(tracker, config_manager=config_manager)

    def _run():
        app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False, threaded=True)

    import threading

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t
