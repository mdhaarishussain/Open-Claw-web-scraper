"""
Main entry point for the Heartisans Autonomous Data Pipeline.
Run this script to start the autonomous data collection process.
"""
import os
import sys
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.settings import settings


def setup_logging():
    """Configure logging for the pipeline"""
    # Ensure logs directory exists
    settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Create timestamp for log files
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Build handlers list
    console_handler = logging.StreamHandler(sys.stdout)

    all_log_handler = logging.FileHandler(
        settings.LOGS_DIR / f'pipeline_{timestamp}.log',
        encoding='utf-8',
    )

    error_log_handler = logging.FileHandler(
        settings.LOGS_DIR / f'errors_{timestamp}.log',
        encoding='utf-8',
    )
    error_log_handler.setLevel(logging.ERROR)  # Set level AFTER creation

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[console_handler, all_log_handler, error_log_handler],
    )

    # Set specific log levels for noisy modules
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('scrapling').setLevel(logging.WARNING)

    return logging.getLogger(__name__)


def main():
    """Main execution function"""
    logger = setup_logging()

    logger.info("=" * 80)
    logger.info("HEARTISANS AUTONOMOUS DATA PIPELINE")
    logger.info("=" * 80)
    logger.info(f"Target rows: {settings.TARGET_ROW_COUNT:,}")
    logger.info(f"LLM Provider: {settings.LLM_PROVIDER}")
    logger.info(f"Output CSV:   {settings.CSV_PATH}")
    logger.info(f"Database:     {settings.DATABASE_PATH}")
    logger.info(f"Concurrent requests: {settings.CONCURRENT_REQUESTS}")
    logger.info(f"Crawl directory: {settings.CRAWL_DIR}")
    logger.info("=" * 80)

    try:
        # Validate configuration
        settings.validate()
        logger.info("[OK] Configuration validated")

        # Ensure data directories exist
        settings.ensure_directories()
        logger.info("[OK] Directories initialized")

        # Use Spider-based pipeline (Scrapling Spider framework)
        # Clean up stale checkpoint temp files (Windows os.rename bug)
        import glob
        crawl_dir = str(settings.CRAWL_DIR)
        for tmp_file in glob.glob(os.path.join(crawl_dir, '*.tmp')):
            try:
                os.remove(tmp_file)
                logger.info(f"[OK] Cleaned stale temp file: {os.path.basename(tmp_file)}")
            except OSError:
                pass

        from src.orchestrator.spider_pipeline import run_spider_pipeline
        run_spider_pipeline()

        logger.info("=" * 80)
        logger.info("Pipeline execution completed successfully!")
        logger.info("=" * 80)

    except KeyboardInterrupt:
        logger.warning("\nPipeline interrupted by user (Ctrl+C)")
        logger.info("Spider crawl state saved. Re-run to resume from checkpoint.")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Pipeline failed with error: {e}", exc_info=True)
        logger.error("Check logs for details")
        sys.exit(1)


if __name__ == "__main__":
    main()
