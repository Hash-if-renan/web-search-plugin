from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.async_configs import CacheMode
from typing import Dict, List, Optional, Any
import asyncio


class Crawler:
    """
    A class for scraping websites using crawl4ai's AsyncWebCrawler.

    This class provides a convenient interface for configuring and running web crawls,
    and accessing the results in a structured way.
    """

    def __init__(
        self,
        word_count_threshold: int = 10,
        excluded_tags: List[str] = None,
        exclude_external_links: bool = True,
        process_iframes: bool = True,
        remove_overlay_elements: bool = True,
        cache_mode: CacheMode = CacheMode.ENABLED,
        exclude_internal_links: bool = True,
    ):
        """
        Initialize the WebsiteScraper with default or custom configuration.

        Args:
            word_count_threshold: Minimum word count for content to be included
            excluded_tags: HTML tags to exclude from the results
            exclude_external_links: Whether to exclude links to external sites
            process_iframes: Whether to process content within iframes
            remove_overlay_elements: Whether to remove overlay elements like popups
            cache_mode: Cache mode for the crawler (ENABLED, DISABLED, or FORCE_REFRESH)
        """
        self.browser_config = BrowserConfig()

        if excluded_tags is None:
            excluded_tags = ["form", "header"]

        self.default_run_config = CrawlerRunConfig(
            word_count_threshold=word_count_threshold,
            excluded_tags=excluded_tags,
            exclude_external_links=exclude_external_links,
            process_iframes=process_iframes,
            remove_overlay_elements=remove_overlay_elements,
            cache_mode=cache_mode,
            exclude_internal_links=exclude_internal_links,
        )

    async def crawl(
        self, url: str, custom_config: Optional[CrawlerRunConfig] = None
    ) -> Dict[str, Any]:
        """
        Crawl the specified URL and return the results.

        Args:
            url: The URL to crawl
            custom_config: Optional custom configuration to override defaults

        Returns:
            A dictionary containing all crawl results including:
            - markdown: Raw and fitted markdown content
            - html: Raw and cleaned HTML
            - success: Whether the crawl succeeded
            - status_code: HTTP status code
            - media: Extracted media
            - links: Found links
        """
        run_config = (
            custom_config if custom_config is not None else self.default_run_config
        )

        async with AsyncWebCrawler(config=self.browser_config) as crawler:
            result = await crawler.arun(url=url, config=run_config)

            return {
                "markdown": {
                    "raw": result.markdown.raw_markdown,
                    "fitted": result.markdown.fit_markdown,
                },
                "html": {"raw": result.html, "cleaned": result.cleaned_html},
                "success": result.success,
                "status_code": result.status_code,
                "media": result.media,
                "links": result.links,
            }


# Example usage:


# To run the example:
if __name__ == "__main__":

    async def example_usage():
        scraper = Crawler()
        results = await scraper.crawl("https://docs.zyte.com/zyte-api/pricing.html")

        # Access different parts of the results
        print(results["markdown"]["raw"])  # Raw markdown content
        # print(results["success"])  # Whether the crawl succeeded
        # print(results["links"])  # All found links

    asyncio.run(example_usage())
