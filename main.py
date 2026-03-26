"""
Main entry point for the Heartisans Autonomous Data Pipeline.
Run this script to start the autonomous data collection process.
"""
import sys
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.settings import settings
from src.orchestrator.pipeline import AutonomousPipeline


def setup_logging():
    """Configure logging for the pipeline"""
    # Ensure logs directory exists
    settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Create timestamp for log files
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            # Console handler
            logging.StreamHandler(sys.stdout),
            # File handler - all logs
            logging.FileHandler(
                settings.LOGS_DIR / f'pipeline_{timestamp}.log',
                encoding='utf-8'            ),
            # File handler - errors only
            logging.FileHandler(
                settings.LOGS_DIR / f'errors_{timestamp}.log',
                level=logging.ERROR,
                encoding='utf-8'
            )
        ]
    )

    # Set specific log levels for modules
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)

    return logging.getLogger(__name__)


def main():
    """Main execution function"""
    logger = setup_logging()

    logger.info("=" * 80)
    logger.info("HEARTISANS AUTONOMOUS DATA PIPELINE")
    logger.info("=" * 80)
    logger.info(f"Target rows: {settings.TARGET_ROW_COUNT:,}")
    logger.info(f"LLM Provider: {settings.LLM_PROVIDER}")
    logger.info(f"Database: {settings.DATABASE_PATH}")
    logger.info(f"Checkpoint interval: {settings.CHECKPOINT_INTERVAL} rows")
    logger.info("=" * 80)

    try:
        # Validate configuration
        settings.validate()
        logger.info("✓ Configuration validated")

        # Ensure data directories exist
        settings.ensure_directories()
        logger.info("✓ Directories initialized")

        # Create and run pipeline
        pipeline = AutonomousPipeline()
        pipeline.run()

        logger.info("=" * 80)
        logger.info("Pipeline execution completed successfully!")
        logger.info("=" * 80)

    except KeyboardInterrupt:
        logger.warning("\nPipeline interrupted by user (Ctrl+C)")
        logger.info("Progress has been checkpointed. Re-run to resume.")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Pipeline failed with error: {e}", exc_info=True)
        logger.error("Check logs for details")
        sys.exit(1)


if __name__ == "__main__":
    main()
