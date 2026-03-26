"""
Main autonomous pipeline orchestrator.
Coordinates scraping, extraction, validation, and storage in a self-running loop.
"""
import logging
import time
from typing import List, Optional, Dict

from src.scraper.stealthy_fetcher import StealthyFetcher
from src.scraper.rate_limiter import CombinedRateLimiter
from src.scraper.url_navigator import URLNavigator
from src.extraction.llm_extractor import SmartExtractor
from src.extraction.validator import Validator
from src.storage.database import Database
from src.orchestrator.state_manager import StateManager
from config.settings import settings

logger = logging.getLogger(__name__)


class AutonomousPipeline:
    """
    Main autonomous pipeline that orchestrates the entire data collection process.
    Runs without human intervention from seed URLs to target row count.
    """

    def __init__(self, target_rows: Optional[int] = None):
        """
        Initialize the autonomous pipeline.

        Args:
            target_rows: Target number of rows to collect (uses settings default if None)
        """
        self.target_rows = target_rows or settings.TARGET_ROW_COUNT
        self.checkpoint_interval = settings.CHECKPOINT_INTERVAL

        # Initialize components
        self.fetcher = StealthyFetcher()
        self.rate_limiter = CombinedRateLimiter()
        self.navigator = URLNavigator()
        self.extractor = SmartExtractor()
        self.validator = Validator()
        self.database = Database()
        self.state = StateManager()

        logger.info(
            f"AutonomousPipeline initialized (target: {self.target_rows} rows, "
            f"checkpoint every {self.checkpoint_interval} rows)"
        )

    def run(self):
        """
        Main execution loop. Runs autonomously until target row count is reached.
        """
        logger.info("=" * 60)
        logger.info("STARTING AUTONOMOUS PIPELINE")
        logger.info("=" * 60)

        try:
            # Resume from checkpoint if exists
            if self.state.checkpoint_exists():
                logger.info("Resuming from checkpoint...")
                self.state.load_checkpoint()
                logger.info(f"Current progress: {self.state.row_count}/{self.target_rows} rows")

            # Ensure directories exist
            settings.ensure_directories()

            # Load seed URLs
            seed_config = settings.load_seed_urls()
            sources = seed_config.get('sources', [])

            if not sources:
                logger.error("No seed URLs configured in seed_urls.yaml")
                return

            logger.info(f"Loaded {len(sources)} seed URL sources")

            # Process each source
            for source in sources:
                if self.state.row_count >= self.target_rows:
                    logger.info(f"Target reached: {self.state.row_count} rows")
                    break

                logger.info(f"Processing source: {source['name']}")
                self.process_source(source)

            # Final checkpoint and report
            self.state.save_checkpoint()
            self.generate_final_report()

            logger.info("=" * 60)
            logger.info("PIPELINE COMPLETED SUCCESSFULLY")
            logger.info("=" * 60)

        except KeyboardInterrupt:
            logger.warning("Pipeline interrupted by user")
            self.state.save_checkpoint()
            self.state.print_report()

        except Exception as e:
            logger.error(f"Pipeline failed with error: {e}", exc_info=True)
            self.state.save_checkpoint()
            raise

    def process_source(self, source: Dict):
        """
        Process a single source (e.g., a website category).

        Args:
            source: Source configuration dictionary
        """
        base_url = source['base_url']
        name = source['name']
        product_selector = source.get('product_selector')
        next_page_selector = source.get('next_page_selector')

        current_page_url = base_url
        page_num = 1

        logger.info(f"Starting source: {name} at {base_url}")

        while current_page_url and self.state.row_count < self.target_rows:
            # Check if already processed this page
            if self.state.is_processed(current_page_url):
                logger.info(f"Page already processed, skipping: {current_page_url[:50]}...")
                break

            logger.info(f"Processing page {page_num}: {current_page_url[:80]}...")

            # Check circuit breaker
            if not self.rate_limiter.wait_if_allowed(current_page_url):
                logger.warning(f"Circuit breaker open for {current_page_url}, skipping source {name}")
                break

            # Fetch category page
            try:
                fetch_result = self.fetcher.fetch(current_page_url)

                if not fetch_result['success']:
                    logger.error(f"Failed to fetch page: {fetch_result['error']}")
                    self.rate_limiter.record_result(current_page_url, False)
                    break

                self.rate_limiter.record_result(current_page_url, True)

                # Extract product URLs from page
                product_urls = self.navigator.extract_product_links(
                    fetch_result['raw_html'],
                    current_page_url,
                    product_selector
                )

                logger.info(f"Found {len(product_urls)} product URLs on page {page_num}")

                # Process each product
                for product_url in product_urls:
                    if self.state.row_count >= self.target_rows:
                        logger.info("Target reached, stopping source processing")
                        break

                    if self.state.is_processed(product_url):
                        continue

                    self.process_product(product_url)

                    # Checkpoint periodically
                    if self.state.row_count % self.checkpoint_interval == 0:
                        self.state.save_checkpoint()

                # Mark page as processed
                self.state.mark_processed(current_page_url)

                # Find next page
                current_page_url = self.navigator.find_next_page_link(
                    fetch_result['raw_html'],
                    current_page_url,
                    next_page_selector
                )

                if current_page_url:
                    page_num += 1
                else:
                    logger.info(f"No more pages found for source {name}")

            except Exception as e:
                logger.error(f"Error processing page {current_page_url}: {e}", exc_info=True)
                self.rate_limiter.record_result(current_page_url, False)
                break

        logger.info(f"Completed source: {name} ({self.state.row_count}/{self.target_rows} rows total)")

    def process_product(self, product_url: str):
        """
        Process a single product: scrape, extract, validate, and store.

        Args:
            product_url: URL of the product to process
        """
        logger.info(f"Processing product: {product_url[:80]}...")

        try:
            # Step 1: Scrape
            if not self.rate_limiter.wait_if_allowed(product_url):
                logger.warning(f"Circuit breaker open for {product_url}, skipping")
                self.state.record_failure(product_url, 'circuit_breaker')
                return

            scrape_start = time.time()
            fetch_result = self.fetcher.fetch(product_url)
            scrape_time = time.time() - scrape_start

            if not fetch_result['success']:
                logger.warning(f"Scrape failed: {fetch_result['error']}")
                self.state.record_failure(product_url, 'scrape')
                self.rate_limiter.record_result(product_url, False)
                return

            self.rate_limiter.record_result(product_url, True)

            # Step 2: Extract with LLM
            extraction_start = time.time()
            try:
                product_data = self.extractor.extract(
                    fetch_result['raw_text'],
                    url=product_url
                )
            except Exception as e:
                logger.warning(f"Extraction failed: {e}")
                self.state.record_failure(product_url, 'extraction')
                return
            extraction_time = time.time() - extraction_start

            # Step 3: Validate
            is_valid, error_msg, confidence = self.validator.validate(product_data)

            if not is_valid:
                logger.warning(f"Validation failed: {error_msg}")
                # Determine failure type based on error
                if 'price' in error_msg.lower():
                    self.state.record_failure(product_url, 'no_price')
                else:
                    self.state.record_failure(product_url, 'validation')
                return

            # Step 4: Store
            try:
                self.database.insert(product_data, product_url, confidence)
                self.state.increment_row_count()
                self.state.record_success(product_url, scrape_time, extraction_time)

                logger.info(
                    f"✓ Successfully stored product #{self.state.row_count}: "
                    f"${product_data.current_market_price:,.2f} "
                    f"(confidence: {confidence:.2f})"
                )

            except Exception as e:
                logger.error(f"Storage failed: {e}")
                self.state.record_failure(product_url, 'storage')
                return

        except Exception as e:
            logger.error(f"Unexpected error processing {product_url}: {e}", exc_info=True)
            self.state.record_failure(product_url, 'exception')

    def generate_final_report(self):
        """Generate and display final execution report"""
        logger.info("\n" + "=" * 70)
        logger.info("FINAL PIPELINE EXECUTION REPORT")
        logger.info("=" * 70)

        report = self.state.get_report()

        logger.info(f"Total rows collected:        {report['total_rows']:,}")
        logger.info(f"Target rows:                 {self.target_rows:,}")
        logger.info(f"Completion:                  {(report['total_rows'] / self.target_rows * 100):.1f}%")
        logger.info(f"URLs processed:              {report['urls_processed']:,}")
        logger.info(f"URLs failed:                 {report['urls_failed']:,}")
        logger.info(f"Success rate:                {report['success_rate']:.1%}")
        logger.info(f"Avg scrape time:             {report['avg_scrape_time']:.2f}s")
        logger.info(f"Avg extraction time:         {report['avg_extraction_time']:.2f}s")
        logger.info(f"Total runtime:               {report['total_runtime']}")

        logger.info(f"\nFailures by type:")
        for failure_type, count in report['failures_by_type'].items():
            logger.info(f"  - {failure_type:20s}: {count:,}")

        # Price statistics
        price_stats = self.database.get_price_statistics()
        logger.info(f"\nPrice statistics:")
        logger.info(f"  - Min price:      ${price_stats['min']:,.2f}")
        logger.info(f"  - Max price:      ${price_stats['max']:,.2f}")
        logger.info(f"  - Avg price:      ${price_stats['avg']:,.2f}")
        logger.info(f"  - Median price:   ${price_stats['median']:,.2f}")

        # Export data
        if report['total_rows'] > 0:
            export_path = settings.DATA_DIR / f"heartisans_dataset_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            self.database.export_to_csv(str(export_path))
            logger.info(f"\nDataset exported to: {export_path}")

        logger.info("=" * 70)

        # Print to console as well
        self.state.print_report()
