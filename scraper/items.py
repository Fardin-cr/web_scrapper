import scrapy

class SteamGameItem(scrapy.Item):
    app_id        = scrapy.Field()
    title         = scrapy.Field()
    price         = scrapy.Field()
    original_price= scrapy.Field()
    discount      = scrapy.Field()
    rating        = scrapy.Field()
    review_count  = scrapy.Field()
    release_date  = scrapy.Field()
    developer     = scrapy.Field()
    genre         = scrapy.Field()
    tags          = scrapy.Field()
    os_support    = scrapy.Field()
    scraped_at    = scrapy.Field()
