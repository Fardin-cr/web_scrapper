import scrapy

class SteamGameItem(scrapy.Item):
    app_id         = scrapy.Field()
    title          = scrapy.Field()
    genre          = scrapy.Field()
    price          = scrapy.Field()
    original_price = scrapy.Field()
    discount       = scrapy.Field()
    rating         = scrapy.Field()
    review_count   = scrapy.Field()
    developer      = scrapy.Field()
    release_date   = scrapy.Field()
    tags           = scrapy.Field()
    os_support     = scrapy.Field()
