"""
Stealthy web scraper using Scrapling's fetchers.
Handles anti-bot protection bypass (Cloudflare, Turnstile, CAPTCHAs).

Uses the correct Scrapling public API:
  - StealthyFetcher.fetch()   — one-off class-method for stealth browser requests
  - StealthySession            — persistent session for reusing browser across requests
  - AsyncStealthySession       — async variant for concurrent fetching
"""
import asyncio
import logging
import time
from typing import Dict, Optional
from functools import wraps

from scrapling.fetchers import StealthyFetcher as ScraplingStealthyFetcher
from scrapling.fetchers import StealthySession, AsyncStealthySession

from config.settings import settings

logger = logging.getLogger(__name__)


def retry_on_failure(max_attempts: int = None, delay: float = 2, backoff: float = 2):
    """
    Decorator to retry a function on failure with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts (uses settings default if None)
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each attempt

    Returns:
        Decorated function with retry logic
    """
    if max_attempts is None:
        max_attempts = settings.MAX_RETRIES

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 1
            current_delay = delay

            while attempt <= max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise

                    logger.warning(
                        f"{func.__name__} attempt {attempt}/{max_attempts} failed: {e}. "
                        f"Retrying in {current_delay:.1f}s..."
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff
                    attempt += 1

        return wrapper
    return decorator


class StealthyFetcher:
    """
    Wrapper around Scrapling's StealthyFetcher / StealthySession.
    Supports both one-off requests and persistent session-based fetching.
    """

    def __init__(
        self,
        timeout: Optional[int] = None,
        headless: bool = True,
        use_session: bool = True,
    ):
        """
        Initialize the stealthy fetcher.

        Args:
            timeout: Request timeout in seconds (uses settings default if None)
            headless: Whether to run browser in headless mode
            use_session: If True, keep browser session alive across requests (faster)
        """
        self.timeout = timeout or settings.REQUEST_TIMEOUT
        self.headless = headless
        self.use_session = use_session
        self._session: Optional[StealthySession] = None

        logger.info(
            f"StealthyFetcher initialized (timeout={self.timeout}s, "
            f"headless={self.headless}, session={self.use_session})"
        )

    def _get_session(self) -> StealthySession:
        """Get or create a persistent StealthySession."""
        if self._session is None:
            self._session = StealthySession(headless=self.headless)
        return self._session

    @retry_on_failure()
    def fetch(self, url: str) -> Dict[str, any]:
        """
        Fetch a webpage with stealth techniques to bypass bot detection.

        Args:
            url: The URL to fetch

        Returns:
            Dictionary containing:
                - success (bool): Whether the fetch was successful
                - url (str): The final URL (after redirects)
                - raw_html (str): The raw HTML content
                - raw_text (str): Extracted text content
                - page (object): The Scrapling response/Adaptor for direct CSS/XPath use
                - error (str): Error message if failed
        """
        logger.debug(f"Fetching: {url}")
        start_time = time.time()

        try:
            if self.use_session:
                session = self._get_session()
                page = session.fetch(url, network_idle=True)
            else:
                # One-off request: opens browser, fetches, closes browser
                page = ScraplingStealthyFetcher.fetch(
                    url,
                    headless=self.headless,
                    network_idle=True,
                )

            raw_html = page.html if hasattr(page, 'html') else str(page)
            raw_text = page.text if hasattr(page, 'text') else ''

            elapsed_time = time.time() - start_time
            logger.info(
                f"Successfully fetched {url} in {elapsed_time:.2f}s "
                f"({len(raw_html)} bytes)"
            )

            return {
                'success': True,
                'url': url,
                'raw_html': raw_html,
                'raw_text': raw_text,
                'page': page,  # Scrapling Adaptor — use page.css(), page.xpath()
                'error': None,
            }

        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return {
                'success': False,
                'url': url,
                'raw_html': '',
                'raw_text': '',
                'page': None,
                'error': str(e),
            }

    def close(self):
        """Close the browser session if open."""
        if self._session is not None:
            try:
                self._session.__exit__(None, None, None)
            except Exception:
                pass
            self._session = None
            logger.debug("StealthySession closed")


class AsyncStealthyFetcher:
    """
    Async wrapper around Scrapling's AsyncStealthySession.
    Enables concurrent fetching with a shared browser pool.
    """

    def __init__(
        self,
        headless: bool = True,
        max_pages: int = 5,
    ):
        self.headless = headless
        self.max_pages = max_pages
        self._session: Optional[AsyncStealthySession] = None

    async def _get_session(self) -> AsyncStealthySession:
        if self._session is None:
            self._session = AsyncStealthySession(
                headless=self.headless,
                max_pages=self.max_pages,
            )
        return self._session

    async def fetch(self, url: str) -> Dict[str, any]:
        """Async fetch a single URL."""
        logger.debug(f"[async] Fetching: {url}")
        start_time = time.time()

        try:
            session = await self._get_session()
            page = await session.fetch(url, network_idle=True)

            raw_html = page.html if hasattr(page, 'html') else str(page)
            raw_text = page.text if hasattr(page, 'text') else ''

            elapsed = time.time() - start_time
            logger.info(f"[async] Fetched {url} in {elapsed:.2f}s ({len(raw_html)} bytes)")

            return {
                'success': True,
                'url': url,
                'raw_html': raw_html,
                'raw_text': raw_text,
                'page': page,
                'error': None,
            }
        except Exception as e:
            logger.error(f"[async] Error fetching {url}: {e}")
            return {
                'success': False,
                'url': url,
                'raw_html': '',
                'raw_text': '',
                'page': None,
                'error': str(e),
            }

    async def fetch_many(self, urls: list[str]) -> list[Dict[str, any]]:
        """Fetch multiple URLs concurrently."""
        tasks = [self.fetch(url) for url in urls]
        return await asyncio.gather(*tasks)

    async def close(self):
        if self._session is not None:
            try:
                await self._session.__aexit__(None, None, None)
            except Exception:
                pass
            self._session = None


# ---------------------------------------------------------------------------
# Custom exceptions (avoid shadowing Python's built-in TimeoutError)
# ---------------------------------------------------------------------------

class ScrapeError(Exception):
    """Custom exception for scraping errors"""
    pass


class BotDetectionError(ScrapeError):
    """Raised when bot detection is triggered"""
    pass


class ScrapeTimeoutError(ScrapeError):
    """Raised when a request times out (renamed to avoid shadowing builtins)"""
    pass
