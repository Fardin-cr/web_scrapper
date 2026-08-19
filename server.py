"""
Flask server — serves the dashboard and exposes APIs for scraping and export.
Usage: python server.py
Then open: http://localhost:5000
"""
import csv
import io
import json
import subprocess
import threading
from pathlib import Path
from flask import Flask, jsonify, request, send_file, send_from_directory

ROOT     = Path(__file__).parent
DATA_DIR = ROOT / "data" / "processed"
DB_PATH  = DATA_DIR / "steam_games.db"

app = Flask(__name__, static_folder=str(ROOT / "dashboard"))

@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response

@app.route("/api/clear", methods=["OPTIONS"])
@app.route("/api/scrape", methods=["OPTIONS"])
@app.route("/api/export", methods=["OPTIONS"])
def preflight():
    return "", 204

# ── Scrape state ──────────────────────────────────────────
scrape_state = {"running": False, "log": [], "done": False, "error": None, "cleared": False, "proc": None}


def run_spider(genre: str, max_pages: int, test: bool):
    scrape_state["running"] = True
    scrape_state["done"]    = False
    scrape_state["error"]   = None
    scrape_state["log"]     = []
    scrape_state["cleared"] = False

    args = ["scrapy", "crawl", "steam", "-s", "LOG_LEVEL=INFO"]
    if test:
        args += ["-a", "test=true"]
    if genre:
        args += ["-a", f"filter_genre={genre}"]
    args += ["-a", f"max_pages={max_pages}"]

    try:
        proc = subprocess.Popen(
            args, cwd=ROOT,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace"
        )
        scrape_state["proc"] = proc
        for line in proc.stdout:
            line = line.rstrip()
            scrape_state["log"].append(line)
            if len(scrape_state["log"]) > 200:
                scrape_state["log"] = scrape_state["log"][-200:]
        proc.wait()
        scrape_state["error"] = None if proc.returncode == 0 else "Spider exited with errors"
    except Exception as e:
        scrape_state["error"] = str(e)
    finally:
        scrape_state["running"] = False
        scrape_state["done"]    = True
        scrape_state["proc"]    = None


# ── Routes ────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(str(ROOT / "dashboard"), "index.html")


@app.route("/api/data")
def api_data():
    """Return all games from SQLite as JSON array."""
    if scrape_state["cleared"] or not DB_PATH.exists():
        return jsonify([])
    try:
        import sqlite3
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM games ORDER BY review_count DESC").fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/scrape", methods=["POST"])
def api_scrape():
    """Start a scrape job."""
    if scrape_state["running"]:
        return jsonify({"error": "Already running"}), 409

    body      = request.get_json(silent=True) or {}
    genre     = body.get("genre", "")
    max_pages = int(body.get("max_pages", 1))
    test      = body.get("test", True)

    t = threading.Thread(target=run_spider, args=(genre, max_pages, test), daemon=True)
    t.start()
    return jsonify({"status": "started"})


@app.route("/api/scrape/stop", methods=["POST"])
def api_scrape_stop():
    proc = scrape_state.get("proc")
    if proc and scrape_state["running"]:
        proc.terminate()
        return jsonify({"status": "stopped"})
    return jsonify({"status": "not running"})


@app.route("/api/scrape/status")
def api_scrape_status():
    return jsonify({
        "running": scrape_state["running"],
        "done":    scrape_state["done"],
        "error":   scrape_state["error"],
        "log":     scrape_state["log"][-30:],
    })


@app.route("/api/export")
def api_export():
    """Export filtered data as a clean CSV download."""
    if not DB_PATH.exists():
        return jsonify({"error": "No data yet"}), 404

    genre  = request.args.get("genre", "")
    rating = request.args.get("rating", "")
    price  = request.args.get("price", "")
    q      = request.args.get("q", "").lower()

    import sqlite3
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM games").fetchall()
    conn.close()

    games = []
    for row in rows:
        row = dict(row)
        px = _float(row.get("price"))
        rt = row.get("rating", "")
        if genre  and row.get("genre") != genre: continue
        if q      and q not in f"{row.get('title','')} {row.get('developer','')} {row.get('tags','')}".lower(): continue
        if rating == "pos"   and "positive" not in rt.lower(): continue
        if rating == "mixed" and "mixed"    not in rt.lower(): continue
        if rating == "neg"   and "negative" not in rt.lower(): continue
        if price  == "free"  and px != 0:  continue
        if price  == "u10"   and (px == 0 or px >= 10): continue
        if price  == "u20"   and (px == 0 or px >= 20): continue
        if price  == "o20"   and px < 20:  continue
        games.append(row)

    if not games:
        return jsonify({"error": "No data matches filters"}), 404

    # Build clean CSV in memory
    fields = ["app_id","title","genre","price","original_price","discount",
              "rating","review_count","release_date","developer","tags","os_support","scraped_at"]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore", lineterminator="\r\n")
    writer.writeheader()
    writer.writerows(games)

    mem = io.BytesIO(buf.getvalue().encode("utf-8-sig"))  # utf-8-sig = Excel-friendly BOM
    mem.seek(0)
    return send_file(
        mem,
        mimetype="text/csv",
        as_attachment=True,
        download_name="steam_games_export.csv"
    )


@app.route("/api/clear", methods=["DELETE"])
def api_clear():
    """Clear all game rows from SQLite."""
    if scrape_state["running"]:
        return jsonify({"error": "Cannot clear while scraping"}), 409
    scrape_state["cleared"] = True
    if DB_PATH.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(str(DB_PATH))
            conn.execute("DELETE FROM games")
            conn.commit()
            conn.close()
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"status": "cleared"})


# ── Helpers ───────────────────────────────────────────────
def _float(v):
    try: return round(float(v), 2)
    except: return 0.0

def _int(v):
    try: return int(str(v).replace(",",""))
    except: return 0


if __name__ == "__main__":
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print("\n  SteamLens server running at http://localhost:5000\n")
    app.run(debug=False, port=5000)
