import sqlite3
import csv
import re
import os
from datetime import datetime
from itemadapter import ItemAdapter


class CleaningPipeline:
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        # Clean price — strip currency symbols
        for field in ("price", "original_price"):
            val = adapter.get(field, "")
            if isinstance(val, str):
                cleaned = re.sub(r"[^\d.]", "", val)
                adapter[field] = float(cleaned) if cleaned else 0.0

        # Clean discount
        discount = adapter.get("discount", "0")
        if isinstance(discount, str):
            cleaned = re.sub(r"[^\d]", "", discount)
            adapter["discount"] = int(cleaned) if cleaned else 0

        # Clean review count
        rc = adapter.get("review_count", "0")
        if isinstance(rc, str):
            cleaned = re.sub(r"[^\d]", "", rc)
            adapter["review_count"] = int(cleaned) if cleaned else 0

        # Tags list to comma string
        tags = adapter.get("tags", [])
        if isinstance(tags, list):
            adapter["tags"] = ", ".join(tags[:5])

        # OS list to comma string
        os_list = adapter.get("os_support", [])
        if isinstance(os_list, list):
            adapter["os_support"] = ", ".join(os_list)

        adapter["scraped_at"] = datetime.utcnow().isoformat()

        return item


class SQLitePipeline:
    def open_spider(self, spider):
        os.makedirs("data/processed", exist_ok=True)
        self.conn = sqlite3.connect("data/processed/steam_games.db")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS games (
                app_id         TEXT PRIMARY KEY,
                title          TEXT,
                price          REAL,
                original_price REAL,
                discount       INTEGER,
                rating         TEXT,
                review_count   INTEGER,
                release_date   TEXT,
                developer      TEXT,
                genre          TEXT,
                tags           TEXT,
                os_support     TEXT,
                scraped_at     TEXT
            )
        """)
        self.conn.commit()

    def close_spider(self, spider):
        self.conn.close()

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        self.conn.execute("""
            INSERT OR REPLACE INTO games VALUES (
                :app_id, :title, :price, :original_price, :discount,
                :rating, :review_count, :release_date, :developer,
                :genre, :tags, :os_support, :scraped_at
            )
        """, dict(adapter))
        self.conn.commit()
        return item


class CSVPipeline:
    def open_spider(self, spider):
        os.makedirs("data/processed", exist_ok=True)
        self.file = open("data/processed/steam_games_raw.csv", "w", newline="", encoding="utf-8")
        self.writer = None

    def close_spider(self, spider):
        self.file.close()

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        if self.writer is None:
            self.writer = csv.DictWriter(self.file, fieldnames=adapter.field_names())
            self.writer.writeheader()
        self.writer.writerow(dict(adapter))
        return item
