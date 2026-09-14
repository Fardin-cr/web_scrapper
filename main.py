"""
main.py — Entry point
Usage:
    python main.py scrape    # scrape ~2000 Steam games
    python main.py model     # run K-Means clustering
    python main.py server    # start web UI at http://localhost:5000
"""
import sys, subprocess, webbrowser
from pathlib import Path

ROOT = Path(__file__).parent

def scrape():
    print("Scraping Steam games (this takes a few minutes)...")
    subprocess.run(["scrapy", "crawl", "steam"], cwd=ROOT)

def model():
    import model as m
    m.run()

def server():
    import server as s
    print("Opening http://localhost:5000")
    s.app.run(debug=False, port=5000)

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if   cmd == "scrape": scrape()
    elif cmd == "model" : model()
    elif cmd == "server": server()
    else: print(__doc__)
