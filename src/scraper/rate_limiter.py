"""
Rate limiter to ensure human-like delays between requests and prevent IP bans.
Implements per-domain rate tracking and circuit breaker pattern.
"""
import time
import random
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from urllib.parse import urlparse

from config.settings import settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter with randomized delays and per-domain tracking.
    Helps avoid bot detection by simulating human-like behavior.
    """

    def __init__(
        self,
        min_delay: Optional[float] = None,
        max_delay: Optional[float] = None
    ):
        """
        Initialize the rate limiter.

        Args:
            min_delay: Minimum delay between requests in seconds
            max_delay: Maximum delay between requests in seconds
        """
        self.min_delay = min_delay or settings.MIN_DELAY
        self.max_delay = max_delay or settings.MAX_DELAY

        # Track last request time per domain
        self.last_request_time: Dict[str, float] = {}

        logger.info(
            f"RateLimiter initialized (delay: {self.min_delay}-{self.max_delay}s)"
        )

    def wait(self, url: Optional[str] = None):
        """
        Wait for an appropriate duration before the next request.
        Applies a randomized delay to simulate human behavior.

        Args:
            url: Optional URL to track per-domain rate limiting
        """
        domain = self._extract_domain(url) if url else None

        # Check if we need to wait based on last request to this domain
        if domain and domain in self.last_request_time:
            elapsed = time.time() - self.last_request_time[domain]
            if elapsed < self.min_delay:
                additional_wait = self.min_delay - elapsed
                logger.debug(f"Domain rate limit: waiting {additional_wait:.2f}s for {domain}")
                time.sleep(additional_wait)

        # Apply randomized delay
        delay = random.uniform(self.min_delay, self.max_delay)
        logger.debug(f"Rate limit delay: {delay:.2f}s")
        time.sleep(delay)

        # Update last request time
        if domain:
            self.last_request_time[domain] = time.time()

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            parsed = urlparse(url)
            return parsed.netloc
        except Exception:
            return url


class CircuitBreaker:
    """
    Circuit breaker to temporarily block domains after repeated failures.
    Prevents wasting time on blocked or problematic domains.
    """

    def __init__(
        self,
        failure_threshold: Optional[int] = None,
        timeout_seconds: Optional[int] = None
    ):
        """
        Initialize the circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout_seconds: Seconds to wait before attempting again
        """
        self.failure_threshold = failure_threshold or settings.CIRCUIT_BREAKER_THRESHOLD
        self.timeout_seconds = timeout_seconds or settings.CIRCUIT_BREAKER_TIMEOUT

        # Track failures per domain
        self.failure_count: Dict[str, int] = {}

        # Track when circuit was opened (blocked until)
        self.blocked_until: Dict[str, datetime] = {}

        logger.info(
            f"CircuitBreaker initialized (threshold={self.failure_threshold}, "
            f"timeout={self.timeout_seconds}s)"
        )

    def can_proceed(self, url: str) -> bool:
        """
        Check if a request to this domain can proceed.

        Args:
            url: URL to check

        Returns:
            True if request can proceed, False if circuit is open (blocked)
        """
        domain = self._extract_domain(url)

        # Check if domain is currently blocked
        if domain in self.blocked_until:
            if datetime.now() < self.blocked_until[domain]:
                remaining = (self.blocked_until[domain] - datetime.now()).total_seconds()
                logger.warning(
                    f"Circuit breaker OPEN for {domain}. "
                    f"Blocked for {remaining:.0f} more seconds"
                )
                return False
            else:
                # Timeout expired, reset circuit
                logger.info(f"Circuit breaker RESET for {domain}")
                del self.blocked_until[domain]
                self.failure_count[domain] = 0

        return True

    def record_failure(self, url: str):
        """
        Record a failure for a domain. Opens circuit if threshold reached.

        Args:
            url: URL that failed
        """
        domain = self._extract_domain(url)
        self.failure_count[domain] = self.failure_count.get(domain, 0) + 1

        logger.warning(
            f"Failure recorded for {domain}: "
            f"{self.failure_count[domain]}/{self.failure_threshold}"
        )

        # Open circuit if threshold reached
        if self.failure_count[domain] >= self.failure_threshold:
            self.blocked_until[domain] = datetime.now() + timedelta(seconds=self.timeout_seconds)
            logger.error(
                f"Circuit breaker OPENED for {domain}. "
                f"Too many failures ({self.failure_count[domain]}). "
                f"Blocked for {self.timeout_seconds}s"
            )

    def record_success(self, url: str):
        """
        Record a success for a domain. Resets failure count.

        Args:
            url: URL that succeeded
        """
        domain = self._extract_domain(url)
        if domain in self.failure_count:
            logger.debug(f"Success recorded for {domain}, resetting failure count")
            self.failure_count[domain] = 0

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            parsed = urlparse(url)
            return parsed.netloc
        except Exception:
            return url

    def get_status(self, url: str) -> Dict[str, any]:
        """
        Get circuit breaker status for a domain.

        Args:
            url: URL to check

        Returns:
            Dictionary with status information
        """
        domain = self._extract_domain(url)
        is_blocked = domain in self.blocked_until and datetime.now() < self.blocked_until[domain]

        result = {
            'domain': domain,
            'is_blocked': is_blocked,
            'failure_count': self.failure_count.get(domain, 0),
            'blocked_until': self.blocked_until.get(domain)
        }

        if is_blocked:
            result['remaining_seconds'] = (
                self.blocked_until[domain] - datetime.now()
            ).total_seconds()

        return result


class CombinedRateLimiter:
    """
    Combines rate limiting and circuit breaker functionality.
    Provides a unified interface for request management.
    """

    def __init__(self):
        """Initialize combined rate limiter with circuit breaker"""
        self.rate_limiter = RateLimiter()
        self.circuit_breaker = CircuitBreaker()

    def wait_if_allowed(self, url: str) -> bool:
        """
        Check circuit breaker and wait if allowed to proceed.

        Args:
            url: URL to request

        Returns:
            True if request can proceed, False if blocked by circuit breaker
        """
        if not self.circuit_breaker.can_proceed(url):
            return False

        self.rate_limiter.wait(url)
        return True

    def record_result(self, url: str, success: bool):
        """
        Record the result of a request.

        Args:
            url: URL that was requested
            success: Whether the request succeeded
        """
        if success:
            self.circuit_breaker.record_success(url)
        else:
            self.circuit_breaker.record_failure(url)
