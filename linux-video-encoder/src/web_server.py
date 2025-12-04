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
    body { margin: 0; background: radial-gradient(circle at 20% 20%, rgba(59,130,246,0.08), transparent 40%), #0b1220; color: #e2e8f0; }
    header { padding: 12px 16px; background: #0f172a; border-bottom: 1px solid #1f2937; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 6px 20px rgba(0,0,0,0.25); }
    h1 { font-size: 18px; margin: 0; letter-spacing: 0.2px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); grid-auto-rows: minmax(240px, auto); gap: 12px; padding: 12px; }
    .panel { background: linear-gradient(145deg, #111827, #0d1528); border: 1px solid #1f2937; border-radius: 12px; padding: 12px; box-shadow: 0 14px 38px rgba(0,0,0,0.28); }
    .panel h2 { margin: 0 0 8px 0; font-size: 15px; color: #93c5fd; letter-spacing: 0.3px; }
    form { display: grid; gap: 8px; margin-top: 8px; }
    label { font-size: 12px; color: #cbd5e1; display: grid; gap: 4px; }
    input, select { padding: 8px 10px; border-radius: 8px; border: 1px solid #1f2937; background: #0b1220; color: #e2e8f0; }
    button { padding: 8px 12px; border: 0; border-radius: 8px; background: #2563eb; color: #fff; font-weight: 700; cursor: pointer; transition: transform 0.08s ease, box-shadow 0.2s; }
    button:hover { background: #1d4ed8; transform: translateY(-1px); box-shadow: 0 6px 16px rgba(37,99,235,0.35); }
    .log { font-family: "SFMono-Regular", Menlo, Consolas, monospace; font-size: 12px; background: #0b1220; border-radius: 10px; padding: 10px; overflow: auto; height: 320px; border: 1px solid #1f2937; white-space: pre-wrap; }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 11px; color: #0f172a; font-weight: 700; }
    .badge.running { background: #fde047; }
    .badge.success { background: #34d399; }
    .badge.error { background: #f87171; }
    .badge.queued { background: #60a5fa; }
    .badge.canceled { background: #cbd5e1; }
    .progress { background: #1f2937; border-radius: 6px; height: 8px; overflow: hidden; margin-top: 6px; }
    .progress-bar { background: #22c55e; height: 100%; transition: width 0.2s ease; }
    .item { padding: 8px; border-bottom: 1px solid #1f2937; }
    .item:last-child { border-bottom: 0; }
    .muted { color: #94a3b8; }
    .flex-between { display: flex; justify-content: space-between; gap: 8px; align-items: center; }
    .path { word-break: break-all; }
    .metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(100px, 1fr)); gap: 6px; }
    .metric-card { background: rgba(255,255,255,0.03); border: 1px solid #1f2937; border-radius: 10px; padding: 6px; box-shadow: inset 0 0 0 1px rgba(255,255,255,0.03); }
    .metric-label { font-size: 10px; color: #8ea0bd; text-transform: uppercase; letter-spacing: 0.8px; display: flex; align-items: center; gap: 6px; }
    .metric-value { font-size: 13px; font-weight: 700; color: #e5edff; margin-top: 2px; font-family: Arial, "Helvetica Neue", sans-serif; }
    .smb-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 8px; }
    .smb-list { max-height: 220px; overflow-y: auto; border: 1px solid #1f2937; border-radius: 8px; padding: 8px; background: #0b1220; }
    .smb-item { padding: 6px 0; border-bottom: 1px solid #1f2937; display: flex; justify-content: space-between; gap: 8px; align-items: center; }
    .smb-item:last-child { border-bottom: 0; }
    .smb-btn { padding: 6px 10px; border: 0; border-radius: 6px; background: #2563eb; color: #fff; cursor: pointer; }
    .smb-path { word-break: break-all; flex: 1; }
  </style>
</head>
<body>
  <header>
    <h1>Linux Video Encoder v__VERSION__ - Live Status</h1>
    <div style="display:flex; gap:10px; align-items:center;">
      <button onclick="window.location.reload(true)">Hard Reload</button>
      <div id="clock" class="muted"></div>
    </div>
  </header>
  <div class="grid">
    <div class="panel">
      <h2>Active Encodes</h2>
      <div class="muted" id="hb-runtime"></div>
      <div id="active"></div>
    </div>
    <div class="panel">
      <h2>Recent Jobs</h2>
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
      <h2>Status Messages</h2>
      <div id="events" class="log"></div>
    </div>
    <div class="panel">
      <h2>System Metrics</h2>
      <div id="metrics" class="log"></div>
    </div>
    <div class="panel">
      <h2>SMB Browser</h2>
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
      <h2>HandBrake Settings</h2>
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
        <label>Audio mode
          <select id="hb-audio-mode" name="audio_mode">
            <option value="encode">Encode (AAC)</option>
            <option value="copy">Copy original</option>
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
        <div class="muted">Applies: Default for regular files, DVD for VIDEO_TS, BR for BDMV/STREAM.</div>
      </form>
    </div>
    <div class="panel">
      <h2>MakeMKV Settings</h2>
      <form id="makemkv-form">
        <label>Rip directory <input id="mk-ripdir" name="rip_dir" /></label>
        <label>Min title length (seconds) <input id="mk-minlen" name="min_length" type="number" step="60" /></label>
        <button type="button" id="mk-save">Save MakeMKV</button>
      </form>
    </div>
    <div class="panel" style="grid-column: 1 / -1;">
      <div style="display:flex; align-items:center; gap:10px; margin-bottom:6px; justify-content: space-between;">
        <h2 style="margin:0;">Logs</h2>
        <button id="copy-logs" style="padding:6px 10px; background:#2563eb; color:#fff; border:0; border-radius:6px; cursor:pointer;">Copy last 300</button>
      </div>
      <div id="logs" class="log"></div>
    </div>
  </div>
  <script>
    let hbDirty = false;
    let mkDirty = false;

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
        const stopBtn = state === "running" ? '<button class="stop-btn" data-src="' + encodeURIComponent(item.source || "") + '">Stop</button>' : "";
        const infoLine = item.info ? '<div class="muted">' + item.info + '</div>' : "";
        return [
          '<div class="item">',
          '  <div class="flex-between">',
          '    <div class="path">' + (item.source || "") + '</div>',
          '    <div>' + badge + ' ' + stopBtn + '</div>',
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
      setSelectValue(document.getElementById("hb-dvd-quality"), cfg.handbrake_dvd.quality, 20);
      setSelectValue(document.getElementById("hb-br-quality"), cfg.handbrake_br.quality, 25);
      setSelectValue(document.getElementById("hb-ext"), cfg.handbrake.extension, ".mkv");
      setSelectValue(document.getElementById("hb-audio-mode"), cfg.handbrake.audio_mode || "encode", "encode");
      setSelectValue(document.getElementById("hb-audio-bitrate"), cfg.handbrake.audio_bitrate_kbps || 128, 128);
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
      const body = {
        profile: "handbrake",
        handbrake: {
          encoder: document.getElementById("hb-encoder").value,
          quality: qDefault,
          extension: ext,
          audio_mode: audioMode,
          audio_bitrate_kbps: audioBitrate
        },
        handbrake_dvd: { quality: qDvd, extension: ext, audio_mode: audioMode, audio_bitrate_kbps: audioBitrate },
        handbrake_br: { quality: qBr, extension: ext, audio_mode: audioMode, audio_bitrate_kbps: audioBitrate }
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
      const body = {
        rip_dir: document.getElementById("mk-ripdir").value,
        makemkv_minlength: Number(document.getElementById("mk-minlen").value)
      };
      await fetch("/api/config", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
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
        await navigator.clipboard.writeText(text);
        alert("Copied last " + lines.length + " log lines to clipboard.");
      } catch (e) {
        alert("Failed to copy logs: " + e);
      }
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
        const path = mounts[id];
        return '<div class="smb-item"><div class="smb-path">' + id + ' → ' + path + '</div><button class="smb-btn smb-unmount" data-id="' + id + '">Unmount</button></div>';
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

    document.getElementById("smb-refresh").addEventListener("click", async () => {
      await smbRefreshMounts();
      await smbList();
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
        # Escape spaces for mount.cifs
        return url.replace(" ", r"\040")

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
        tracker.add_smb_mount(mid, str(mnt))
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
        mnt = mounts.get(mount_id)
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
        mnt = mounts.get(mid)
        if not mnt:
            return jsonify({"error": "mount not found"}), 400
        base = pathlib.Path(mnt)
        target = ensure_under(base, base / rel_path.lstrip("/"))
        if not target.is_file():
            return jsonify({"error": "file not found"}), 400
        dest_root = pathlib.Path("/mnt/input")
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
        tracker.add_event(f"Copied from SMB and queued: {target} -> {dest}")
        return jsonify({"queued": str(dest), "source": str(target)})

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
