"""
Spider-based autonomous pipeline using Scrapling's built-in Spider framework.
Replaces the custom AutonomousPipeline with Scrapling's concurrent, pause/resume Spider.

Features:
  - Concurrent crawling with configurable limits
  - Per-domain throttling / download delays
  - Pause/resume via crawldir checkpoints (press Ctrl+C, restart to resume)
  - StealthySession for anti-bot bypass
  - Async LLM extraction via asyncio.to_thread()
  - Integrated validation and DB storage
"""
import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Optional

from scrapling.spiders import Spider, Request, Response
try:
    from scrapling.fetchers import AsyncDynamicSession
except ImportError:
    from scrapling.fetchers import AsyncStealthySession as AsyncDynamicSession

from src.extraction.llm_extractor import SmartExtractor
from src.extraction.validator import Validator
from src.storage.database import Database
from config.settings import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Windows checkpoint fix: Scrapling uses pathlib.rename() which fails on Windows
# when the target file already exists (WinError 183). Patch it to use replace().
# ---------------------------------------------------------------------------
if sys.platform == 'win32':
    try:
        import scrapling.spiders.checkpoint as _ckpt_mod
        import inspect, textwrap

        # Find and patch the save method to use os.replace instead of rename
        original_save = _ckpt_mod.CheckpointManager.save

        async def _patched_save(self, data):
            import pickle
            import anyio
            temp_path = self._checkpoint_path.with_suffix('.tmp')
            # Write temp file
            async with await anyio.open_file(str(temp_path), 'wb') as f:
                await f.write(pickle.dumps(data))
            # Use os.replace() which works on Windows even if target exists
            os.replace(str(temp_path), str(self._checkpoint_path))

        _ckpt_mod.CheckpointManager.save = _patched_save
        logger.debug("[WIN] Checkpoint save patched to use os.replace()")
    except Exception as _e:
        logger.warning(f"Could not patch checkpoint manager: {_e}")



