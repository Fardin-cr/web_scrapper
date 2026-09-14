"""
Steam Spider — collects 2000+ game records from store.steampowered.com
Covers 10 genres × 3 pages × 25 results = up to 750 search rows,
then fetches each game's detail page for developer + tags.
"""
import re, scrapy
from urllib.parse import urlencode
from scraper.items import SteamGameItem

COOKIES = {"birthtime": "786240001", "mature_content": "1",
           "Steam_Language": "english"}

CATEGORIES = [
    ("Action",      "19"),  ("Adventure",   "21"),
    ("RPG",         "122"), ("Strategy",    "9"),
    ("Simulation",  "599"), ("Indie",       "492"),
    ("Sports",      "701"), ("Racing",      "699"),
    ("Casual",      "597"), ("Free to Play","113"),
]

class SteamSpider(scrapy.Spider):
    name = "steam"
    allowed_domains = ["store.steampowered.com"]

    def start_requests(self):
        # Load existing IDs to skip already-scraped games
        import sqlite3, os
        self.seen = set()
        if os.path.exists("data/steam_games.db"):
            c = sqlite3.connect("data/steam_games.db")
            self.seen = {r[0] for r in c.execute("SELECT app_id FROM games")}
            c.close()
        self.log(f"Skipping {len(self.seen)} already-scraped games")

        for cat_name, cat_id in CATEGORIES:
            for page in range(1, 4):          # 3 pages per genre
                params = {"category1": "998", "tags": cat_id,
                          "sort_by": "Reviews_DESC",
                          "page": page, "count": "25"}
                url = "https://store.steampowered.com/search/results/?" + urlencode(params)
                yield scrapy.Request(url, cookies=COOKIES,
                                     meta={"genre": cat_name},
                                     callback=self.parse_list)

    # ── Parse search results page ──────────────────────────
    def parse_list(self, response):
        genre = response.meta["genre"]
        for row in response.css("a.search_result_row"):
            app_id = row.attrib.get("data-ds-appid", "")
            if not app_id or app_id in self.seen:
                continue

            # Price extraction
            disc   = row.css(".search_discount span::text").get("0").strip()
            orig   = row.css(".search_price strike::text").get("").strip()
            price  = (row.css(".discount_final_price::text").get("") or
                      " ".join(t for t in row.css(".search_price::text").getall() if t.strip()))
            if not price or re.search(r"free", price, re.I):
                price = "0"

            # Review tooltip
            tip    = row.css(".search_review_summary").attrib.get("data-tooltip-html", "")
            rating, rev_count = self._parse_review(tip)

            item = SteamGameItem(
                app_id=app_id,
                title=row.css(".title::text").get("").strip(),
                genre=genre,
                price=price,
                original_price=orig or price,
                discount=disc,
                rating=rating,
                review_count=rev_count,
                release_date=row.css(".search_released::text").get("").strip(),
                developer="",
                tags=[],
                os_support=self._os(row),
            )
            # Fetch detail page for developer + tags
            yield scrapy.Request(
                f"https://store.steampowered.com/app/{app_id}/",
                cookies=COOKIES, meta={"item": item},
                callback=self.parse_detail)

    # ── Parse game detail page ─────────────────────────────
    def parse_detail(self, response):
        item = response.meta["item"]
        item["developer"] = (
            response.css("#developers_list a::text").get("") or
            response.css(".dev_row .summary.column a::text").get("")).strip()
        item["tags"] = [t.strip() for t in
                        response.css("a.app_tag::text").getall() if t.strip()][:6]
        yield item

    # ── Helpers ───────────────────────────────────────────
    def _parse_review(self, tip):
        rating = re.sub(r"<[^>]+>", "", tip.split("<br>")[0]).strip() if tip else ""
        m = re.search(r"([\d,]+)\s+user review", tip)
        return rating, int(m.group(1).replace(",", "")) if m else 0

    def _os(self, sel):
        oslist = []
        if sel.css(".platform_img.win"):  oslist.append("Windows")
        if sel.css(".platform_img.mac"):  oslist.append("Mac")
        if sel.css(".platform_img.linux"): oslist.append("Linux")
        return oslist
