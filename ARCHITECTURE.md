# System Architecture

## Overview

The Heartisans Autonomous Data Pipeline is built as a modular, scalable system for autonomous web scraping and structured data extraction. The architecture follows a layered approach with clear separation of concerns.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        main.py                               │
│                    (Entry Point)                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Orchestration Layer                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  AutonomousPipeline (pipeline.py)                   │  │
│  │  - Autonomous loop coordination                      │  │
│  │  - Pagination handling                               │  │
│  │  - Error recovery                                    │  │
│  └──────────────────┬───────────────────────────────────┘  │
│                     │                                        │
│  ┌──────────────────▼───────────────────────────────────┐  │
│  │  StateManager (state_manager.py)                     │  │
│  │  - Progress tracking                                 │  │
│  │  - Checkpoint management                             │  │
│  │  - Metrics collection                                │  │
│  └──────────────────────────────────────────────────────┘  │
└────────┬──────────────┬──────────────┬────────────────────┘
         │              │              │
         ▼              ▼              ▼
┌────────────┐  ┌──────────────┐  ┌──────────────┐
│  Scraping  │  │  Extraction  │  │   Storage    │
│   Layer    │  │    Layer     │  │    Layer     │
└────────────┘  └──────────────┘  └──────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Scraping Layer                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  StealthyFetcher (stealthy_fetcher.py)              │  │
│  │  - Scrapling integration                             │  │
│  │  - Anti-bot bypass (Cloudflare, Turnstile)          │  │
│  │  - Retry logic with exponential backoff              │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  RateLimiter & CircuitBreaker (rate_limiter.py)     │  │
│  │  - Human-like delays (2-7 seconds)                   │  │
│  │  - Per-domain rate tracking                          │  │
│  │  - Circuit breaker for failed domains                │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  URLNavigator (url_navigator.py)                     │  │
│  │  - Product URL extraction                            │  │
│  │  - Pagination discovery                              │  │
│  │  - Duplicate prevention                              │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   Extraction Layer                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  ProductData Schema (schema.py)                      │  │
│  │  - 15-feature Pydantic models                        │  │
│  │  - Strict price validation                           │  │
│  │  - Field validators                                  │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  LLMExtractor (llm_extractor.py)                     │  │
│  │  - Multi-provider support:                           │  │
│  │    • Cerebras (llama3.3-70b) - RECOMMENDED           │  │
│  │    • OpenAI (gpt-4o-mini)                            │  │
│  │    • Anthropic (claude-3-haiku)                      │  │
│  │    • Ollama (local llama3)                           │  │
│  │  - JSON extraction with fallback                     │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Validator (validator.py)                            │  │
│  │  - Currency normalization to INR                     │  │
│  │  - Data quality checks                               │  │
│  │  - Confidence scoring                                │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Storage Layer                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Product ORM Model (models.py)                       │  │
│  │  - SQLAlchemy model for 15 features                  │  │
│  │  - Metadata (URL, timestamp, confidence)            │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Database Manager (database.py)                      │  │
│  │  - SQLite connection management                      │  │
│  │  - CRUD operations                                   │  │
│  │  - CSV export                                        │  │
│  │  - Duplicate detection                               │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                 Configuration Layer                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Settings (settings.py)                              │  │
│  │  - Environment variables (.env)                      │  │
│  │  - Seed URLs (seed_urls.yaml)                        │  │
│  │  - LLM prompts (extraction_prompt.txt)               │  │
│  │  - Configuration validation                          │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

### High-Level Flow

```
1. Load Configuration & Seed URLs
   ↓
2. Resume from Checkpoint (if exists)
   ↓
3. For each seed URL:
   a. Fetch category page (Stealth)
   b. Extract product URLs
   c. For each product URL:
      i.   Apply rate limiting
      ii.  Fetch product page (Stealth)
      iii. Extract with LLM
      iv.  Validate data (especially price)
      v.   Store in database
      vi.  Update state
   d. Find next page
   e. Repeat until target reached
   ↓
4. Generate final report
5. Export to CSV
```

### Detailed Request Flow

```
URL → CircuitBreaker.can_proceed() → RateLimiter.wait()
    ↓
StealthyFetcher.fetch()
    ↓ (raw HTML/text)
LLMExtractor.extract()
    ↓ (JSON)
ProductData.model_validate()
    ↓ (Pydantic model)
Validator.validate()
    ↓ (validated data)
Database.insert()
    ↓
StateManager.record_success()
    ↓
Checkpoint (every 100 rows)
```

## Component Details

### 1. Orchestration Layer

