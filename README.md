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

Heartisans Autonomous Data Pipeline is a production-ready, enterprise-grade web scraping system designed to collect and structure luxury and antique product data for ML-powered price prediction. Built with **zero human intervention** in mind, it autonomously scrapes, extracts, validates, and stores 10,000+ product records with 15+ structured features.

### Why This Pipeline?

- ✅ **Fully Autonomous**: Set it and forget it - runs from seed URLs to completion
- ✅ **Anti-Bot Bypass**: Defeats Cloudflare, Turnstile, and other bot protections
- ✅ **LLM-Powered**: Uses Cerebras Llama 3.3 70B for lightning-fast, accurate extraction
- ✅ **Self-Healing**: Circuit breakers, retry logic, and automatic recovery
- ✅ **Production Ready**: Checkpoint system, comprehensive logging, and metrics

---

## ✨ Features

### 🤖 LLM-Powered Extraction
- **Cerebras Inference** (Primary): Ultra-fast Llama 3.3 70B inference (~100x faster than local)
- **Multi-Provider Support**: OpenAI, Anthropic, Ollama as alternatives
- **Structured Output**: Extracts 15 features with Pydantic validation
- **Smart Fallback**: Automatic provider switching on failures

### 🕵️ Stealth Scraping
- **Scrapling Integration**: Playwright-based stealth browser automation
- **Anti-Bot Bypass**: Cloudflare, Turnstile, reCAPTCHA handling
- **Human-Like Behavior**: Random delays (2-7s), realistic browsing patterns
- **Circuit Breaker**: Auto-blocks failing domains (5 failures → 5min timeout)

### 🔄 Self-Healing & Resilience
- **Checkpoint System**: Auto-saves every 100 rows - resume anytime
- **Retry Logic**: 3 attempts with exponential backoff
- **Error Categorization**: Scrape, extraction, validation, storage failures tracked
- **Graceful Degradation**: Skip bad items, continue pipeline

### 📊 Data Quality
- **Strict Validation**: Pydantic models with custom validators
- **Price Mandatory**: Automatically discards items without valid prices
- **Currency Normalization**: Converts all prices to INR
- **Duplicate Prevention**: URL-based deduplication

