"""
URL navigator for pagination and product link extraction.
Uses Scrapling's built-in parser instead of BeautifulSoup for consistency and performance.
"""
import logging
from typing import List, Optional, Set
from urllib.parse import urljoin, urlparse

from scrapling.parser import Selector

logger = logging.getLogger(__name__)


class URLNavigator:
    """
    Handles URL navigation, pagination, and product link extraction.
    Uses Scrapling's Selector for HTML parsing — no BeautifulSoup dependency.
    """

    def __init__(self):
        """Initialize URL navigator"""
        self.visited_urls: Set[str] = set()
        logger.info("URLNavigator initialized")

    def extract_product_links(
        self,
        html_content: str,
        base_url: str,
        selector: Optional[str] = None,
        *,
        page=None,
    ) -> List[str]:
        """
        Extract product links from a category/listing page.

        Args:
            html_content: HTML content of the page (used if page is None)
            base_url: Base URL for resolving relative links
            selector: CSS selector for product links (optional)
            page: Optional Scrapling Adaptor/Response object (preferred over raw HTML)

        Returns:
            List of product URLs
        """
        # Use Scrapling Adaptor if provided, otherwise parse raw HTML
        if page is not None:
            doc = page
        else:
            doc = Selector(html_content)

        links: list[str] = []

        try:
            if selector:
                elements = doc.css(selector)
                for element in elements:
                    href = element.attrib.get('href')
                    if href:
                        absolute_url = urljoin(base_url, href)
                        links.append(absolute_url)
            else:
                # Fallback: find all <a> tags
                for link in doc.css('a[href]'):
                    href = link.attrib.get('href', '')
                    if href:
                        absolute_url = urljoin(base_url, href)
                        if self._looks_like_product_url(absolute_url):
                            links.append(absolute_url)

            # Remove duplicates while preserving order
            links = list(dict.fromkeys(links))

            # Filter out already-visited URLs
            new_links = [url for url in links if url not in self.visited_urls]

            logger.info(
                f"Extracted {len(new_links)} new product links from {base_url[:50]}... "
                f"({len(links)} total, {len(links) - len(new_links)} already visited)"
            )

            return new_links

        except Exception as e:
            logger.error(f"Error extracting product links: {e}")
            return []

    def find_next_page_link(
        self,
        html_content: str,
        current_url: str,
        selector: Optional[str] = None,
        *,
        page=None,
    ) -> Optional[str]:
        """
        Find the "Next Page" pagination link.

        Args:
            html_content: HTML content of current page (used if page is None)
            current_url: Current page URL
            selector: CSS selector for next page link (optional)
            page: Optional Scrapling Adaptor/Response object

        Returns:
            URL of next page, or None if not found
        """
        if page is not None:
            doc = page
        else:
            doc = Selector(html_content)

        try:
            next_link = None

            # Try provided selector first
            if selector:
                elements = doc.css(selector)
                if elements:
                    next_link = elements[0].attrib.get('href')

            # Fallback: common pagination patterns
            if not next_link:
                css_patterns = [
                    'a.next',
                    'a.pagination-next',
                    'a[aria-label="Next"]',
                    'a[rel="next"]',
                    'li.next > a',
                    '.pagination a.next',
                ]
                for pattern in css_patterns:
                    elements = doc.css(pattern)
                    if elements:
                        next_link = elements[0].attrib.get('href')
                        if next_link:
                            break

            # Text-based fallback
            if not next_link:
                for a_tag in doc.css('a'):
                    text = (a_tag.text or '').strip().lower()
                    if text in ('next', 'next ›', 'next »', '>', '»', '→'):
                        next_link = a_tag.attrib.get('href')
                        if next_link:
                            break

            if next_link:
                absolute_url = urljoin(current_url, next_link)
                logger.info(f"Found next page: {absolute_url[:100]}...")
                return absolute_url

            logger.debug("No next page link found")
            return None

        except Exception as e:
            logger.error(f"Error finding next page link: {e}")
            return None

    def _looks_like_product_url(self, url: str) -> bool:
        """
        Heuristic to determine if a URL likely points to a product page.
        """
        url_lower = url.lower()

        exclude_patterns = [
            '/search', '/category', '/categories', '/filter',
            '/sort', '/login', '/register', '/account', '/cart',
            '/checkout', '/about', '/contact', '/help', '/faq',
            '/terms', '/privacy', '/sitemap', '#', 'javascript:',
            'mailto:', '.pdf', '.jpg', '.png', '.gif',
        ]

        for pattern in exclude_patterns:
            if pattern in url_lower:
                return False

        include_patterns = [
            '/product/', '/item/', '/p/', '/watch/', '/furniture/',
            '/jewelry/', '/listing/', '/detail/',
        ]

        for pattern in include_patterns:
            if pattern in url_lower:
                return True

        # If no clear pattern, include it (safer to over-include)
        return True

    def mark_visited(self, url: str):
        """Mark a URL as visited"""
        self.visited_urls.add(url)

    def is_visited(self, url: str) -> bool:
        """Check if URL has been visited"""
        return url in self.visited_urls

    def get_visited_count(self) -> int:
        """Get count of visited URLs"""
        return len(self.visited_urls)