**AutonomousPipeline** (`src/orchestrator/pipeline.py`)
- **Purpose**: Coordinates the entire scraping process
- **Key Features**:
  - Autonomous loop execution
  - Multi-source scraping
  - Pagination automation
  - Error handling and recovery
  - Progress monitoring

**StateManager** (`src/orchestrator/state_manager.py`)
- **Purpose**: Tracks pipeline state and enables resumption
- **Key Features**:
  - Progress tracking (row count, URLs processed)
  - Checkpoint persistence (pickle format)
  - Metrics collection (timings, success rates)
  - Failure categorization
  - Resume capability

### 2. Scraping Layer

**StealthyFetcher** (`src/scraper/stealthy_fetcher.py`)
- **Purpose**: Fetch web pages while bypassing anti-bot protections
- **Technology**: Scrapling (Playwright-based)
- **Key Features**:
  - Cloudflare bypass
  - Turnstile CAPTCHA handling
  - Retry with exponential backoff (3 attempts)
  - Timeout handling (30s default)
  - Resource blocking for speed

**RateLimiter & CircuitBreaker** (`src/scraper/rate_limiter.py`)
- **Purpose**: Prevent IP bans and handle problematic domains
- **Key Features**:
  - Randomized delays (2-7 seconds)
  - Per-domain tracking
  - Circuit breaker pattern (5 failures → 5 min block)
  - Human-like behavior simulation

**URLNavigator** (`src/scraper/url_navigator.py`)
- **Purpose**: Extract product links and handle pagination
- **Key Features**:
  - CSS selector-based link extraction
  - Next page discovery
  - Duplicate URL prevention
  - Support for multiple pagination patterns

### 3. Extraction Layer

**ProductData Schema** (`src/extraction/schema.py`)
- **Technology**: Pydantic v2
- **15 Features**:
  1. material_used (str, required)
  2. valuable_gem (Optional[str])
  3. expensive_material (Optional[str])
  4. origin (str, required)
  5. date_of_manufacture (str, required)
  6. defects (Optional[str])
  7. scratches (bool, required)
  8. colour (str, required)
  9. **current_market_price (float, required)** ← Critical field
  10. seller_reputation (Optional[float], 0-10)
  11. dimensions (Optional[str])
  12. weight (Optional[str])
  13. work_type (Enum: Handwork/Machine/Unknown)
  14. brand (Optional[str])
  15. limited_edition (bool)

**LLMExtractor** (`src/extraction/llm_extractor.py`)
- **Supported Providers**:
  - **Cerebras**: Fast Llama 3.3 70B inference (RECOMMENDED)
  - **OpenAI**: GPT-4o-mini for accuracy
  - **Anthropic**: Claude 3 Haiku for reliability
  - **Ollama**: Local Llama 3 for privacy
- **Features**:
  - Provider abstraction
  - Fallback support
  - JSON extraction
  - Error handling

**Validator** (`src/extraction/validator.py`)
- **Purpose**: Ensure data quality and consistency
- **Key Features**:
  - Currency normalization to INR
  - Price sanity checks
  - Confidence scoring
  - Cross-field validation

### 4. Storage Layer

**Product ORM** (`src/storage/models.py`)
- **Technology**: SQLAlchemy
- **Schema**: Maps 15 features + metadata
- **Indexes**: URL (unique), price, brand

**Database Manager** (`src/storage/database.py`)
- **Database**: SQLite (file-based)
- **Operations**:
  - Insert with duplicate detection
  - Bulk queries
  - CSV export
  - Statistics generation
  - Connection pooling

### 5. Configuration Layer

**Settings** (`config/settings.py`)
- **Environment Variables**: Loaded from `.env`
- **Configuration Files**:
  - `seed_urls.yaml`: Target websites
  - `extraction_prompt.txt`: LLM system prompt
- **Validation**: Startup configuration checks

## Design Patterns

### 1. Retry Pattern with Exponential Backoff
```python
@retry_on_failure(max_attempts=3, delay=2, backoff=2)
def fetch_page(url):
    # Attempt 1: wait 2s on failure
    # Attempt 2: wait 4s on failure
    # Attempt 3: raise exception
```

### 2. Circuit Breaker Pattern
```python
if not circuit_breaker.can_proceed(url):
    # Domain is blocked temporarily
    return None

try:
    result = scrape(url)
    circuit_breaker.record_success(url)
except:
    circuit_breaker.record_failure(url)
    # After 5 failures, domain is blocked for 5 minutes
```

### 3. Checkpoint Pattern
```python
for product in products:
    process(product)
    row_count += 1

    if row_count % 100 == 0:
        state.save_checkpoint()  # Enables resume
```

