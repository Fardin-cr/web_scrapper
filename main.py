"""
Entry point — run the Steam scraper then launch the dashboard.
Usage:
    python main.py scrape       # collect 2000+ games (20-40 min)
    python main.py test         # collect ~50 games in ~30 seconds
    python main.py server       # start Flask dashboard at http://localhost:5000
    python main.py dashboard    # open static dashboard in browser
    python main.py all          # scrape then open dashboard
"""
import sys
import subprocess
import webbrowser
from pathlib import Path


ROOT = Path(__file__).parent


def run_scraper(test_mode=False):
    if test_mode:
        print("=" * 50)
        print("  TEST MODE — Steam Games Scraper")
        print("  Target: ~50 games in ~30 seconds")
        print("  Categories: Action, RPG (1 page each)")
        print("=" * 50)
        extra_args = ["-s", "spider.test=true", "-a", "test=true"]
    else:
        print("=" * 50)
        print("  FULL RUN — Steam Games Scraper")
        print("  Target: 2000+ games across 10 categories")
        print("  Estimated time: 20-40 minutes")
        print("=" * 50)
        extra_args = []

    result = subprocess.run(
        ["scrapy", "crawl", "steam", "-s", "LOG_LEVEL=INFO"] + extra_args,
        cwd=ROOT,
    )

    if result.returncode == 0:
        csv_path = ROOT / "data" / "processed" / "steam_games.csv"
        if csv_path.exists():
            with open(csv_path, encoding='utf-8') as f:
                rows = sum(1 for _ in f) - 1
            print(f"\n✓ Done! {rows} games saved to data/processed/steam_games.csv")
        else:
            print("\n✓ Scraping complete.")
    else:
        print("\n✗ Scraper exited with errors.")

    return result.returncode


def open_dashboard():
    dashboard = ROOT / "dashboard" / "index.html"
    if not dashboard.exists():
        print("Dashboard not found at dashboard/index.html")
        return
    print(f"Opening dashboard in browser...")
    webbrowser.open(dashboard.as_uri())


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"

    if cmd == "scrape":
        run_scraper()

    elif cmd == "test":
        code = run_scraper(test_mode=True)
        if code == 0:
            open_dashboard()

    elif cmd == "server":
        import server as srv
        srv.app.run(debug=False, port=5000)

    elif cmd == "dashboard":
        open_dashboard()

    elif cmd == "all":
        code = run_scraper()
        if code == 0:
            open_dashboard()

    else:
        print(__doc__)
