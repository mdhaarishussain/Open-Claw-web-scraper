"""
OpenClaw tool: Scrape a URL using Scrapling's stealth fetchers.

This tool can be registered with OpenClaw so the agent can autonomously
fetch web pages while bypassing anti-bot protections.
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def scrape_url(
    url: str,
    headless: bool = True,
    use_session: bool = False,
) -> Dict[str, Any]:
    """
    Fetch a single URL using Scrapling's StealthyFetcher.
    Bypasses Cloudflare, Turnstile, and other bot protections.

    Args:
        url: The URL to scrape
        headless: Run browser in headless mode (default True)
        use_session: Keep browser session alive for faster subsequent calls

    Returns:
        Dictionary with keys:
          - success (bool)
          - url (str)
          - raw_html (str)
          - raw_text (str)
          - error (str or None)
    """
    from src.scraper.stealthy_fetcher import StealthyFetcher

    fetcher = StealthyFetcher(headless=headless, use_session=use_session)
    result = fetcher.fetch(url)

    # Don't include the Scrapling page object in the returned dict (not serializable)
    return {
        'success': result['success'],
        'url': result['url'],
        'raw_html': result['raw_html'],
        'raw_text': result['raw_text'],
        'error': result['error'],
        'text_length': len(result['raw_text']),
        'html_length': len(result['raw_html']),
    }


def scrape_product(
    url: str,
    headless: bool = True,
) -> Dict[str, Any]:
    """
    Scrape a product page and return structured product data.
    Combines scraping + LLM extraction + validation in one call.

    Args:
        url: Product page URL
        headless: Run browser in headless mode

    Returns:
        Dictionary with keys:
          - success (bool)
          - data (dict or None): Extracted product data as dictionary
          - confidence (float): Extraction confidence score 0-1
          - error (str or None)
          - stored (bool): Whether the data was saved to the database
    """
    from src.scraper.stealthy_fetcher import StealthyFetcher
    from src.extraction.llm_extractor import SmartExtractor
    from src.extraction.validator import Validator
    from src.storage.database import Database

    try:
        # Step 1: Scrape
        fetcher = StealthyFetcher(headless=headless, use_session=False)
        fetch_result = fetcher.fetch(url)

        if not fetch_result['success']:
            return {
                'success': False,
                'data': None,
                'confidence': 0.0,
                'error': f"Scrape failed: {fetch_result['error']}",
                'stored': False,
            }

        # Step 2: Extract
        extractor = SmartExtractor()
        product_data = extractor.extract(fetch_result['raw_text'], url=url)

        # Step 3: Validate
        validator = Validator()
        is_valid, error_msg, confidence = validator.validate(product_data)

        if not is_valid:
            return {
                'success': False,
                'data': product_data.model_dump(),
                'confidence': confidence,
                'error': f"Validation failed: {error_msg}",
                'stored': False,
            }

        # Step 4: Store
        db = Database()
        db.insert(product_data, url, confidence)
        db.close()

        return {
            'success': True,
            'data': product_data.model_dump(),
            'confidence': confidence,
            'error': None,
            'stored': True,
        }

    except Exception as e:
        logger.error(f"scrape_product failed for {url}: {e}")
        return {
            'success': False,
            'data': None,
            'confidence': 0.0,
            'error': str(e),
            'stored': False,
        }
