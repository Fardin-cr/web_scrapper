BOT_NAME    = "steam_scraper"
SPIDER_MODULES   = ["scraper.spiders"]
NEWSPIDER_MODULE = "scraper.spiders"

# Polite scraping settings
DOWNLOAD_DELAY              = 1.5
RANDOMIZE_DOWNLOAD_DELAY    = True
CONCURRENT_REQUESTS         = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 4
AUTOTHROTTLE_ENABLED        = True
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0
RETRY_TIMES                 = 3
RETRY_HTTP_CODES            = [500, 502, 503, 504, 429]

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
              "AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/125.0.0.0 Safari/537.36")

ITEM_PIPELINES   = {"scraper.pipelines.SteamPipeline": 100}
COOKIES_ENABLED  = True
ROBOTSTXT_OBEY   = False
HTTPCACHE_ENABLED = False
FEED_EXPORT_ENCODING = "utf-8"
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
