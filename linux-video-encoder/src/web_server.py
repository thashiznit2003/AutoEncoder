from flask import Flask, jsonify, Response

HTML_PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Linux Video Encoder</title>
  <style>
    :root { color-scheme: dark; font-family: "Segoe UI", Arial, sans-serif; }
    body { margin: 0; background: #0f172a; color: #e2e8f0; }
    header { padding: 12px 16px; background: #111827; border-bottom: 1px solid #1f2937; display: flex; justify-content: space-between; align-items: center; }
    h1 { font-size: 18px; margin: 0; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); grid-auto-rows: minmax(240px, auto); gap: 12px; padding: 12px; }
    .panel { background: #111827; border: 1px solid #1f2937; border-radius: 10px; padding: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); }
    .panel h2 { margin: 0 0 8px 0; font-size: 15px; color: #93c5fd; }
    .log { font-family: "SFMono-Regular", Menlo, Consolas, monospace; font-size: 12px; background: #0b1220; border-radius: 8px; padding: 10px; overflow: auto; height: 320px; border: 1px solid #1f2937; }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 11px; color: #0f172a; font-weight: 600; }
    .badge.running { background: #fde047; }
    .badge.success { background: #34d399; }
    .badge.error { background: #f87171; }
    .item { padding: 8px; border-bottom: 1px solid #1f2937; }
    .item:last-child { border-bottom: 0; }
    .muted { color: #94a3b8; }
    .flex-between { display: flex; justify-content: space-between; gap: 8px; align-items: center; }
    .path { word-break: break-all; }
  </style>
</head>
<body>
  <header>
    <h1>Linux Video Encoder - Live Status</h1>
    <div id="clock" class="muted"></div>
  </header>
  <div class="grid">
    <div class="panel">
      <h2>Active Encodes</h2>
      <div id="active"></div>
    </div>
    <div class="panel">
      <h2>Recent Jobs</h2>
      <div id="recent"></div>
    </div>
    <div class="panel" style="grid-column: 1 / -1;">
      <h2>Logs</h2>
      <div id="logs" class="log"></div>
    </div>
  </div>
  <script>
    async function fetchJSON(url) {
      const res = await fetch(url);
      return res.json();
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
        container.innerHTML = `<div class="muted">${empty}</div>`;
        return;
      }
      container.innerHTML = items.map(item => {
        const badge = `<span class="badge ${item.state}">${item.state.toUpperCase()}</span>`;
        const duration = item.duration_sec ? fmtDuration(item.duration_sec) : (item.finished_at && item.started_at ? fmtDuration(item.finished_at - (item.started_at || item.finished_at)) : "");
        return `<div class="item">
          <div class="flex-between">
            <div class="path">${item.source || ""}</div>
            <div>${badge}</div>
          </div>
          <div class="muted">-> ${item.destination || ""}</div>
          <div class="muted">${item.message || ""}</div>
          <div class="muted">${duration ? "Duration: " + duration : ""}</div>
        </div>`;
      }).join("");
    }

    async function refresh() {
      try {
        const status = await fetchJSON("/api/status");
        renderList(document.getElementById("active"), status.active, "No active encodes.");
        renderList(document.getElementById("recent"), status.recent, "No recent jobs.");
      } catch (e) {
        document.getElementById("active").innerHTML = "<div class='muted'>Status unavailable.</div>";
        document.getElementById("recent").innerHTML = "<div class='muted'>Status unavailable.</div>";
      }
      try {
        const logs = await fetchJSON("/api/logs");
        document.getElementById("logs").textContent = logs.lines.join("\\n");
      } catch (e) {
        document.getElementById("logs").textContent = "Logs unavailable.";
      }
    }

    function tickClock() {
      const now = new Date();
      document.getElementById("clock").textContent = now.toLocaleString();
    }

    setInterval(refresh, 2000);
    setInterval(tickClock, 1000);
    refresh();
    tickClock();
  </script>
</body>
</html>
"""


def create_app(tracker):
    app = Flask(__name__)

    @app.route("/")
    def index():
        return Response(HTML_PAGE, mimetype="text/html")

    @app.route("/api/status")
    def status():
        return jsonify(tracker.snapshot())

    @app.route("/api/logs")
    def logs():
        return jsonify({"lines": tracker.tail_logs()})

    return app


def start_web_server(tracker, port: int = 5959):
    app = create_app(tracker)

    def _run():
        app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False, threaded=True)

    import threading

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t
