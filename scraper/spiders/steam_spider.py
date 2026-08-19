import scrapy
import re
from urllib.parse import urlencode
from scraper.items import SteamGameItem


class SteamSpider(scrapy.Spider):
    name = "steam"
    allowed_domains = ["store.steampowered.com"]

    # Scalable: add more categories here to collect more rows
    ALL_CATEGORIES = [
        ("Action",          "19"),
        ("Adventure",       "25"),
        ("RPG",             "122"),
        ("Strategy",        "9"),
        ("Simulation",      "28"),
        ("Indie",           "492"),
        ("Sports",          "18"),
        ("Racing",          "699"),
        ("Casual",          "597"),
        ("Free to Play",    "113"),
    ]

    TEST_CATEGORIES = [
        ("Action",  "19"),
        ("RPG",     "122"),
    ]

    MAX_PAGES      = 8   # full run: 8 × 25 × 10 = 2000 games
    TEST_MAX_PAGES = 1   # test run: 1 × 25 × 2  = ~50 games

    custom_settings = {
        "DOWNLOADER_MIDDLEWARES": {
            "scraper.middlewares.RotateUserAgentMiddleware": 400,
            "scraper.middlewares.SteamAgeCheckMiddleware": 401,
        },
        "COOKIES_ENABLED": True,
    }

    def start_requests(self):
        test_mode    = getattr(self, 'test', 'false').lower() == 'true'
        filter_genre = getattr(self, 'filter_genre', '').strip()

        # Respect max_pages argument from server; fall back to defaults
        if test_mode:
            max_pages = int(getattr(self, 'max_pages', self.TEST_MAX_PAGES))
        else:
            max_pages = int(getattr(self, 'max_pages', self.MAX_PAGES))

        # Filter to one genre if requested, otherwise use full/test category list
        if filter_genre:
            categories = [(cat_name, cat_id) for cat_name, cat_id in self.ALL_CATEGORIES
                          if cat_name.lower() == filter_genre.lower()]
            if not categories:
                self.logger.warning(f"Unknown genre '{filter_genre}', scraping all")
                categories = self.ALL_CATEGORIES
        elif test_mode:
            categories = self.TEST_CATEGORIES
        else:
            categories = self.ALL_CATEGORIES

        self.logger.info(f"Scraping {len(categories)} genre(s) × {max_pages} page(s) "
                         f"≈ {len(categories) * max_pages * 25} games")

        for cat_name, cat_id in categories:
            for page in range(1, max_pages + 1):
                params = {
                    "category1": "998",
                    "tags":       cat_id,
                    "sort_by":    "Reviews_DESC",
                    "page":       page,
                    "count":      "25",
                }
                url = f"https://store.steampowered.com/search/results/?{urlencode(params)}"
                yield scrapy.Request(
                    url,
                    callback=self.parse_search,
                    cookies={"birthtime": "786240001", "mature_content": "1"},
                    meta={"category": cat_name, "page": page},
                )

    def parse_search(self, response):
        category = response.meta["category"]
        games = response.css("a.search_result_row")

        if not games:
            self.logger.warning(f"No games found on page {response.meta['page']} for {category}")
            return

        for game in games:
            app_id = game.attrib.get("data-ds-appid", "")
            if not app_id:
                continue

            title = game.css(".title::text").get("").strip()
            release = game.css(".search_released::text").get("").strip()

            # Price extraction — Steam uses different structures for free/paid/discounted
            discount_pct = game.css(".search_discount span::text").get("0").strip()
            original = game.css(".search_price strike::text").get("").strip()
            # Try discount_final_price first (discounted items), then the generic price column
            final_price = (
                game.css(".discount_final_price::text").get("").strip()
                or game.css(".search_price::text").getall()
            )
            if isinstance(final_price, list):
                final_price = " ".join(t for t in final_price if t.strip()).strip()
            # Normalise "Free to Play" / "Free" → "0"
            if not final_price or re.search(r"free", final_price, re.I):
                final_price = "0"

            # Reviews
            review_el = game.css(".search_review_summary")
            review_tooltip = review_el.attrib.get("data-tooltip-html", "")
            rating, review_count = self._parse_reviews(review_tooltip)

            item = SteamGameItem(
                app_id=app_id,
                title=title,
                price=final_price or "0",
                original_price=original or final_price or "0",
                discount=discount_pct,
                rating=rating,
                review_count=review_count,
                release_date=release,
                developer="",
                genre=category,
                tags=[],
                os_support=self._get_os(game),
            )

            # Fetch detail page for developer + tags
            detail_url = f"https://store.steampowered.com/app/{app_id}/"
            yield scrapy.Request(
                detail_url,
                callback=self.parse_detail,
                cookies={"birthtime": "786240001", "mature_content": "1"},
                meta={"item": item},
                dont_filter=False,
            )

    def parse_detail(self, response):
        item = response.meta["item"]

        developer = response.css("#developers_list a::text").get("").strip()
        if not developer:
            developer = response.css(".dev_row .summary.column a::text").get("").strip()
        item["developer"] = developer

        tags = response.css("a.app_tag::text").getall()
        item["tags"] = [t.strip() for t in tags if t.strip()][:8]

        yield item

    def _parse_reviews(self, tooltip: str):
        rating = ""
        count = 0
        if not tooltip:
            return rating, count
        # e.g. "Overwhelmingly Positive<br>95% of the 123,456 user reviews..."
        parts = re.split(r"<br>|<br/>", tooltip)
        if parts:
            rating = re.sub(r"<[^>]+>", "", parts[0]).strip()
        match = re.search(r"([\d,]+)\s+user review", tooltip)
        if match:
            count = int(match.group(1).replace(",", ""))
        return rating, count

    def _get_os(self, sel):
        os_list = []
        if sel.css(".platform_img.win"):
            os_list.append("Windows")
        if sel.css(".platform_img.mac"):
            os_list.append("Mac")
        if sel.css(".platform_img.linux"):
            os_list.append("Linux")
        return os_list
