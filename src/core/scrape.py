from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.async_configs import CacheMode
from crawl4ai.async_dispatcher import MemoryAdaptiveDispatcher, SemaphoreDispatcher
from crawl4ai import RateLimiter, CrawlerMonitor, DisplayMode
from typing import Dict, List, Optional, Any, Union, Tuple
import asyncio
import pprint


class Crawl4AIScraper:
    """
    A high-level web crawler with advanced multi-URL scraping capabilities.

    Features:
    - Single URL scraping with customizable configuration
    - Batch URL processing with different dispatcher strategies
    - Streaming mode for real-time results
    - Memory management and rate limiting
    - Real-time monitoring
    """

    def __init__(
        self,
        # Basic crawling config
        word_count_threshold: int = 10,
        excluded_tags: List[str] = None,
        exclude_external_links: bool = True,
        process_iframes: bool = True,
        remove_overlay_elements: bool = True,
        cache_mode: CacheMode = CacheMode.ENABLED,
        # Browser config
        browser_config: Optional[BrowserConfig] = None,
        # Dispatcher defaults
        dispatcher_type: str = "memory_adaptive",  # or "semaphore"
        max_concurrent: int = 10,
        memory_threshold: float = 90.0,
        check_interval: float = 1.0,
        # Rate limiting defaults
        base_delay: Tuple[float, float] = (1.0, 3.0),
        max_delay: float = 60.0,
        max_retries: int = 3,
        rate_limit_codes: List[int] = [429, 503],
        # Monitoring defaults
        monitor: bool = True,
    ):
        """
        Initialize the crawler with comprehensive configuration options.
        """
        self.browser_config = browser_config or BrowserConfig()

        self.default_run_config = CrawlerRunConfig(
            word_count_threshold=word_count_threshold,
            excluded_tags=excluded_tags or ["form", "header"],
            exclude_external_links=exclude_external_links,
            process_iframes=process_iframes,
            remove_overlay_elements=remove_overlay_elements,
            cache_mode=cache_mode,
        )

        # Rate limiter configuration
        self.rate_limiter = RateLimiter(
            base_delay=base_delay,
            max_delay=max_delay,
            max_retries=max_retries,
            rate_limit_codes=rate_limit_codes,
        )

        # Monitor configuration
        self.monitor = CrawlerMonitor() if monitor else None

        # Dispatcher configuration
        self.dispatcher_type = dispatcher_type
        self.max_concurrent = max_concurrent
        self.memory_threshold = memory_threshold
        self.check_interval = check_interval

    async def scrape(
        self, url: str, config: Optional[Union[CrawlerRunConfig, Dict]] = None
    ) -> Dict[str, Any]:
        """Scrape a single URL with optional configuration override."""
        run_config = self._resolve_config(config)

        async with AsyncWebCrawler(config=self.browser_config) as crawler:
            result = await crawler.arun(url=url, config=run_config)
            return self._format_result(result)

    async def scrape_many(
        self,
        urls: List[str],
        config: Optional[Union[CrawlerRunConfig, Dict]] = None,
        dispatcher: Optional[
            Union[MemoryAdaptiveDispatcher, SemaphoreDispatcher]
        ] = None,
        batch_size: int = None,
        check_robots_txt: bool = False,
    ) -> Union[List[Dict[str, Any]], Any]:
        """
        Scrape multiple URLs with advanced dispatching options.

        Args:
            urls: List of URLs to scrape
            config: Optional configuration override
            dispatcher: Custom dispatcher instance
            stream: Whether to stream results as they arrive
            batch_size: Process URLs in batches of this size
            check_robots_txt: Respect robots.txt rules

        Returns:
            List of results if stream=False, async generator if stream=True
        """
        run_config = self._resolve_config(config)
        run_config.check_robots_txt = check_robots_txt

        if dispatcher is None:
            dispatcher = self._create_default_dispatcher()

        async with AsyncWebCrawler(config=self.browser_config) as crawler:
            if batch_size:

                return await self._process_in_batches(
                    crawler, urls, run_config, dispatcher, batch_size
                )
            results = await crawler.arun_many(
                urls=urls, config=run_config, dispatcher=dispatcher
            )
            return [self._format_result(r) for r in results]

    def _create_default_dispatcher(self):
        """Create a dispatcher based on initialization settings."""
        if self.dispatcher_type == "semaphore":
            return SemaphoreDispatcher(
                max_session_permit=self.max_concurrent,
                rate_limiter=self.rate_limiter,
                monitor=self.monitor,
            )

        return MemoryAdaptiveDispatcher(
            memory_threshold_percent=self.memory_threshold,
            check_interval=self.check_interval,
            max_session_permit=self.max_concurrent,
            rate_limiter=self.rate_limiter,
            monitor=self.monitor,
        )

    async def _process_in_batches(
        self,
        crawler: AsyncWebCrawler,
        urls: List[str],
        config: CrawlerRunConfig,
        dispatcher: Union[MemoryAdaptiveDispatcher, SemaphoreDispatcher],
        batch_size: int,
    ) -> List[Dict[str, Any]]:
        """Collect results in batches."""
        all_results = []
        for i in range(0, len(urls), batch_size):
            batch = urls[i : i + batch_size]
            batch_results = await crawler.arun_many(
                urls=batch, config=config, dispatcher=dispatcher
            )
            all_results.extend([self._format_result(r) for r in batch_results])
        return all_results

    def _resolve_config(
        self, config: Optional[Union[CrawlerRunConfig, Dict]]
    ) -> CrawlerRunConfig:
        """Handle configuration input of different types."""
        if config is None:
            return self.default_run_config

        if isinstance(config, dict):
            return CrawlerRunConfig(**{**self.default_run_config.__dict__, **config})

        return config

    def _format_result(self, result) -> Dict[str, Any]:
        """Standardize the result format with dispatch information."""
        formatted = {
            "content": {
                "markdown": {
                    "raw": result.markdown.raw_markdown,
                    "fitted": result.markdown.fit_markdown,
                },
                "html": {"raw": result.html, "cleaned": result.cleaned_html},
                "text": getattr(result, "text", None),
            },
            "metadata": {
                "success": result.success,
                "status_code": result.status_code,
                "url": result.url,
                "timestamp": getattr(result, "timestamp", None),
            },
            "resources": {"media": result.media, "links": result.links},
        }

        if hasattr(result, "dispatch_result"):
            formatted["dispatch_info"] = result.dispatch_result

        return formatted


