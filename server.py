"""
server.py — Flask backend for SteamLens dashboard
"""
import io, csv, sys, sqlite3, threading, traceback, importlib
from pathlib import Path
from flask import Flask, jsonify, request, send_file, send_from_directory

ROOT   = Path(__file__).parent
DB     = ROOT / "data" / "steam_games.db"
PYTHON = sys.executable

app = Flask(__name__, static_folder=str(ROOT / "dashboard"))

# ── CORS headers on every response ────────────────────────────────────────
@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response

# ── Shared state ──────────────────────────────────────────────────────────
state = {"running": False, "task": "", "log": [], "done": False, "error": None}

def log(msg):
    """Add a line to the log and print it to terminal."""
    print(msg, flush=True)
    state["log"].append(str(msg))
    if len(state["log"]) > 300:
        state["log"] = state["log"][-300:]

# ── Run scraper in subprocess ─────────────────────────────────────────────
def _run_scraper():
    import subprocess, os, sys
    state.update(running=True, task="Scraper", log=[], done=False, error=None)
    log("[SCRAPER] Starting...")
    try:
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        proc = subprocess.Popen(
            [sys.executable, "-m", "scrapy", "crawl", "steam"],
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env
        )
        log(f"[SCRAPER] PID {proc.pid}")
        for line in proc.stdout:
            log(line.rstrip())
        proc.wait()
        if proc.returncode == 0:
            state["error"] = None
            log("[SCRAPER] Done.")
        else:
            state["error"] = f"Exited with code {proc.returncode}"
    except Exception as e:
        state["error"] = str(e)
        log(f"[SCRAPER] Error: {e}")
        log(traceback.format_exc())
    finally:
        state.update(running=False, done=True)

# ── Run model directly in-process ─────────────────────────────────────────
def _run_model():
    state.update(running=True, task="Clustering", log=[], done=False, error=None)
    log("[MODEL] Starting K-Means clustering...")
    buf = io.StringIO()
    try:
        sys.path.insert(0, str(ROOT))
        if "model" in sys.modules:
            importlib.reload(sys.modules["model"])
        else:
            import model  # noqa
        from contextlib import redirect_stdout, redirect_stderr
        with redirect_stdout(buf), redirect_stderr(buf):
            sys.modules["model"].run()
        for line in buf.getvalue().splitlines():
            log(line)
        state["error"] = None
        log("[MODEL] Done successfully.")
    except Exception as e:
        state["error"] = str(e)
        log(f"[MODEL] Exception: {e}")
        log(traceback.format_exc())
        for line in buf.getvalue().splitlines():
            log(line)
    finally:
        state.update(running=False, done=True)

# ── Routes ────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(str(ROOT / "dashboard"), "index.html")

@app.route("/<path:filename>")
def static_file(filename):
    return send_from_directory(str(ROOT / "dashboard"), filename)

@app.route("/api/data")
def api_data():
    if not DB.exists():
        return jsonify([])
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM games ORDER BY review_count DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/scrape", methods=["GET", "POST", "OPTIONS"])
def api_scrape():
    if request.method == "OPTIONS":
        return "", 204
    if state["running"]:
        return jsonify({"error": "A task is already running"}), 409
    threading.Thread(target=_run_scraper, daemon=True).start()
    return jsonify({"status": "started"})

@app.route("/api/model", methods=["GET", "POST", "OPTIONS"])
def api_model():
    if request.method == "OPTIONS":
        return "", 204
    if state["running"]:
        return jsonify({"error": "A task is already running"}), 409
    threading.Thread(target=_run_model, daemon=True).start()
    return jsonify({"status": "started"})

@app.route("/api/debug")
def api_debug():
    return jsonify({
        "version": "v3-clean-rewrite",
        "python":  str(PYTHON),
        "root":    str(ROOT),
        "db":      str(DB.exists()),
        "state":   state
    })

@app.route("/api/status")
def api_status():
    return jsonify({
        "running": state["running"],
        "task":    state["task"],
        "done":    state["done"],
        "error":   state["error"],
        "log":     state["log"][-50:]
    })

@app.route("/api/export")
def api_export():
    if not DB.exists():
        return jsonify({"error": "No data"}), 404
    genre  = request.args.get("genre",  "")
    rating = request.args.get("rating", "")
    price  = request.args.get("price",  "")
    q      = request.args.get("q",      "").lower()

    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute("SELECT * FROM games").fetchall()]
    conn.close()

    filtered = []
    for r in rows:
        p  = float(r.get("price") or 0)
        rt = str(r.get("rating") or "")
        if genre  and r.get("genre") != genre: continue
        if q      and q not in f"{r.get('title','')} {r.get('developer','')} {r.get('tags','')}".lower(): continue
        if rating == "pos"   and "positive" not in rt.lower(): continue
        if rating == "mixed" and "mixed"    not in rt.lower(): continue
        if rating == "neg"   and "negative" not in rt.lower(): continue
        if price  == "free"  and p != 0:         continue
        if price  == "u10"   and (p == 0 or p >= 10): continue
        if price  == "u20"   and (p == 0 or p >= 20): continue
        if price  == "o20"   and p < 20:          continue
        filtered.append(r)

    if not filtered:
        return jsonify({"error": "No data matches"}), 404

    # Export WITHOUT scraped_at column
    fields = ["app_id","title","genre","price","original_price",
              "discount","rating","review_count","release_date",
              "developer","tags","os_support"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore", lineterminator="\r\n")
    w.writeheader()
    w.writerows(filtered)
    mem = io.BytesIO(buf.getvalue().encode("utf-8-sig"))
    mem.seek(0)
    return send_file(mem, mimetype="text/csv", as_attachment=True,
                     download_name="steam_games.csv")

# ── Start ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "reports").mkdir(exist_ok=True)
    print(f"\n  SteamLens  →  http://localhost:5001")
    print(f"  Python     →  {PYTHON}\n")
    app.run(debug=False, port=5001, use_reloader=False)