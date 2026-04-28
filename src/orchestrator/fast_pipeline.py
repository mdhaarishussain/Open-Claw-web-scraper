import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional, List
from urllib.parse import urlparse

# We keep using Scrapling's AsyncFetcher for stealth
from scrapling import AsyncFetcher
from scrapling.fetchers import AsyncStealthySession

from src.extraction.llm_extractor import SmartExtractor
from src.extraction.validator import Validator
from src.storage.database import Database
from config.settings import settings

logger = logging.getLogger(__name__)

class NativeFastPipeline:
    """
    Ultra-fast async pipeline utilizing Scrapling's AsyncFetcher directly.
    Bypasses Playwright headless Chromium overhead completely for 20x speed.
    """
    def __init__(self, sources: list = None, target_rows: int = None):
        self.sources_config = sources or []
        self.target_rows = target_rows or settings.TARGET_ROW_COUNT
        self.concurrent_requests = settings.CONCURRENT_REQUESTS
        
        # Build source map
        self._source_map: Dict[str, dict] = {}
        for source in self.sources_config:
            if source.get('enabled', True):
                self._source_map[source['base_url']] = source

        self._extractor = SmartExtractor()
        self._validator = Validator()
        self._database = Database()
        
        self.row_count = 0
        self.successes = 0
        self.failures = 0
        self.failures_by_type = {}
        self._start_time = datetime.now()
        
        # Concurrency primitives
        self.product_queue = asyncio.Queue()
        self.category_queue = asyncio.Queue()
        self.target_reached_event = asyncio.Event()
        # Maximize concurrency using the 12 Groq API keys pool
        self.llm_semaphore = asyncio.Semaphore(15)
        
        # In-memory deduplication cache to block duplicates of failed items in the same session
        self.seen_urls = set()

    def _find_source(self, url: str) -> Optional[dict]:
        if url in self._source_map:
            return self._source_map[url]
        for source_url, config in self._source_map.items():
            if url.startswith(source_url) or source_url.startswith(url):
                return config
        try:
            url_domain = urlparse(url).netloc.replace('www.', '')
            for source_url, config in self._source_map.items():
                if urlparse(source_url).netloc.replace('www.', '') == url_domain:
                    return config
        except Exception:
            pass
        return None

    def _record_failure(self, failure_type: str):
        self.failures += 1
        self.failures_by_type[failure_type] = self.failures_by_type.get(failure_type, 0) + 1

    async def _fetch_categories_worker(self, fetcher: AsyncFetcher):
        """Worker that grabs category pages, extracts product links and pagination."""
        while not self.target_reached_event.is_set():
            try:
                # Use timeout to allow checking event flag
                url = await asyncio.wait_for(self.category_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            if self.target_reached_event.is_set():
                self.category_queue.task_done()
                break

            source = self._find_source(url) or {}
            product_selector = source.get('product_selector', 'a')
            next_page_selector = source.get('next_page_selector')

            try:
                logger.info(f"[CATEGORY] Fetching {url[:80]}")
                
                is_stealth = any(domain in url.lower() for domain in ['1stdibs.com', 'therealreal.com', 'rebag.com', 'grailed.com'])
                
                if is_stealth:
                    response = await self.stealth_session.fetch(url)
                else:
                    response = await fetcher.get(url)
                
                # Get product links
                product_links = response.css(product_selector)
                if not product_links:
                    fallback_selectors = ['a[href*="/product"]', 'a[href*="/item"]', 'a[href*="/listing"]', 'a[href*="/id"]', 'a[href*="/p/"]']
                    for fb_sel in fallback_selectors:
                        product_links = response.css(fb_sel)
                        if product_links:
                            break
                
                # Only add necessary URLS
                added = 0
                for link in product_links:
                    if self.target_reached_event.is_set(): break
                    href = link.attrib.get('href', '').strip()
                    if href:
                        product_url = response.urljoin(href)
                        
                        # Standardize liveauctioneers item URLs to prevent duplicate slug variants
                        if 'liveauctioneers.com/item/' in product_url:
                            import re as _re
                            # Match the base item ID and strip the trailing slug string
                            product_url = _re.sub(r'(/item/\d+)[^?/]*', r'\1', product_url)
                            
                        # Pre-append category to URL so DB deduplication catches it before downloading
                        if source and source.get('category'):
                            cat_val = source.get('category')
                            url_sep = '&' if '?' in product_url else '?'
                            product_url = f"{product_url}{url_sep}src_cat={cat_val}"
                        
                        # In-memory dedup to prevent burning tokens on the exact same item multiple times
                        if product_url in self.seen_urls:
                            continue
                        self.seen_urls.add(product_url)
                        
                        # Safety net: ensure we stay on the same domain (prevents extracting cookie banner links etc)
                        try:
                            source_domain = urlparse(source.get('base_url', url)).netloc.replace('www.', '')
                            product_domain = urlparse(product_url).netloc.replace('www.', '')
                            if product_domain and source_domain and product_domain != source_domain:
                                continue
                        except Exception:
                            pass
                            
                        await self.product_queue.put((product_url, source))
                        added += 1
                        
                logger.debug(f"[CATEGORY] {url[:60]} -> Found {len(product_links)} products, queued {added}")

                # Pagination
                if next_page_selector and not self.target_reached_event.is_set():
                    next_links = response.css(next_page_selector)
                    if next_links:
                        next_href = next_links[0].attrib.get('href')
                        if next_href:
                            logger.info(f"[PAGINATION] Queuing next page: {next_href[:60]}")
                            await self.category_queue.put(response.urljoin(next_href))

            except Exception as e:
                logger.error(f"[CATEGORY FAIL] {url[:80]}: {str(e)}")
            finally:
                self.category_queue.task_done()

    async def _process_products_worker(self, fetcher: AsyncFetcher):
        """Worker that grabs product pages, extracts data, and saves."""
        while not self.target_reached_event.is_set():
            try:
                queue_item = await asyncio.wait_for(self.product_queue.get(), timeout=1.0)
                if isinstance(queue_item, tuple):
                    url, source = queue_item
                else:
                    url = queue_item
                    source = self._find_source(url) or {}
                    
                if self.target_reached_event.is_set():
                    self.product_queue.task_done()
                    break

            except asyncio.TimeoutError:
                continue

            try:
                # Basic product page test to avoid downloading rubbish
                product_path_hints = ['/p/', '/products/', '/item/', '/listing/', '/id-', '/lot/', '/product/']
                if not any(hint in url for hint in product_path_hints):
                    continue

                # Aggressive negative filtering for static/footer pages
                junk_paths = ['/pages/', '/policy', '/terms', '/contact', '/about', '/privacy', 'login', 'register', 'cart', 'checkout', 'buyer-protection', 'partnership', 'faq', '/similar/']
                if any(junk in url.lower() for junk in junk_paths):
                    continue
                # DB Deduplication
                if self._database.url_exists(url):
                    logger.debug(f"[SKIP] Already in DB: {url[:60]}")
                    continue

                # Stealth Routing for highly blocked websites
                is_stealth = any(domain in url.lower() for domain in ['1stdibs.com', 'therealreal.com', 'rebag.com', 'grailed.com'])
                
                try:
                    if is_stealth:
                        response = await asyncio.wait_for(self.stealth_session.fetch(url), timeout=30.0)
                    else:
                        response = await asyncio.wait_for(fetcher.get(url), timeout=30.0)
                except asyncio.TimeoutError:
                    logger.warning(f"[SKIP] Network Timeout (30s) on {url[:60]}")
                    continue
                except Exception as e:
                    logger.warning(f"[SKIP] Network error on {url[:60]}: {str(e)}")
                    continue
                
                # Bot challenge check & 403 Check
                if response.status == 403:
                    logger.warning(f"[SKIP] 403 Forbidden (Blocked) - {url[:60]}")
                    continue
                
                # Extract clean text from page to save token cost
                extracted_parts = []
                import re, json as _json
                # response.text is often empty for scrapling's AsyncFetcher on dynamic sites.
                # response.body (raw bytes) always contains the full HTML including <script> tags.
                raw_html = ''
                if hasattr(response, 'body') and response.body:
                    try:
                        raw_html = response.body.decode('utf-8', errors='ignore') if isinstance(response.body, bytes) else str(response.body)
                    except Exception:
                        pass
                if not raw_html and hasattr(response, 'text') and response.text:
                    raw_html = response.text
                if not raw_html:
                    try:
                        raw_html = response.get_all_text(separator=' ', strip=True)
                    except Exception:
                        raw_html = ''

                # --- PRE-SCRUB: Extract price from JSON-LD BEFORE stripping scripts ---
                # This is critical for Novica and other sites where the main product price
                # lives only inside a <script type="application/ld+json"> tag.
                ld_price_found = None
                ld_currency = 'USD'  # default
                
                # Skip JSON-LD price checking for auction sites because their JSON schema usually
                # just contains a useless $10 "Starting Bid" which overrides our Estimate/Hammer Price.
                is_auction = url and any(x in url.lower() for x in ['liveauctioneers.com', 'bonhams.com'])
                
                if not is_auction:
                    for ld_block in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', raw_html, re.IGNORECASE | re.DOTALL):
                        try:
                            ld_data = _json.loads(ld_block.group(1))
                            offers = ld_data.get('offers', {})
                            if isinstance(offers, list):
                                offers = offers[0] if offers else {}
                            if 'price' in offers:
                                ld_price_found = str(offers['price'])
                                ld_currency = offers.get('priceCurrency', 'USD').upper()
                                extracted_parts.append(f"PRICE: {ld_price_found} {ld_currency}")
                                break
                        except Exception:
                            pass

                clean_html = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', raw_html, flags=re.IGNORECASE | re.DOTALL)
                raw_text = re.sub(r'\s+', ' ', re.sub(r'<[^>]*>', ' ', clean_html)).strip()
                if 'Cloudflare' in raw_text or 'Just a moment...' in raw_text or 'attention required' in raw_text.lower():
                    logger.warning(f"[SKIP] Hit Cloudflare CAPTCHA - {url[:60]}")
                    continue

                for sel in ['h1', '.product-title', '.product-name', '[data-testid="product-title"]', 'title']:
                    nodes = response.css(sel)
                    if nodes:
                        extracted_parts.append(f"TITLE: {nodes[0].text.strip()}")
                        break

                # Only run CSS price extraction if JSON-LD didn't already find the price
                if not ld_price_found:
                    for sel in ['.price', '.product-price', '[itemprop="price"]', '[data-price]', '#price', 'span.amount', 'p.price', '.current-price', '.money', '.price-item', '.price__regular', '.selling-price', '.regular-price']:
                        nodes = response.css(sel)
                        if nodes:
                            # Only use text content — never use data-rate-us attribute as it
                            # belongs to carousel/related items on Novica, not the main product.
                            pt = ' '.join(n.text.strip() for n in nodes[:3] if n.text and n.text.strip())
                            if pt:
                                extracted_parts.append(f"PRICE: {pt}")
                                break

                for sel in ['.product-description', '[itemprop="description"]', '.description', '#description']:
                    nodes = response.css(sel)
                    if nodes:
                        desc = nodes[0].text.strip()[:800]
                        if len(desc) > 30:
                            extracted_parts.append(f"DESCRIPTION: {desc}")
                            break

                for sel in ['.specifications', '#specs', '.product-details', '#details', '.attributes', 'table.woocommerce-product-attributes', 'dl.product-info', '.features', '#features', '[data-testid="product-details"]']:
                    nodes = response.css(sel)
                    if nodes:
                        specs = ' '.join(n.text.strip() for n in nodes[:3])[:800]
                        if len(specs) > 20:
                            extracted_parts.append(f"SPECS/DETAILS: {specs}")
                            break

                for sel in ['.brand', '[itemprop="brand"]', '.vendor', '.product-vendor']:
                    nodes = response.css(sel)
                    if nodes:
                        brand = nodes[0].text.strip()[:100]
                        if len(brand) > 2:
                            extracted_parts.append(f"BRAND: {brand}")
                            break

                if len(extracted_parts) < 2:
                    # Token Condensation: Extract from the top where price/title usually live
                    # Limit to 5000 chars to save token limit while capturing deep DOM nodes.
                    extracted_parts = [f"PAGE TEXT:\n{raw_text[:5000]}"]

                content_for_llm = f"SOURCE URL: {url}\n\n" + "\n".join(extracted_parts)
                
                # Token Saver: If this is an auction, only call LLM if there's evidence of an Estimate or Winning Bid.
                # This prevents burning 1,500 tokens on junk items that will just fail validation anyway.
                if is_auction:
                    lower_content = content_for_llm.lower()
                    if not any(k in lower_content for k in ['estimate', 'winning bid', 'hammer price', 'sold for', 'price realized', 'bidding closed']):
                        logger.debug(f"[SKIP] No auction price markers found, saving tokens: {url[:60]}")
                        self._record_failure('no_price')
                        continue

                # LLM Extraction
                # Leverage all 12 API keys concurrently; the key-rotator will handle any 429 Rate Limits automatically.
                async with self.llm_semaphore:
                    # Run synchronous LLM extraction in thread pool
                    product_data = await asyncio.to_thread(
                        self._extractor.extract, content_for_llm, url
                    )
                # Validation
                is_valid, error_msg, confidence = self._validator.validate(product_data)
                if not is_valid:
                    self._record_failure('no_price' if 'price' in (error_msg or '').lower() else 'validation')
                    logger.warning(f"[FAIL] Validation: {url[:60]}... ({error_msg})")
                    continue

                # --- DETERMINISTIC PRICE OVERRIDE ---
                # If JSON-LD gave us a verified price, override whatever the LLM returned.
                # This prevents hallucinations (e.g. itokri returning 10000 instead of 3390).
                if ld_price_found:
                    import re as _re
                    try:
                        raw_ld_val = float(_re.sub(r'[^\d.]', '', ld_price_found))
                        # Apply domain currency failsafe on top of ld_currency
                        url_lower_check = url.lower() if url else ''
                        if any(x in url_lower_check for x in ['novica.com', 'therealreal.com', '1stdibs.com', 'rebag.com', 'grailed.com', 'saffronart.com']):
                            final_price = round(raw_ld_val * 83.0, 2)
                        elif any(x in url_lower_check for x in ['catawiki.com', 'pamono.com']):
                            final_price = round(raw_ld_val * 90.0, 2)
                        elif any(x in url_lower_check for x in ['bonhams.com']):
                            final_price = round(raw_ld_val * 107.0, 2)
                        elif ld_currency == 'USD':
                            final_price = round(raw_ld_val * 83.0, 2)
                        elif ld_currency == 'EUR':
                            final_price = round(raw_ld_val * 90.0, 2)
                        elif ld_currency == 'GBP':
                            final_price = round(raw_ld_val * 107.0, 2)
                        else:  # INR or unknown — keep as-is
                            final_price = raw_ld_val
                        product_data.current_market_price = final_price
                    except Exception as _e:
                        logger.warning(f"LD price override failed: {_e}")
                # ------------------------------------

                # --- DETERMINISTIC LIMITED EDITION OVERRIDE ---
                # High-value items (near/over 1 Crore INR) or URLs explicitly mentioning scarcity
                if product_data.current_market_price and product_data.current_market_price >= 9000000:
                    product_data.limited_edition = True
                elif url and any(word in url.lower() for word in ['limited-edition', '/rare-', '-rare-', 'one-of-a-kind', '1-of-1']):
                    product_data.limited_edition = True
                # ----------------------------------------------
                
                # Storage 
                row_id = self._database.insert(product_data, url, confidence)
                if not row_id:
                    # Duplicate caught by SQLite integrity check after parallel fetching
                    continue

                self.row_count += 1
                self.successes += 1
                
                price_out = f"INR {product_data.current_market_price:,.2f}" if product_data.current_market_price else "N/A"
                logger.info(f"[OK] Product #{self.row_count}/{self.target_rows}: {price_out} | {product_data.brand or 'N/A'}")

                if self.row_count >= self.target_rows:
                    self.target_reached_event.set()
                    logger.info(">>> TARGET REACHED! Signal sent to stop queue. <<<")

            except Exception as e:
                logger.error(f"[FAIL] Network/Extr fail for {url[:60]}: {str(e)}")
                self._record_failure('extraction')
            finally:
                self.product_queue.task_done()

    async def run(self):
        """Execute the pipeline concurrently."""
        # Initialize fetcher
        fetcher = AsyncFetcher()
        self.stealth_session = AsyncStealthySession(headless=True)
        await self.stealth_session.start()
        
        logger.info(f"Initialized ultra-fast native pipeline (Target: {self.target_rows})")
        
        # Load all start URLs
        for src in self.sources_config:
            if src.get('enabled', True):
                await self.category_queue.put(src['base_url'])

        # Create workers
        category_tasks = [asyncio.create_task(self._fetch_categories_worker(fetcher)) for _ in range(2)]
        product_tasks = [asyncio.create_task(self._process_products_worker(fetcher)) for _ in range(self.concurrent_requests)]

        # Wait until target is reached or queues drain
        async def wait_for_queues():
            await self.category_queue.join()
            await self.product_queue.join()
            
        pending = [
            asyncio.create_task(self.target_reached_event.wait()),
            asyncio.create_task(wait_for_queues())
        ]
        
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
        
        if not self.target_reached_event.is_set():
            logger.warning("[PIPELINE HALT] Drained all available URLs across all sources. Target not reached!")
            self.target_reached_event.set() # Stop any remaining workers checking the queue occasionally
            
        # Cleanup
        for t in category_tasks + product_tasks:
            t.cancel()
        
        await self.stealth_session.close() # Gracefully close playwright browsers
        
        # Print summary
        self.print_report()
        logger.info(f"Dataset exported to: {self._database.csv_path}")

    def print_report(self):
        runtime = datetime.now() - self._start_time
        logger.info("=" * 60)
        logger.info("PIPELINE COMPLETED")
        logger.info(f"Total Rows:     {self.row_count}")
        logger.info(f"Failures:       {self.failures}")
        logger.info(f"Runtime:        {runtime}")
        logger.info("=" * 60)


def run_spider_pipeline():
    """Wrapper that matches previous syntax for main.py integration."""
    logger.info("=" * 60)
    logger.info("STARTING NATIVE ASYNC PIPELINE")
    logger.info("=" * 60)
    
    seed_config = settings.load_seed_urls()
    sources = seed_config.get('sources', [])
    
    # Auto-Discover Dynamic Sites (Bonhams)
    # Disabled by request to focus exclusively on LiveAuctioneers bulk extraction.
    # from src.discovery.bonhams_discovery import discover_bonhams_auctions
    # import asyncio
    # 
    # try:
    #     logger.info("Running pre-flight auto-discovery checks...")
    #     bonhams_seeds = asyncio.run(discover_bonhams_auctions())
    #     if bonhams_seeds:
    #         sources.extend(bonhams_seeds)
    #         logger.info(f"Injecting {len(bonhams_seeds)} dynamic seeds into pipeline.")
    # except Exception as e:
    #     logger.error(f"Auto-discovery failed: {str(e)}")

    pipeline = NativeFastPipeline(
        sources=sources,
    )
    
    asyncio.run(pipeline.run())
