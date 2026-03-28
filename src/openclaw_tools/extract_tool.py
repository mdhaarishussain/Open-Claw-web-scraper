"""
OpenClaw tool: Extract structured product data from raw text using LLMs.

This tool can be registered with OpenClaw so the agent can autonomously
extract structured data from scraped content without manually invoking
the full pipeline.
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def extract_product_data(
    raw_text: str,
    url: Optional[str] = None,
    provider: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Extract structured product data from raw text content using an LLM.

    Args:
        raw_text: Raw text content from a product page
        url: Optional source URL for context
        provider: LLM provider override ('cerebras', 'openai', 'anthropic', 'ollama')

    Returns:
        Dictionary with keys:
          - success (bool)
          - data (dict or None): Extracted ProductData as dictionary
          - confidence (float): Confidence score 0-1
          - error (str or None)
    """
    from src.extraction.llm_extractor import LLMExtractor
    from src.extraction.validator import Validator

    try:
        extractor = LLMExtractor(provider=provider)
        product_data = extractor.extract(raw_text, url=url)

        validator = Validator()
        is_valid, error_msg, confidence = validator.validate(product_data)

        return {
            'success': is_valid,
            'data': product_data.model_dump(),
            'confidence': confidence,
            'error': error_msg,
        }

    except Exception as e:
        logger.error(f"extract_product_data failed: {e}")
        return {
            'success': False,
            'data': None,
            'confidence': 0.0,
            'error': str(e),
        }


def run_pipeline(
    target_rows: int = 10,
    sources: Optional[list] = None,
) -> Dict[str, Any]:
    """
    Run the full Spider-based scraping pipeline.

    Args:
        target_rows: Number of rows to collect (default 10 for testing)
        sources: Optional list of source configs. If None, loads from seed_urls.yaml.

    Returns:
        Dictionary with keys:
          - success (bool)
          - rows_collected (int)
          - report (dict): Execution report with metrics
          - error (str or None)
    """
    from config.settings import settings
    from src.orchestrator.spider_pipeline import HeartisansSpider

    try:
        # Load sources if not provided
        if sources is None:
            seed_config = settings.load_seed_urls()
            sources = [
                s for s in seed_config.get('sources', [])
                if s.get('enabled', True)
            ]

        if not sources:
            return {
                'success': False,
                'rows_collected': 0,
                'report': {},
                'error': 'No sources configured',
            }

        spider = HeartisansSpider(
            sources=sources,
            target_rows=target_rows,
        )

        result = spider.start()
        report = spider.get_report()

        spider.database.close()

        return {
            'success': True,
            'rows_collected': spider.row_count,
            'items_scraped': len(result.items),
            'report': report,
            'error': None,
        }

    except Exception as e:
        logger.error(f"run_pipeline failed: {e}")
        return {
            'success': False,
            'rows_collected': 0,
            'report': {},
            'error': str(e),
        }
