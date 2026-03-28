---
name: heartisans-scraper
description: Autonomous web scraping pipeline for luxury & antique price data collection using Scrapling + LLM extraction
---

# Heartisans Autonomous Data Pipeline

An intelligent, self-healing web scraping pipeline for luxury & antique price prediction. Uses Scrapling's stealth browser automation to bypass anti-bot protections and LLMs for structured data extraction.

## Prerequisites

- **Python 3.10+** with a virtual environment active
- **Scrapling** with browser dependencies installed:
  ```bash
  pip install "scrapling[fetchers]>=0.2.9"
  scrapling install
  ```
- **LLM API key** (Cerebras recommended, or OpenAI/Anthropic/Ollama)
- A configured `.env` file (see `.env.example`)

## Available Tools

### 1. `scrape_url(url, headless=True)`
Fetch a single URL with stealth bot-bypass.

**When to use**: When you need to inspect a page's raw content before deciding what to extract.

```python
from src.openclaw_tools import scrape_url
result = scrape_url("https://www.chrono24.com/watch/example.htm")
if result['success']:
    print(f"Got {result['text_length']} chars of text")
```

### 2. `scrape_product(url, headless=True)`
Full pipeline for a single product: scrape → LLM extract → validate → store in DB.

**When to use**: When you have a specific product URL and want structured data stored immediately.

```python
from src.openclaw_tools import scrape_product
result = scrape_product("https://www.1stdibs.com/furniture/example/")
if result['success']:
    print(f"Price: ₹{result['data']['current_market_price']:,.2f}")
    print(f"Brand: {result['data']['brand']}")
```

### 3. `extract_product_data(raw_text, url=None, provider=None)`
Extract structured data from already-scraped text content.

**When to use**: When you already have the page text and just need LLM extraction + validation.

```python
from src.openclaw_tools import extract_product_data
result = extract_product_data(page_text, url="https://example.com/item/123")
if result['success']:
    print(f"Extracted {len(result['data'])} fields, confidence={result['confidence']}")
```

### 4. `run_pipeline(target_rows=10, sources=None)`
Run the full Spider-based pipeline. Crawls category pages, follows pagination, extracts product data, stores in SQLite.

**When to use**: When you want to collect a batch of product data autonomously.

```python
from src.openclaw_tools import run_pipeline
result = run_pipeline(target_rows=50)
print(f"Collected {result['rows_collected']} rows")
print(f"Success rate: {result['report']['success_rate']:.1%}")
```

## Data Schema

The pipeline extracts 15 structured features per product. All prices are in **INR (Indian Rupees)**.

| Feature | Type | Required | Description |
|---------|------|----------|-------------|
| `material_used` | str | ✅ | Primary material |
| `valuable_gem` | str | ❌ | Gemstone type |
| `expensive_material` | str | ❌ | Precious metals |
| `origin` | str | ✅ | Country/region |
| `date_of_manufacture` | str | ✅ | Year or era |
| `defects` | str | ❌ | Damage description |
| `scratches` | bool | ✅ | Has scratches |
| `colour` | str | ✅ | Primary color |
| `current_market_price` | float | ✅⚠️ | Price in INR — **critical** |
| `seller_reputation` | float | ❌ | Rating 0-10 |
| `dimensions` | str | ❌ | Physical dimensions |
| `weight` | str | ❌ | Weight with unit |
| `work_type` | enum | ✅ | Handwork/Machine/Unknown |
| `brand` | str | ❌ | Brand name |
| `limited_edition` | bool | ✅ | Limited edition status |

> **Critical**: Items without a valid `current_market_price` are automatically discarded.

## Configuration

Edit `.env` to configure:

```bash
# LLM Provider (cerebras recommended)
LLM_PROVIDER=cerebras
CEREBRAS_API_KEY=your_key_here

# Scraping behavior
MIN_DELAY_SECONDS=2
MAX_DELAY_SECONDS=7
CONCURRENT_REQUESTS=5

# Pipeline
TARGET_ROW_COUNT=10000
```

Edit `config/seed_urls.yaml` to add target websites with CSS selectors.

## Outputs

- **SQLite DB**: `data/heartisans.db`
- **CSV export**: `data/heartisans_dataset_*.csv` (auto-generated)
- **Logs**: `logs/pipeline_*.log` and `logs/errors_*.log`
- **Crawl state**: `data/crawl_data/` (for Spider pause/resume)

## Interpreter Path

If OpenClaw asks for a Python interpreter, use the virtual environment path:
- **Windows (WSL)**: `~/.openclaw/venvs/scrapling/bin/python`
- **macOS**: `~/.openclaw/venvs/scrapling/bin/python`