### 🎛️ Monitoring & Observability
- **Real-Time Progress**: Live console output with row counts
- **Comprehensive Logging**: Separate files for info, errors, and debug
- **Final Reports**: Success rates, timing stats, failure breakdowns
- **Metrics Collection**: Scrape times, extraction times, confidence scores

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- **Cerebras API Key** (Get free credits at [cerebras.ai](https://cerebras.ai))
- pip (Python package manager)
- ~100MB disk space

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/Open-Claw-web-scraper.git
cd Open-Claw-web-scraper

# 2. Create virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env

# 5. Edit .env and add your Cerebras API key
# LLM_PROVIDER=cerebras
# CEREBRAS_API_KEY=your_actual_api_key_here
```

### Configure Seed URLs

Edit `config/seed_urls.yaml` to add your target websites:

```yaml
sources:
  - name: "your_source_name"
    base_url: "https://example.com/antiques"
    category: "luxury_items"
    product_selector: "a.product-link"  # CSS selector
    next_page_selector: "a.next-page"   # CSS selector
    enabled: true
```

### Run the Pipeline

```bash
# Start with a small test (10 rows)
# Edit .env: TARGET_ROW_COUNT=10

python main.py
```

**That's it!** The pipeline will:
1. ✅ Load configuration and validate settings
2. ✅ Start scraping from seed URLs
3. ✅ Extract data using Cerebras LLM
4. ✅ Validate and store in SQLite
5. ✅ Save checkpoints every 100 rows
6. ✅ Generate final report and export CSV

---

## 📐 Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     main.py                              │
│                    Entry Point                           │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │  AutonomousPipeline         │
        │  (Orchestrator)             │
        └────────────┬────────────────┘
                     │
        ┌────────────┴────────────┐
        │                          │
        ▼                          ▼
┌──────────────┐          ┌──────────────┐
│ StateManager │          │ RateLimiter  │
│ (Checkpoints)│          │ (Anti-Ban)   │
└──────────────┘          └──────────────┘
        │                          │
        └────────────┬─────────────┘
                     │
        ┌────────────┴──────────────┐
        │                            │
        ▼                            ▼
┌─────────────────┐      ┌──────────────────┐
│ StealthyFetcher │      │  LLMExtractor     │
│ (Scrapling)     │  →   │  (Cerebras)       │
└─────────────────┘      └──────────────────┘
                                    │
                                    ▼
                         ┌──────────────────┐
                         │  ProductData     │
                         │  (Pydantic)      │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │   Database       │
                         │   (SQLite)       │
                         └──────────────────┘
```

**See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed system design.**

---

## 🧬 Data Schema

The pipeline extracts **15 structured features** for each product:

| # | Feature | Type | Required | Description |
|---|---------|------|----------|-------------|
| 1 | `material_used` | str | ✅ | Primary material (e.g., "Gold", "Mahogany") |
| 2 | `valuable_gem` | str | ❌ | Gemstone type (e.g., "Diamond", "Ruby") |
| 3 | `expensive_material` | str | ❌ | Precious metals (e.g., "18k Gold") |
| 4 | `origin` | str | ✅ | Country/region (e.g., "Switzerland") |
| 5 | `date_of_manufacture` | str | ✅ | Year or era (e.g., "1950s") |
| 6 | `defects` | str | ❌ | Description of damage |
| 7 | `scratches` | bool | ✅ | Presence of scratches |
| 8 | `colour` | str | ✅ | Primary color |
| 9 | **`current_market_price`** | float | ✅⚠️ | **Price in INR - CRITICAL FIELD** |
| 10 | `seller_reputation` | float | ❌ | Rating 0-10 |
| 11 | `dimensions` | str | ❌ | Physical dimensions |
| 12 | `weight` | str | ❌ | Weight with unit |
| 13 | `work_type` | enum | ✅ | Handwork/Machine/Unknown |
| 14 | `brand` | str | ❌ | Brand name if any |
| 15 | `limited_edition` | bool | ✅ | Limited edition status |

**⚠️ Critical Rule**: Items without valid `current_market_price` are automatically discarded (no hallucination).

---

## 🎛️ Configuration

### LLM Providers

The pipeline supports multiple LLM providers. **Cerebras is recommended** for speed and cost-effectiveness.

#### Option 1: Cerebras (Recommended) ⭐

```bash
# .env
LLM_PROVIDER=cerebras
CEREBRAS_API_KEY=your_cerebras_api_key
CEREBRAS_MODEL=llama3.3-70b
```

**Why Cerebras?**
- ⚡ **Ultra-Fast**: ~100x faster inference than local Llama
- 💰 **Cost-Effective**: Competitive pricing with free tier
- 🎯 **High Quality**: Llama 3.3 70B performance
- 🌐 **OpenAI-Compatible**: Drop-in replacement

#### Option 2: OpenAI

```bash
# .env
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini
```

#### Option 3: Anthropic

```bash
# .env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_anthropic_api_key
ANTHROPIC_MODEL=claude-3-haiku-20240307
```

#### Option 4: Ollama (Local)

```bash
# .env
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3
OLLAMA_HOST=http://localhost:11434

# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Pull model
ollama pull llama3
```

### Rate Limiting

```bash
# .env
MIN_DELAY_SECONDS=2          # Minimum delay between requests
MAX_DELAY_SECONDS=7          # Maximum delay between requests
CIRCUIT_BREAKER_THRESHOLD=5  # Failures before domain block
CIRCUIT_BREAKER_TIMEOUT=300  # Block duration in seconds
```

### Pipeline Settings

```bash
# .env
TARGET_ROW_COUNT=10000       # Total rows to collect
CHECKPOINT_INTERVAL=100      # Save progress every N rows
DATABASE_PATH=./data/heartisans.db
LOG_LEVEL=INFO
```

---

## 📊 Outputs

### Database
- **Location**: `data/heartisans.db`
- **Format**: SQLite
- **Schema**: 15 features + metadata (URL, timestamp, confidence)
- **Indexes**: URL (unique), price, brand

### CSV Export
- **Auto-Generated**: On pipeline completion
- **Location**: `data/heartisans_dataset_YYYYMMDD_HHMMSS.csv`
- **Format**: UTF-8 encoded, comma-separated
- **Use Case**: Direct import into pandas, Excel, ML pipelines

### Logs
- **Pipeline Log**: `logs/pipeline_YYYYMMDD_HHMMSS.log` (all events)
- **Error Log**: `logs/errors_YYYYMMDD_HHMMSS.log` (errors only)
- **Console Output**: Real-time progress

### Checkpoints
- **Location**: `data/checkpoints/pipeline_state.pkl`
- **Format**: Python pickle
- **Contents**: Progress, URLs processed, metrics
- **Usage**: Automatic resume on restart

---

## 🔍 Monitoring

### Real-Time Console Output

```
=====================================================================
HEARTISANS AUTONOMOUS DATA PIPELINE
=====================================================================
Target rows: 10,000
LLM Provider: cerebras
Database: ./data/heartisans.db
Checkpoint interval: 100 rows
=====================================================================

Processing product: https://example.com/antiques/item-123...
✓ Successfully extracted: ₹12,500.00 | Brand: Tiffany & Co | Confidence: 0.94
✓ Successfully stored product #1

Processing product: https://example.com/antiques/item-456...
✓ Successfully extracted: ₹8,750.00 | Brand: N/A | Confidence: 0.89
✓ Successfully stored product #2

...

Checkpoint saved. Progress: 100/10000 (1.0%)
Success rate: 87.3% | Avg scrape time: 6.2s | Avg extraction time: 2.1s

...

=====================================================================
PIPELINE EXECUTION REPORT
=====================================================================
Total rows collected:     10,000
URLs processed:           11,458
URLs failed:              1,458
Success rate:             87.3%
Avg scrape time:          6.18s
Avg extraction time:      2.14s
Total runtime:            19h 42m 15s

Failures by type:
  - scrape               : 523
  - extraction           : 412
  - no_price             : 389
  - validation           : 134
=====================================================================
Pipeline execution completed successfully!
=====================================================================
```

---

## 🐛 Troubleshooting

### Common Issues

#### 1. "CEREBRAS_API_KEY is required"

**Solution**: Add your Cerebras API key to `.env`:
```bash
CEREBRAS_API_KEY=csk-xxxxxxxxxxxxxxxxxxxxxx
```

Get your key at [cloud.cerebras.ai](https://cloud.cerebras.ai)

#### 2 "Failed to fetch page" errors

**Causes**:
- Website blocking scraper
- Network issues
- Invalid URL

**Solutions**:
- Increase delays in `.env`: `MIN_DELAY_SECONDS=5`, `MAX_DELAY_SECONDS=10`
- Check if website is accessible in browser
- Verify seed URLs in `config/seed_urls.yaml`
- Check `logs/errors_*.log` for details

#### 3. "Circuit breaker open" warnings

**Meaning**: Too many failures for a domain (auto-blocked for 5 minutes)

**Solutions**:
- Wait for timeout to expire
- Check if website structure changed
- Increase delays to avoid detection
- Verify CSS selectors are correct

#### 4. Low success rate (<70%)

**Solutions**:
```bash
# 1. Increase rate limiting
MIN_DELAY_SECONDS=5
MAX_DELAY_SECONDS=12

# 2. Check selectors
# Open browser DevTools → Console:
document.querySelectorAll("your selector")

# 3. Try different LLM provider
LLM_PROVIDER=openai  # or anthropic

# 4. Review extraction prompt
# Edit: prompts/extraction_prompt.txt
```

#### 5. "Extraction failed" errors

**Causes**:
- LLM provider API issues
- Rate limits hit
- Invalid HTML content

**Solutions**:
- Check LLM provider status
- Verify API key is valid
- Try fallback provider:
  ```bash
  LLM_PROVIDER=cerebras
  LLM_FALLBACK=openai  # Falls back if Cerebras fails
  ```

### Debug Mode

Enable detailed logging:

```bash
# .env
LOG_LEVEL=DEBUG
```

Then check `logs/pipeline_*.log` for detailed execution trace.

---

## 📖 Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)**: Detailed system design, data flow, patterns
- **[PRD.md](PRD.md)**: Original product requirements document
- **[API Reference](#)**: Coming soon
- **[FAQ](#)**: Coming soon

---

## 🙏 Best Practices

### Before You Start

1. ✅ **Start Small**: Set `TARGET_ROW_COUNT=10` for testing
2. ✅ **Check robots.txt**: Respect website crawling policies
3. ✅ **Test Selectors**: Verify CSS selectors in browser DevTools
4. ✅ **Conservative Rate Limits**: Start with 5-10 second delays
5. ✅ **Monitor First Hour**: Watch logs closely for issues

### During Execution

1. ✅ **Don't Interrupt**: Let checkpoints save naturally (every 100 rows)
2. ✅ **Monitor Success Rate**: Should be >75% ideally
3. ✅ **Check Logs Periodically**: Look for patterns in errors
4. ✅ **Watch for Blocks**: Circuit breaker warnings indicate detection

### After Completion

1. ✅ **Validate Data Quality**: Check CSV for completeness
2. ✅ **Review Price Distribution**: Look for outliers
3. ✅ **Check for Duplicates**: Verify URL uniqueness
4. ✅ **Export to CSV**: `data/heartisans_dataset_*.csv`

---

## ⚖️ Legal & Ethical Considerations

**IMPORTANT**: Users are fully responsible for compliance with laws and terms of service.

- ✅ **Permission**: Ensure you have permission to scrape target websites
- ✅ **robots.txt**: Respect crawling directives
- ✅ **Rate Limiting**: Don't overload servers (use appropriate delays)
- ✅ **Terms of Service**: Review and comply with website ToS
- ✅ **Personal Data**: This pipeline should only scrape public product data
- ✅ **Attribution**: Credit sources if required

**This tool is for educational and research purposes.**

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📜 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

**Disclaimer**: Users are responsible for compliance with applicable laws and terms of service.

---

## 🌟 Acknowledgments

- **[Scrapling](https://github.com/D4Vinci/Scrapling)**: Stealth web scraping library
- **[Cerebras](https://cerebras.ai)**: Ultra-fast LLM inference
- **[Pydantic](https://pydantic.dev)**: Data validation library
- **[SQLAlchemy](https://www.sqlalchemy.org)**: SQL toolkit and ORM
- **Heartisans Team**: For the vision and requirements

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/Open-Claw-web-scraper/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/Open-Claw-web-scraper/discussions)
- **Email**: support@heartisans.com

---

<div align="center">

**Built with ❤️ for Heartisans Price Prediction ML Model**

</div>
