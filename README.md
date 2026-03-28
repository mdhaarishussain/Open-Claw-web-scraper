# 🏺 Heartisans Autonomous Data Pipeline

<div align="center">

**An intelligent, self-healing web scraping pipeline for luxury & antique price prediction**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Powered by Cerebras](https://img.shields.io/badge/Powered%20by-Cerebras-orange.svg)](https://cerebras.ai)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

[Features](#-features) •
[Quick Start](#-quick-start) •
[Architecture](#-architecture) •
[Documentation](#-documentation) •
[Troubleshooting](#-troubleshooting)

</div>

---

## 🎯 Overview

Heartisans Autonomous Data Pipeline is a high-speed, enterprise-grade web scraping system designed to collect and structure luxury and antique product data for ML-powered price prediction. Built with **zero human intervention** in mind, it autonomously crawls through pages, extracts targeted product data using high-speed headless browsers, interprets the results using advanced LLM integration, and drops it neatly into CSV and SQLite files for downstream Model Training.

### Why This Pipeline?

- ✅ **Blazing Fast Concurrency**: Powered by Python's `asyncio` and `Scrapling`. It rips through queue quotas seamlessly without blocking RAM. 
- ✅ **LLM-Powered Extraction**: Transforms raw DOM text into fully structured JSON schemas using state-of-the-art inference loops (e.g. Cerebras Llama 3).
- ✅ **Graceful Degradation**: Safely drops bad/out-of-stock items, prevents database-breaking strict Pydantic failures by enforcing `Optional` flexibilities, and converts unparseable values gracefully.
- ✅ **Production Ready**: Utilizes checkpoint systems for network interruptions, comprehensive logging interfaces, and modular pipeline design.

---

## ✨ Features

### 🤖 LLM-Powered Extraction
- **Cerebras Inference**: Ultra-fast Llama 3 inference out of the box.
- **Pre-Processed Contexts**: Stops overwhelming LLMs with raw 2MB HTML DOM loads. We pre-extract `.price`, `h1`, and `description` nodes via CSS targeting to dramatically reduce token load and hallucination risk.
- **Structured Output**: Extracts 15 product features mapping perfectly to the Database SQLite layer.

### 🕵️ Stealth Scraping
- **Scrapling Integration**: Async-managed Playwright operations (`AsyncDynamicSession`) allow true multi-page scraping without context-manager crashes (`__aexit__`) typical of older frameworks.
- **Smart Quotas**: Dynamically tracks your Target Rows limit (`TARGET_ROW_COUNT`) and limits URL queuing out-of-the-box (queuing 100 max per source block)—drastically minimizing IP blocks and RAM spikes.

### 🔄 Self-Healing & Resilience
- **Checkpoint System**: Uses atomized file-system operations (e.g., `os.replace` on Windows) to prevent corrupt checkpoints during saves.
- **Relaxed Data Parsing**: If the LLM generates string responses (like `brand="NOVICA"`) when float responses were expected, the Database Layer dynamically adapts string injection rather than crashing the insertion.

### 📊 Data Quality
- **Mandatory Anchoring**: The system relies on Price availability. Items without valid target prices are logged as skips.
- **Auto-Conversion**: Converts pricing into Indian Rupees (`INR`).
- **Duplicate Prevention**: URL fingerprinting dynamically discards recursive links during scraping.

---

## 🚀 Quick Start (Beginners Guide!)

### 1. Prerequisites Download

- Python 3.10 or higher
- **Cerebras API Key** (Get free credits at [cerebras.ai](https://cerebras.ai))
- git bash / command line

### 2. Installation

Open your terminal and run the following commands line by line:

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/Open-Claw-web-scraper.git
cd Open-Claw-web-scraper

# 2. Create virtual environment
python -m venv venv

# 3. Activate the environment
# -> On Windows:
venv\Scripts\activate
# -> On Linux/Mac:
source venv/bin/activate

# 4. Install dependencies
# Make sure Playwright and Scrapling are installed via the requirements sheet!
pip install -r requirements.txt
playwright install chromium
```

### 3. Setup you `.env` Configuration File

Create a copy of the available template:
```bash
cp .env.example .env
```

Open `.env` in any text editor and fill in your details:
```bash
# Set your Cerebras Key
LLM_PROVIDER=cerebras
CEREBRAS_API_KEY=your_actual_api_key_here

# Determine how much data you want the bot to collect!
TARGET_ROW_COUNT=10
```

### 4. Run the Pipeline!

You're done. Boot it up:
```bash
python main.py
```

**Where does my data go?**
1. 📂 Raw CSV files for Excel/Pandas: `data/heartisans.csv`
2. 🗄️ Database dumps: `data/heartisans.db` (SQLite)

---

## 🧬 Data Schema

The pipeline extracts **15 structured features** for each product, specifically formatted to act as predictors for Artificial Intelligence Pricing models. 

| # | Feature | Type | Required? | Interpretation |
|---|---------|------|----------|-------------|
| 1 | `material_used` | String | ✅ | Primary material (e.g., "Gold", "Mahogany") |
| 2 | `valuable_gem` | String | ❌ | Gemstone type (e.g., "Diamond") |
| 3 | `expensive_material` | String | ❌ | Precious metals |
| 4 | `origin` | String | ✅ | Country/region of origin |
| 5 | `date_of_manufacture` | String | ✅ | Year or era (e.g., "1950s") |
| 6 | `defects` | String | ❌ | Identified damages |
| 7 | `scratches` | Bool | ✅ | Presence of superficial scratches |
| 8 | `colour` | String | ✅ | Primary display color |
| 9 | **`current_market_price`** | Float | ⚠️ | **Price in INR - Critical Target Label** |
| 10| `seller_reputation` | String | ❌ | String or Number Rating (e.g. 5/5) |
| 11| `dimensions` | String | ❌ | Physical dimension format |
| 12| `weight` | String | ❌ | Scaled weight |
| 13| `work_type` | Enum | ✅ | Handwork / Machine / Unknown |
| 14| `brand` | String | ❌ | Brand name |
| 15| `limited_edition` | Bool | ✅ | Limited edition status |

*Note: For `current_market_price`, the LLM has permission to output `null` or `0.0` if no prices exist natively. The pipeline validator will safely filter these out to preserve absolute Database validity!*

---

## ⚙️ How Target Configurations Work

### Speed & Performance

If your PC gets loud or your internet is hanging, drop the concurrency in `.env`:
```bash
CONCURRENT_REQUESTS=5
```
This restricts how many async browser tabs open at once. If your PC operates decently, a `10` or higher provides phenomenal extraction speed.

### Supported Sites

To adjust where the scraper looks for items, edit the `config/seed_urls.yaml`. Only "enabled: true" targets are followed. Ensure CSS `product_selector` maps correctly to the site's layout.

---

## 🐛 Troubleshooting & FAQ

#### 1. "Missing or invalid price" warnings in logs

**Meaning**: Do not panic! This simply means the bot successfully landed on a page, looked everywhere using its strict filters, and figured out the product is basically **out of stock**, **unlisted**, or essentially purely informational. The bot safely tosses it away so it doesn't ruin your Machine Learning algorithms. 

#### 2. Network Errors or Site Connection Drops
The tool is built with async smart delays. Some websites severely monitor traffic. If your extraction fails:
1. Increase `MIN_DELAY_SECONDS` in your `.env`.
2. Reduce `CONCURRENT_REQUESTS` to `2`.

#### 3. Why isn't it reaching my `TARGET_ROW_COUNT` on a single website?
Your configuration limits Queuing to 100-300 items at a time explicitly to stop memory bloating. If a website only has 50 valid products left (the rest are out of stock), the script exhausts the URL tree safely and finishes what it collected up to that point.

#### 4. The script completely resets my data when I turn it off!
It shouldn't! Because check-pointing relies uniquely on `TARGET_ROW_COUNT`. If you run for 5 counts, then you run the script again independently without the checkpoint loading natively, it overwrites defaults. Review `data/checkpoints/` and append directly using SQLite. Data saved manually in CSV defaults to append-mode natively and will never overwrite!

---

## 🙏 Contributing

Open an issue for PRs related to `spider_pipeline.py` scaling functions or SQLite model integrations! The repository currently requires strictly Python 3.10 formats.

</div>
