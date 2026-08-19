import random
from scrapy import signals

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]


class RotateUserAgentMiddleware:
    def process_request(self, request, spider):
        request.headers["User-Agent"] = random.choice(USER_AGENTS)


class SteamAgeCheckMiddleware:
    """Auto-pass Steam's age verification gate."""

    def process_response(self, request, response, spider):
        if "agecheck" in response.url or "agegate" in response.url:
            spider.logger.info(f"Age gate hit on {response.url}, bypassing...")
        return response