### 4. Strategy Pattern (LLM Providers)
```python
class LLMExtractor:
    def __init__(self, provider):
        if provider == 'cerebras':
            self.extractor = CerebrasExtractor()
        elif provider == 'openai':
            self.extractor = OpenAIExtractor()
        # ... different strategies for different providers
```

## Scalability Considerations

### Current Limitations
- **Single-threaded**: Sequential processing of URLs
- **Single machine**: No distributed scraping
- **SQLite**: File-based database (suitable for 10K-100K rows)

### Future Enhancements
- **Async scraping**: Use `asyncio` for concurrent requests
- **Distributed workers**: Celery or RQ for multi-machine scraping
- **PostgreSQL**: For larger datasets and concurrent access
- **Queue-based**: Redis queue for URL management
- **Kubernetes**: Container orchestration for cloud deployment

## Error Handling Strategy

### Error Categories
1. **Transient Errors** (retryable):
   - Network timeouts
   - Temporary server errors (5xx)
   - Rate limit warnings

2. **Permanent Errors** (not retryable):
   - Bot detection (blocked)
   - 404 Not Found
   - Invalid HTML structure

3. **Data Errors**:
   - Missing price → Discard item
   - Invalid JSON from LLM → Retry or discard
   - Validation failures → Log and discard

### Error Recovery
- **Retry**: 3 attempts with exponential backoff
- **Circuit Breaker**: Block domain after 5 failures
- **Checkpoint**: Save progress every 100 rows
- **Graceful Degradation**: Skip bad items, continue pipeline

## Security & Ethics

### Security Measures
- **API Keys**: Stored in `.env`, never committed
- **Input Validation**: All data validated with Pydantic
- **SQL Injection**: Protected by SQLAlchemy ORM
- **Rate Limiting**: Prevents overload and bans

### Ethical Considerations
- **robots.txt**: Should be checked before scraping
- **Rate Limiting**: Respects server resources
- **User-Agent**: Identifies as scraper, not browser
- **No Personal Data**: Focuses on public product listings
- **Terms of Service**: User responsible for compliance

## Performance Metrics

### Target Performance
- **Success Rate**: >80% of attempted extractions
- **Scrape Time**: ~5-10 seconds per product (including delays)
- **Extraction Time**: ~2-5 seconds per item (depends on LLM)
- **Total Time**: ~24-48 hours for 10,000 rows
- **Storage**: ~50MB for 10,000 rows (SQLite + CSV)

### Monitoring
- Real-time progress logs
- Checkpoint reports every 100 rows
- Final execution report with:
  - Total rows collected
  - Success/failure rates
  - Average timings
  - Failure breakdown by type

## Dependencies

### Core Dependencies
- **scrapling**: Stealth web scraping
- **pydantic**: Data validation
- **sqlalchemy**: ORM and database management
- **openai**: API client for OpenAI-compatible APIs (Cerebras, OpenAI)
- **anthropic**: Anthropic Claude API
- **pyyaml**: Configuration file parsing
- **python-dotenv**: Environment variable management

### Optional Dependencies
- **ollama**: Local LLM support
- **pytest**: Testing framework

## Configuration Files

### `.env`
- API keys and secrets
- LLM provider selection
- Rate limiting parameters
- Pipeline configuration

### `config/seed_urls.yaml`
- Target websites
- CSS selectors
- Category information

### `prompts/extraction_prompt.txt`
- System prompt for LLM extraction
- Field descriptions
- Extraction rules

## Testing Strategy

### Unit Tests
- Pydantic schema validation
- Database CRUD operations
- Rate limiter logic
- LLM extractor (mocked)

### Integration Tests
- Full scrape-extract-store cycle
- Checkpoint save/load
- Error recovery

### End-to-End Tests
- Mini-pipeline with small target (10-50 rows)
- Verify data quality
- Check resumption

## Deployment

### Local Deployment
```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
python main.py
```

### Cloud Deployment (Future)
- Containerize with Docker
- Deploy to AWS/GCP/Azure
- Use managed databases (RDS, Cloud SQL)
- Schedule with cron or Airflow

## Maintenance

### Regular Tasks
- **Monitor logs**: Check for new error patterns
- **Update selectors**: Websites change HTML structure
- **Adjust rate limits**: Based on success rates
- **Review data quality**: Check extracted data samples
- **Update LLM prompts**: Improve extraction accuracy

### Troubleshooting
- **Low success rate**: Increase delays, check selectors
- **Circuit breaker triggered**: Domain may be blocking, wait or adjust thresholds
- **Extraction failures**: Check LLM provider status, review prompt
- **Checkpoint corruption**: Delete and restart (loses progress)

---

**Last Updated**: 2026-03-27
**Version**: 1.0.0
**Maintainer**: Heartisans Team
