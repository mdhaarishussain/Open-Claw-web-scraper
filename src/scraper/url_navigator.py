"""
URL navigator for pagination and product link extraction.
Handles different pagination patterns and link discovery.
"""
import logging
from typing import List, Optional, Set
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class URLNavigator:
    """
    Handles URL navigation, pagination, and product link extraction.
    """

    def __init__(self):
        """Initialize URL navigator"""
        self.visited_urls: Set[str] = set()
        logger.info("URLNavigator initialized")

    def extract_product_links(
        self,
        html_content: str,
        base_url: str,
        selector: Optional[str] = None
    ) -> List[str]:
        """
        Extract product links from a category/listing page.

        Args:
            html_content: HTML content of the page
            base_url: Base URL for resolving relative links
            selector: CSS selector for product links (optional)

        Returns:
            List of product URLs
        """
        soup = BeautifulSoup(html_content, 'lxml')
        links = []

        try:
            # Use provided selector if available
            if selector:
                elements = soup.select(selector)
                for element in elements:
                    href = element.get('href')
                    if href:
                        absolute_url = urljoin(base_url, href)
                        links.append(absolute_url)
            else:
                # Fallback: find all links
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    absolute_url = urljoin(base_url, href)

                    # Basic heuristic: skip navigation, filters, etc.
                    if self._looks_like_product_url(absolute_url):
                        links.append(absolute_url)

            # Remove duplicates while preserving order
            links = list(dict.fromkeys(links))

            # Filter out already visited URLs
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
        selector: Optional[str] = None
    ) -> Optional[str]:
        """
        Find the "Next Page" pagination link.

        Args:
            html_content: HTML content of current page
            current_url: Current page URL
            selector: CSS selector for next page link (optional)

        Returns:
            URL of next page, or None if not found
        """
        soup = BeautifulSoup(html_content, 'lxml')

        try:
            next_link = None

            # Try provided selector first
            if selector:
                element = soup.select_one(selector)
                if element:
                    next_link = element.get('href')

            # Fallback: common patterns for next page
            if not next_link:
                # Look for common next page indicators
                patterns = [
                    {'name': 'a', 'string': 'Next'},
                    {'name': 'a', 'string': 'next'},
                    {'name': 'a', 'class_': 'next'},
                    {'name': 'a', 'class_': 'pagination-next'},
                    {'name': 'a', 'attrs': {'aria-label': 'Next'}},
                    {'name': 'a', 'attrs': {'rel': 'next'}},
                ]

                for pattern in patterns:
                    element = soup.find(**pattern)
                    if element and element.get('href'):
                        next_link = element['href']
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

        Args:
            url: URL to check

        Returns:
            True if URL looks like a product page
        """
        url_lower = url.lower()

        # Exclude common non-product pages
        exclude_patterns = [
            '/search', '/category', '/categories', '/filter',
            '/sort', '/login', '/register', '/account', '/cart',
            '/checkout', '/about', '/contact', '/help', '/faq',
            '/terms', '/privacy', '/sitemap', '#', 'javascript:',
            'mailto:', '.pdf', '.jpg', '.png', '.gif'
        ]

        for pattern in exclude_patterns:
            if pattern in url_lower:
                return False

        # Include common product page patterns
        include_patterns = [
            '/product/', '/item/', '/p/', '/watch/', '/furniture/',
            '/jewelry/', '/listing/', '/detail/'
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
