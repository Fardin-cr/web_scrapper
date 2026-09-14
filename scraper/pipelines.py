"""
Pipeline: cleans each scraped item and saves it to SQLite.
Data Cleaning steps:
  - Strip currency symbols from price fields
  - Convert discount / review_count to integers
  - Join tags and OS lists into comma-separated strings
  - Fill missing values with safe defaults
"""
import os, re, sqlite3
from itemadapter import ItemAdapter

DB = "data/steam_games.db"

class SteamPipeline:
    # ── open DB ────────────────────────────────────────────
    def open_spider(self, spider):
        os.makedirs("data", exist_ok=True)
        self.conn = sqlite3.connect(DB)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS games (
                app_id         TEXT PRIMARY KEY,
                title          TEXT,
                genre          TEXT,
                price          REAL,
                original_price REAL,
                discount       INTEGER,
                rating         TEXT,
                review_count   INTEGER,
                developer      TEXT,
                release_date   TEXT,
                tags           TEXT,
                os_support     TEXT
            )""")
        self.conn.commit()
        self.seen = {r[0] for r in
                     self.conn.execute("SELECT app_id FROM games")}

    def close_spider(self, spider):
        self.conn.close()

    # ── clean + save ───────────────────────────────────────
    def process_item(self, item, spider):
        a = ItemAdapter(item)
        if a["app_id"] in self.seen:
            return item                        # skip duplicate

        # Clean price fields
        for f in ("price", "original_price"):
            raw = a.get(f, "0") or "0"
            cleaned = re.sub(r"[^\d.]", "", str(raw))
            a[f] = float(cleaned) if cleaned else 0.0

        # Clean discount & review_count to int
        for f in ("discount", "review_count"):
            raw = a.get(f, "0") or "0"
            cleaned = re.sub(r"[^\d]", "", str(raw))
            a[f] = int(cleaned) if cleaned else 0

        # Lists -> comma string
        for f in ("tags", "os_support"):
            val = a.get(f, [])
            a[f] = ", ".join(val) if isinstance(val, list) else str(val or "")

        # Save to DB
        self.conn.execute(
            "INSERT OR REPLACE INTO games "
            "(app_id,title,genre,price,original_price,discount,rating,"
            "review_count,developer,release_date,tags,os_support) "
            "VALUES (:app_id,:title,:genre,:price,:original_price,"
            ":discount,:rating,:review_count,:developer,"
            ":release_date,:tags,:os_support)",
            dict(a))
        self.conn.commit()
        self.seen.add(a["app_id"])
        return item
