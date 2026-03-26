"""
Stealthy web scraper using Scrapling's StealthyFetcher.
Handles anti-bot protection bypass (Cloudflare, Turnstile, CAPTCHAs).
"""
import logging
import time
from typing import Dict, Optional
from functools import wraps

from scrapling.core.fetchers import StealthyFetcher as ScraplingStealthyFetcher
from scrapling.default_settings import PlaywrightDefaultSettings

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
    Wrapper around Scrapling's StealthyFetcher for bypassing anti-bot protections.
    Handles page loading, content extraction, and error recovery.
    """

    def __init__(
        self,
        timeout: Optional[int] = None,
        user_agent: Optional[str] = None,
        headless: bool = True
    ):
        """
        Initialize the stealthy fetcher.

        Args:
            timeout: Request timeout in seconds (uses settings default if None)
            user_agent: Custom user agent string (uses settings default if None)
            headless: Whether to run browser in headless mode
        """
        self.timeout = timeout or settings.REQUEST_TIMEOUT
        self.user_agent = user_agent or settings.USER_AGENT
        self.headless = headless

        # Configure Scrapling settings
        self.settings = PlaywrightDefaultSettings()
        self.settings.timeout = self.timeout * 1000  # Convert to milliseconds
        self.settings.user_agent = self.user_agent
        self.settings.headless = self.headless

        logger.info(
            f"StealthyFetcher initialized (timeout={self.timeout}s, "
            f"headless={self.headless})"
        )

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
                - status_code (int): HTTP status code
                - error (str): Error message if failed

        Raises:
            Exception: If all retry attempts fail
        """
        logger.debug(f"Fetching: {url}")
        start_time = time.time()

        try:
            # Initialize Scrapling's StealthyFetcher
            fetcher = ScraplingStealthyFetcher()

            # Fetch the page with stealth configurations
            response = fetcher.get(
                url,
                headless=self.headless,
                timeout=self.timeout * 1000,  # Milliseconds
                wait_selector=None,  # Don't wait for specific selectors
                block_resources=True  # Block images, fonts, etc. for faster loading
            )

            # Extract content
            raw_html = response.html if hasattr(response, 'html') else str(response)
            raw_text = response.text if hasattr(response, 'text') else ''

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
                'status_code': 200,  # Scrapling doesn't expose status code easily
                'error': None
            }

        except TimeoutError as e:
            logger.error(f"Timeout fetching {url}: {e}")
            return {
                'success': False,
                'url': url,
                'raw_html': '',
                'raw_text': '',
                'status_code': 0,
                'error': f'Timeout: {str(e)}'
            }

        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return {
                'success': False,
                'url': url,
                'raw_html': '',
                'raw_text': '',
                'status_code': 0,
                'error': str(e)
            }

    def fetch_multiple(self, urls: list[str]) -> list[Dict[str, any]]:
        """
        Fetch multiple URLs sequentially.

        Args:
            urls: List of URLs to fetch

        Returns:
            List of fetch results (same format as fetch())
        """
        results = []
        for url in urls:
            result = self.fetch(url)
            results.append(result)
            # Small delay between fetches to avoid detection
            time.sleep(0.5)
        return results


class ScrapeError(Exception):
    """Custom exception for scraping errors"""
    pass


class BotDetectionError(ScrapeError):
    """Raised when bot detection is triggered"""
    pass


class TimeoutError(ScrapeError):
    """Raised when a request times out"""
    pass
