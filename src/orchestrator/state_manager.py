"""
State manager for tracking pipeline progress and enabling resumption.
Saves checkpoints periodically to allow recovery from interruptions.
"""
import json
import pickle
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Set, List, Optional

from config.settings import settings

logger = logging.getLogger(__name__)


class StateManager:
    """
    Manages pipeline state including progress tracking and checkpointing.
    """

    def __init__(self, checkpoint_dir: Optional[Path] = None):
        """
        Initialize state manager.

        Args:
            checkpoint_dir: Directory for checkpoint files (uses settings default if None)
        """
        self.checkpoint_dir = checkpoint_dir or settings.CHECKPOINT_DIR
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # State tracking
        self.row_count = 0
        self.urls_processed: Set[str] = set()
        self.urls_failed: Dict[str, str] = {}  # URL -> failure reason
        self.start_time = datetime.now()

        # Metrics
        self.metrics = {
            'scrape_times': [],
            'extraction_times': [],
            'failures_by_type': {},
            'successes': 0,
            'total_attempts': 0
        }

        self.checkpoint_path = self.checkpoint_dir / "pipeline_state.pkl"
        logger.info(f"StateManager initialized (checkpoint: {self.checkpoint_path})")

    def increment_row_count(self):
        """Increment the count of successfully stored rows"""
        self.row_count += 1
        self.metrics['successes'] += 1
        logger.debug(f"Row count incremented to {self.row_count}")

    def is_processed(self, url: str) -> bool:
        """Check if a URL has already been processed"""
        return url in self.urls_processed

    def mark_processed(self, url: str):
        """Mark a URL as processed"""
        self.urls_processed.add(url)

    def record_success(self, url: str, scrape_time: Optional[float] = None, extraction_time: Optional[float] = None):
        """
        Record a successful processing operation.

        Args:
            url: URL that was processed
            scrape_time: Time taken to scrape (seconds)
            extraction_time: Time taken to extract (seconds)
        """
        self.mark_processed(url)
        self.metrics['total_attempts'] += 1

        if scrape_time:
            self.metrics['scrape_times'].append(scrape_time)
        if extraction_time:
            self.metrics['extraction_times'].append(extraction_time)

        logger.debug(f"Recorded success for {url[:50]}...")

    def record_failure(self, url: str, failure_type: str):
        """
        Record a failed processing operation.

        Args:
            url: URL that failed
            failure_type: Type of failure ('scrape', 'extraction', 'no_price', 'storage')
        """
        self.urls_failed[url] = failure_type
        self.mark_processed(url)  # Don't retry in this run
        self.metrics['total_attempts'] += 1

        # Track failures by type
        self.metrics['failures_by_type'][failure_type] = \
            self.metrics['failures_by_type'].get(failure_type, 0) + 1

        logger.warning(f"Recorded failure for {url[:50]}... (type: {failure_type})")

    def save_checkpoint(self):
        """Save current state to disk for resumption"""
        try:
            state_data = {
                'row_count': self.row_count,
                'urls_processed': list(self.urls_processed),
                'urls_failed': self.urls_failed,
                'start_time': self.start_time,
                'metrics': self.metrics,
                'checkpoint_time': datetime.now()
            }

            with open(self.checkpoint_path, 'wb') as f:
                pickle.dump(state_data, f)

            logger.info(
                f"Checkpoint saved: {self.row_count} rows, "
                f"{len(self.urls_processed)} URLs processed"
            )

        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

    def load_checkpoint(self) -> bool:
        """
        Load state from previous run.

        Returns:
            True if checkpoint was loaded, False if no checkpoint exists
        """
        if not self.checkpoint_path.exists():
            logger.info("No checkpoint found, starting fresh")
            return False

        try:
            with open(self.checkpoint_path, 'rb') as f:
                state_data = pickle.load(f)

            self.row_count = state_data['row_count']
            self.urls_processed = set(state_data['urls_processed'])
            self.urls_failed = state_data['urls_failed']
            self.start_time = state_data['start_time']
            self.metrics = state_data['metrics']

            checkpoint_time = state_data.get('checkpoint_time', 'unknown')

            logger.info(
                f"Checkpoint loaded: {self.row_count} rows, "
                f"{len(self.urls_processed)} URLs processed "
                f"(saved at {checkpoint_time})"
            )

            return True

        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return False

    def checkpoint_exists(self) -> bool:
        """Check if a checkpoint file exists"""
        return self.checkpoint_path.exists()

    def get_report(self) -> Dict:
        """
        Generate a progress report.

        Returns:
            Dictionary with progress statistics
        """
        total_processed = len(self.urls_processed)
        total_failed = len(self.urls_failed)
        total_success = self.metrics['successes']

        success_rate = total_success / total_processed if total_processed > 0 else 0

        avg_scrape_time = (
            sum(self.metrics['scrape_times']) / len(self.metrics['scrape_times'])
            if self.metrics['scrape_times'] else 0
        )

        avg_extraction_time = (
            sum(self.metrics['extraction_times']) / len(self.metrics['extraction_times'])
            if self.metrics['extraction_times'] else 0
        )

        runtime = datetime.now() - self.start_time

        return {
            'total_rows': self.row_count,
            'urls_processed': total_processed,
            'urls_failed': total_failed,
            'success_rate': success_rate,
            'failures_by_type': self.metrics['failures_by_type'],
            'avg_scrape_time': round(avg_scrape_time, 2),
            'avg_extraction_time': round(avg_extraction_time, 2),
            'total_runtime': str(runtime),
            'runtime_seconds': runtime.total_seconds()
        }

    def print_report(self):
        """Print a formatted progress report"""
        report = self.get_report()

        print("=" * 60)
        print("PIPELINE PROGRESS REPORT")
        print("=" * 60)
        print(f"Total rows collected:     {report['total_rows']}")
        print(f"URLs processed:           {report['urls_processed']}")
        print(f"URLs failed:              {report['urls_failed']}")
        print(f"Success rate:             {report['success_rate']:.1%}")
        print(f"Avg scrape time:          {report['avg_scrape_time']:.2f}s")
        print(f"Avg extraction time:      {report['avg_extraction_time']:.2f}s")
        print(f"Total runtime:            {report['total_runtime']}")
        print(f"\nFailures by type:")
        for failure_type, count in report['failures_by_type'].items():
            print(f"  - {failure_type:20s}: {count}")
        print("=" * 60)

    def clear_checkpoint(self):
        """
        Remove checkpoint file. USE WITH CAUTION!
        """
        if self.checkpoint_path.exists():
            self.checkpoint_path.unlink()
            logger.info("Checkpoint file deleted")