class HeartisansSpider(Spider):
    """
    Production spider for scraping luxury & antique product data.

    Uses Scrapling's Spider framework for:
      - Concurrent requests with configurable limits
      - Automatic pause/resume (crawldir)
      - Stealth browser sessions for anti-bot bypass
      - Download delays for polite crawling

    Integrates with the existing extraction pipeline:
      - SmartExtractor (LLM-based data extraction with fallback)
      - Validator (data quality + price checks in INR)
      - Database (SQLite storage)
    """

    name = "heartisans"

    def __init__(
        self,
        sources: list = None,
        target_rows: int = None,
        crawl_dir: str = None,
        **kwargs,
    ):
        """
        Initialize the Heartisans spider.

        Args:
            sources: List of source configs from seed_urls.yaml
            target_rows: Stop after collecting this many valid rows
            crawl_dir: Directory for crawl checkpoints (enables pause/resume)
        """
        self.sources_config = sources or []
        self.target_rows = target_rows or settings.TARGET_ROW_COUNT
        self.concurrent_requests = settings.CONCURRENT_REQUESTS
        self.download_delay = 0.5  # 0.5s between requests (was 2s) — much faster

        # Build source lookup map — ALL sources go in the map for URL matching.
        # start_urls is the limited subset we actually request.
        self._source_map: Dict[str, dict] = {}
        all_seeds = []
        for source in self.sources_config:
            if source.get('enabled', True):
                url = source['base_url']
                all_seeds.append(source)
                self._source_map[url] = source

        # Sort by priority field (lower number = higher priority).
        # Sites with no priority get 50 (mid-range).
        all_seeds.sort(key=lambda s: s.get('priority', 50))

        # SMART SEED LIMITING: only start as many seeds as needed.
        # Formula: need enough seeds that together they'll yield target_rows * 2
        # product links (2x buffer for validation failures).
        # Assume each seed page yields ~15 usable product links on average.
        seeds_needed = max(3, (self.target_rows * 2 // 15) + 1)
        selected = all_seeds[:seeds_needed]
        self.start_urls = [s['base_url'] for s in selected]
        logger.info(
            f"[SEED] Using {len(self.start_urls)} of {len(all_seeds)} sources "
            f"(target={self.target_rows} rows): "
            f"{', '.join(s['name'] for s in selected)}"
        )

        # Processing components
        self._extractor: Optional[SmartExtractor] = None
        self._validator: Optional[Validator] = None
        self._database: Optional[Database] = None

        # Metrics
        self.row_count = 0
        self.successes = 0
        self.failures = 0
        self.failures_by_type: Dict[str, int] = {}
        self._start_time = datetime.now()
        # How many product page requests we've already dispatched.
        # Used to avoid queuing far more pages than target_rows.
        # We queue up to target_rows * 2 (buffer for validation failures).
        self._queued_count = 0

        # Circuit breaker: stop calling LLM after N consecutive failures
        self._consecutive_llm_failures = 0
        self._llm_failure_threshold = settings.CIRCUIT_BREAKER_THRESHOLD
        self._llm_halted = False

        # Crawl directory for pause/resume
        crawl_dir = crawl_dir or str(settings.CRAWL_DIR)

        super().__init__(crawldir=crawl_dir, **kwargs)
        logger.info(
            f"HeartisansSpider initialized: "
            f"{len(self.start_urls)} sources, "
            f"target={self.target_rows} rows, "
            f"concurrency={self.concurrent_requests}"
        )

    # ------------------------------------------------------------------
    # Lazy initialization of heavy components
    # ------------------------------------------------------------------

    @property
    def extractor(self) -> SmartExtractor:
        if self._extractor is None:
            self._extractor = SmartExtractor()
        return self._extractor

    @property
    def validator(self) -> Validator:
        if self._validator is None:
            self._validator = Validator()
        return self._validator

    @property
    def database(self) -> Database:
        if self._database is None:
            self._database = Database()
        return self._database

    # ------------------------------------------------------------------
    # Session configuration
    # ------------------------------------------------------------------

    def configure_sessions(self, manager):
        """
        Use AsyncDynamicSession — the only async-compatible session for the Spider.
        headless=True avoids spinning up a visible browser window.
        network_idle=False means we don't wait for all trackers/ads to load —
        we just need the main DOM content.
        """
        manager.add(
            "fast",
            AsyncDynamicSession(headless=True),
            lazy=True,
        )

    # ------------------------------------------------------------------
    # Spider callbacks
    # ------------------------------------------------------------------

    async def parse(self, response: Response):
        """
        Parse category / listing pages.
        Extracts product links and follows pagination.
        """
        url = str(response.url)
        source = self._find_source(url)

        if not source:
            logger.warning(f"No source config for {url}, using defaults")
            source = {}

        product_selector = source.get('product_selector', 'a')
        next_page_selector = source.get('next_page_selector')

        # Debug: log what we're searching for
        logger.debug(
            f"[parse] URL={url[:80]} | selector='{product_selector}' | "
            f"source={source.get('name', 'unknown')}"
        )

        # Extract product links
        product_links = response.css(product_selector)

        # If primary selector finds nothing, try broad fallback
        if not product_links:
            logger.warning(
                f"Selector '{product_selector}' matched 0 elements. "
                f"Trying fallback selectors..."
            )
            # Try common product link patterns
            fallback_selectors = [
                'a[href*="/product"]',
                'a[href*="/item"]',
                'a[href*="/listing"]',
                'a[href*="/id"]',
                'a[href*="/p/"]',
                'a[href*="/detail"]',
            ]
            for fb_sel in fallback_selectors:
                product_links = response.css(fb_sel)
                if product_links:
                    logger.info(
                        f"Fallback selector '{fb_sel}' found {len(product_links)} links"
                    )
                    break

        logger.info(
            f"[page] {url[:80]}... → {len(product_links)} product links"
        )

        # ---------------------------------------------------------------
        # SMART QUOTA: only queue as many product pages as we still need.
        # We queue up to 100 links per category to ensure we find enough valid items
        # with prices. Scrapling internally limits active concurrency, so this doesn't
        # overwhelm bandwidth or RAM.
        queue_limit = 100
        
        # Take at most queue_limit links from this page
        links_to_queue = []
        for link in product_links:
            href = link.attrib.get('href', '').strip()
            if href and len(links_to_queue) < queue_limit:
                links_to_queue.append(response.urljoin(href))

        logger.info(f"[QUOTA] Queuing {len(links_to_queue)} of {len(product_links)} links (queue_limit allowed: {queue_limit})")

        for product_url in links_to_queue:
            if self.row_count >= self.target_rows:
                break
            self._queued_count += 1
            yield Request(
                product_url,
                callback=self.parse_product,
                sid="fast",
            )

        # Follow pagination
        if next_page_selector and self.row_count < self.target_rows:
            next_links = response.css(next_page_selector)
            if next_links:
                next_href = next_links[0].attrib.get('href')
                if next_href:
                    logger.info(f"[pagination] Following next page")
                    yield Request(
                        response.urljoin(next_href),
                        callback=self.parse,
                        sid="fast",
                    )

    async def parse_product(self, response: Response):
        """
        Parse individual product pages.
        Extract structured data with LLM, validate, and store in DB.
        """
        if self.row_count >= self.target_rows:
            return

        # Circuit breaker: skip LLM if it's broken
        if self._llm_halted:
            return

        # Hard stop: if we already have enough rows, skip remaining queued pages
        if self.row_count >= self.target_rows:
            return

        url = str(response.url)

        # Detect redirect to homepage / non-product page
        # If the URL doesn't contain a product path pattern, skip it
        product_path_hints = ['/p/', '/products/', '/item/', '/listing/', '/id-', '/lot/', '/product/']
        if not any(hint in url for hint in product_path_hints):
            logger.warning(f"[SKIP] URL doesn't look like a product page: {url[:60]}")
            return

        # Extract clean, focused text from the page using CSS selectors.
        # We pull only the structured product data fields, NOT the full HTML.
        # This reduces token usage from ~10,000 chars of soup to ~500 chars of signal.
        extracted_parts = []

        # Title / product name
        for sel in ['h1', 'h1.product-title', '.product-name', '[data-testid="product-title"]', 'title']:
            nodes = response.css(sel)
            if nodes:
                extracted_parts.append(f"TITLE: {nodes[0].text.strip()}")
                break

        # Price — most important field
        for sel in ['.price', '.product-price', '[itemprop="price"]', '[data-price]',
                    '.Price', '#price', 'span.amount', '.woocommerce-Price-amount',
                    'p.price', '.offer-price', '.current-price', '[class*="price"]',
                    '.item-price', '.productPrice', '[data-test="price"]']:
            nodes = response.css(sel)
            if nodes:
                price_text = ' '.join(n.text.strip() for n in nodes[:3] if n.text.strip())
                if price_text:
                    extracted_parts.append(f"PRICE: {price_text}")
                    break

        # Description / details
        for sel in ['.product-description', '[itemprop="description"]', '.description',
                    '#description', '.product-details', '.product-info', 'article',
                    '.summary', '.product-summary', '[class*="description"]']:
            nodes = response.css(sel)
            if nodes:
                desc = nodes[0].text.strip()[:800]  # cap at 800 chars
                if len(desc) > 30:
                    extracted_parts.append(f"DESCRIPTION: {desc}")
                    break

        # Material / specs (common in artisan sites)
        for sel in ['[itemprop="material"]', '.material', '.product-material',
                    'td', 'li', '.spec', '.attribute']:
            nodes = response.css(sel)
            if nodes:
                spec_text = ' | '.join(n.text.strip() for n in nodes[:8] if n.text.strip())
                if spec_text:
                    extracted_parts.append(f"SPECS: {spec_text[:400]}")
                    break

        # Seller / artist info
        for sel in ['.artist-name', '.seller-name', '.artist', '[itemprop="author"]',
                    '.artisan', '.creator', '.by-artist']:
            nodes = response.css(sel)
            if nodes:
                extracted_parts.append(f"SELLER: {nodes[0].text.strip()}")
                break

        # Origin / country metadata
        for sel in ['[itemprop="countryOfOrigin"]', '.origin', '.country', '.made-in']:
            nodes = response.css(sel)
            if nodes:
                extracted_parts.append(f"ORIGIN: {nodes[0].text.strip()}")
                break

        # If no structured data was found, fall back to visible text (capped)
        if len(extracted_parts) < 2:
            raw_text = response.get_all_text(separator=' ', strip=True)
            extracted_parts = [f"PAGE TEXT:\n{raw_text[:3000]}"]

        content_for_llm = f"SOURCE URL: {url}\n\n" + "\n".join(extracted_parts)

        try:
            # Step 1: Extract with LLM (run sync extractor in thread to avoid blocking)
            product_data = await asyncio.to_thread(
                self.extractor.extract,
                content_for_llm,
                url,
            )

            # Reset circuit breaker on success
            self._consecutive_llm_failures = 0

            # Step 2: Validate
            is_valid, error_msg, confidence = self.validator.validate(product_data)

            if not is_valid:
                failure_type = 'no_price' if 'price' in (error_msg or '').lower() else 'validation'
                self._record_failure(url, failure_type)
                logger.warning(f"[FAIL] Validation failed for {url[:60]}...: {error_msg}")
                return

            # Step 3: Store in database
            self.database.insert(product_data, url, confidence)
            self.row_count += 1
            self.successes += 1

            price_out = f"INR {product_data.current_market_price:,.2f}" if product_data.current_market_price else "N/A"
            logger.info(
                f"[OK] Product #{self.row_count}/{self.target_rows}: "
                f"{price_out} | "
                f"Brand: {product_data.brand or 'N/A'} | "
                f"Confidence: {confidence:.2f}"
            )

            # Yield item for Spider result collection
            yield {
                'url': url,
                'price_inr': product_data.current_market_price,
                'brand': product_data.brand,
                'material': product_data.material_used,
                'origin': product_data.origin,
                'confidence': confidence,
            }

        except Exception as e:
            logger.error(f"[FAIL] Failed to process {url[:60]}...: {e}")
            self._record_failure(url, 'extraction')

            # Circuit breaker: track consecutive LLM failures
            self._consecutive_llm_failures += 1
            if self._consecutive_llm_failures >= self._llm_failure_threshold:
                self._llm_halted = True
                logger.critical(
                    f"[CIRCUIT BREAKER] LLM failed {self._consecutive_llm_failures} times "
                    f"consecutively. Halting extraction. Fix the LLM config and restart."
                )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_source(self, url: str) -> Optional[dict]:
        """
        Find the source config that matches a URL.
        Uses URL prefix matching, then domain matching against the source map.
        """
        from urllib.parse import urlparse

        # Exact match
        if url in self._source_map:
            return self._source_map[url]

        # Prefix match (handles path variations)
        for source_url, config in self._source_map.items():
            if url.startswith(source_url) or source_url.startswith(url):
                return config

        # Domain match — only return if there's exactly one source for that domain
        # (avoids mismatching when multiple sources share a domain like chrono24)
        try:
            url_domain = urlparse(url).netloc.replace('www.', '')
            domain_matches = []
            for source_url, config in self._source_map.items():
                src_domain = urlparse(source_url).netloc.replace('www.', '')
                if src_domain == url_domain:
                    domain_matches.append(config)
            if len(domain_matches) == 1:
                return domain_matches[0]
            elif domain_matches:
                # Multiple sources for same domain — return first match
                # (better than wrong domain entirely)
                return domain_matches[0]
        except Exception:
            pass

        return None

    def _record_failure(self, url: str, failure_type: str):
        self.failures += 1
        self.failures_by_type[failure_type] = self.failures_by_type.get(failure_type, 0) + 1

    def get_report(self) -> dict:
        """Generate a final execution report."""
        runtime = datetime.now() - self._start_time
        total = self.successes + self.failures
        success_rate = self.successes / total if total > 0 else 0

        return {
            'total_rows': self.row_count,
            'target_rows': self.target_rows,
            'successes': self.successes,
            'failures': self.failures,
            'success_rate': success_rate,
            'failures_by_type': self.failures_by_type,
            'runtime': str(runtime),
            'runtime_seconds': runtime.total_seconds(),
        }

    def print_report(self):
        """Print a formatted execution report."""
        report = self.get_report()
        price_stats = self.database.get_price_statistics()

        print()
        print("=" * 70)
        print("HEARTISANS PIPELINE - FINAL REPORT")
        print("=" * 70)
        print(f"  Target rows:       {report['target_rows']:,}")
        print(f"  Rows collected:    {report['total_rows']:,}")
        print(f"  Completion:        {(report['total_rows'] / report['target_rows'] * 100):.1f}%")
        print(f"  Success rate:      {report['success_rate']:.1%}")
        print(f"  Total runtime:     {report['runtime']}")
        print()
        print("  Failures by type:")
        for ftype, count in report['failures_by_type'].items():
            print(f"    - {ftype:20s}: {count:,}")
        print()
        print("  Price statistics (INR):")
        print(f"    - Min:    INR {price_stats['min']:,.2f}")
        print(f"    - Max:    INR {price_stats['max']:,.2f}")
        print(f"    - Avg:    INR {price_stats['avg']:,.2f}")
        print(f"    - Median: INR {price_stats['median']:,.2f}")
        print("=" * 70)


def run_spider_pipeline():
    """
    Entry point: load config, create spider, run, export results.
    Called from main.py.
    """
    logger.info("=" * 60)
    logger.info("STARTING SPIDER-BASED PIPELINE")
    logger.info("=" * 60)

    # Load seed URLs
    seed_config = settings.load_seed_urls()
    sources = seed_config.get('sources', [])

    if not sources:
        logger.error("No seed URLs configured in seed_urls.yaml")
        return

    enabled_sources = [s for s in sources if s.get('enabled', True)]
    logger.info(f"Loaded {len(enabled_sources)} enabled seed URL sources")

    # Create and run spider
    spider = HeartisansSpider(
        sources=enabled_sources,
        target_rows=settings.TARGET_ROW_COUNT,
        crawl_dir=str(settings.CRAWL_DIR),
    )

    result = spider.start()

    # Export results
    logger.info(f"Spider finished. Items collected: {len(result.items)}")

    if spider.row_count > 0:
        # Export to CSV
        export_path = (
            settings.DATA_DIR
            / f"heartisans_dataset_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        spider.database.export_to_csv(str(export_path))
        logger.info(f"Dataset exported to: {export_path}")

        # Export Spider items to JSON
        items_path = (
            settings.DATA_DIR
            / f"heartisans_items_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        result.items.to_json(str(items_path))
        logger.info(f"Spider items exported to: {items_path}")

    # Print report
    spider.print_report()

    # Close database
    spider.database.close()
