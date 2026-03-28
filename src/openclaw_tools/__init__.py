"""
OpenClaw tool wrappers for the Heartisans Data Pipeline.

These tools can be registered with OpenClaw so the agent can orchestrate
the scraping pipeline autonomously. Each tool is a self-contained function
that accepts parameters and returns structured results.
"""
from src.openclaw_tools.scrape_tool import scrape_url, scrape_product
from src.openclaw_tools.extract_tool import extract_product_data, run_pipeline

__all__ = [
    'scrape_url',
    'scrape_product',
    'extract_product_data',
    'run_pipeline',
]