async def test_scrape_many():
    """Test the scrape_many functionality with and without batching."""
    # Initialize the scraper
    scraper = Crawl4AIScraper(
        max_concurrent=5,  # Limit concurrent requests
        memory_threshold=80.0,  # Memory threshold for adaptive dispatcher
    )

    # List of test URLs
    test_urls = [
        "https://example.com",
        "https://www.wikipedia.org",
        "https://www.python.org",
        "https://www.github.com",
        "https://www.stackoverflow.com",
        "https://news.ycombinator.com",
        "https://www.reddit.com",
        "https://www.nytimes.com",
    ]

    print("=== Testing scrape_many without batching ===")
    try:
        results = await scraper.scrape_many(test_urls)
        print(f"Successfully scraped {len(results)} URLs")
        pprint.pprint(results[0])  # Print first result for inspection
    except Exception as e:
        print(f"Error in non-batched scrape_many: {str(e)}")

    print("\n=== Testing scrape_many with batching (batch_size=3) ===")
    try:
        batched_results = await scraper.scrape_many(test_urls, batch_size=3)
        print(f"Successfully scraped {len(batched_results)} URLs in batches")
        pprint.pprint(batched_results[0])  # Print first result for inspection
    except Exception as e:
        print(f"Error in batched scrape_many: {str(e)}")

    print("\n=== Testing scrape_many with semaphore dispatcher ===")
    try:
        # Create a semaphore dispatcher with different settings
        semaphore_dispatcher = SemaphoreDispatcher(
            max_session_permit=3,  # Even lower concurrency
            rate_limiter=RateLimiter(
                base_delay=(1.0, 2.0), max_delay=30.0, max_retries=2  # Faster retry
            ),
            monitor=CrawlerMonitor(),
        )

        semaphore_results = await scraper.scrape_many(
            test_urls[:4], dispatcher=semaphore_dispatcher  # Fewer URLs for this test
        )
        print(
            f"Successfully scraped {len(semaphore_results)} URLs with semaphore dispatcher"
        )
        pprint.pprint(semaphore_results[0])
    except Exception as e:
        print(f"Error in semaphore dispatcher test: {str(e)}")


async def main():
    """Run all test cases."""
    await test_scrape_many()


if __name__ == "__main__":
    asyncio.run(main())
