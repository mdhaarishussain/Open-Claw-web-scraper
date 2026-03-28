"""
Central configuration management for the Heartisans Data Pipeline.
Loads settings from environment variables and provides access to configuration files.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
import yaml

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Central configuration class for the pipeline"""

    # Paths
    PROJECT_ROOT = Path(__file__).parent.parent
    CONFIG_DIR = PROJECT_ROOT / "config"
    SRC_DIR = PROJECT_ROOT / "src"
    DATA_DIR = PROJECT_ROOT / "data"
    LOGS_DIR = PROJECT_ROOT / "logs"
    CHECKPOINT_DIR = DATA_DIR / "checkpoints"
    CRAWL_DIR = DATA_DIR / "crawl_data"
    PROMPTS_DIR = PROJECT_ROOT / "prompts"
    TESTS_DIR = PROJECT_ROOT / "tests"

    # Storage Configuration
    DATABASE_PATH = os.getenv("DATABASE_PATH", str(DATA_DIR / "heartisans.db"))  # SQLite (kept for querying)
    CSV_PATH = os.getenv("CSV_PATH", str(DATA_DIR / "heartisans.csv"))  # Primary human-readable output

    # Currency
    CURRENCY = os.getenv("CURRENCY", "INR")  # All prices normalized to INR

    # LLM Configuration
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "cerebras")
    LLM_FALLBACK = os.getenv("LLM_FALLBACK", None)

    # Ollama Settings
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    # OpenAI Settings
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Anthropic Settings
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307")

    # Cerebras Settings (Fast inference with Llama models)
    CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")
    CEREBRAS_MODEL = os.getenv("CEREBRAS_MODEL", "gpt-oss-120b")

    # Scraping Configuration
    MIN_DELAY = float(os.getenv("MIN_DELAY_SECONDS", "2"))
    MAX_DELAY = float(os.getenv("MAX_DELAY_SECONDS", "7"))
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    USER_AGENT = os.getenv(
        "USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    )

    # Concurrency (Spider framework)
    CONCURRENT_REQUESTS = int(os.getenv("CONCURRENT_REQUESTS", "5"))

    # Circuit Breaker Configuration
    CIRCUIT_BREAKER_THRESHOLD = int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "5"))
    CIRCUIT_BREAKER_TIMEOUT = int(os.getenv("CIRCUIT_BREAKER_TIMEOUT", "300"))

    # Pipeline Configuration
    TARGET_ROW_COUNT = int(os.getenv("TARGET_ROW_COUNT", "10000"))
    CHECKPOINT_INTERVAL = int(os.getenv("CHECKPOINT_INTERVAL", "100"))

    # Logging Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def ensure_directories(cls):
        """Create necessary directories if they don't exist"""
        cls.DATA_DIR.mkdir(exist_ok=True)
        cls.LOGS_DIR.mkdir(exist_ok=True)
        cls.CHECKPOINT_DIR.mkdir(exist_ok=True)
        cls.CRAWL_DIR.mkdir(exist_ok=True)

    @classmethod
    def load_seed_urls(cls):
        """Load seed URLs from YAML configuration file"""
        seed_urls_path = cls.CONFIG_DIR / "seed_urls.yaml"
        if not seed_urls_path.exists():
            raise FileNotFoundError(f"Seed URLs configuration not found at {seed_urls_path}")

        with open(seed_urls_path, 'r') as f:
            return yaml.safe_load(f)

    @classmethod
    def load_extraction_prompt(cls):
        """Load the LLM extraction system prompt"""
        prompt_path = cls.PROMPTS_DIR / "extraction_prompt.txt"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Extraction prompt not found at {prompt_path}")

        with open(prompt_path, 'r') as f:
            return f.read()

    @classmethod
    def validate(cls):
        """Validate configuration settings"""
        errors = []

        # Check LLM provider is valid
        valid_providers = ['ollama', 'openai', 'anthropic', 'cerebras']
        if cls.LLM_PROVIDER not in valid_providers:
            errors.append(f"LLM_PROVIDER must be one of {valid_providers}, got: {cls.LLM_PROVIDER}")

        # Check API keys if using cloud providers
        if cls.LLM_PROVIDER == 'openai' and not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
        if cls.LLM_PROVIDER == 'anthropic' and not cls.ANTHROPIC_API_KEY:
            errors.append("ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic")
        if cls.LLM_PROVIDER == 'cerebras' and not cls.CEREBRAS_API_KEY:
            errors.append("CEREBRAS_API_KEY is required when LLM_PROVIDER=cerebras")

        # Check fallback provider if specified
        if cls.LLM_FALLBACK:
            if cls.LLM_FALLBACK not in valid_providers:
                errors.append(f"LLM_FALLBACK must be one of {valid_providers}, got: {cls.LLM_FALLBACK}")
            if cls.LLM_FALLBACK == cls.LLM_PROVIDER:
                errors.append("LLM_FALLBACK cannot be the same as LLM_PROVIDER")

        # Check delays are logical
        if cls.MIN_DELAY >= cls.MAX_DELAY:
            errors.append(f"MIN_DELAY ({cls.MIN_DELAY}) must be less than MAX_DELAY ({cls.MAX_DELAY})")

        # Check positive values
        if cls.REQUEST_TIMEOUT <= 0:
            errors.append(f"REQUEST_TIMEOUT must be positive, got: {cls.REQUEST_TIMEOUT}")
        if cls.MAX_RETRIES < 0:
            errors.append(f"MAX_RETRIES must be non-negative, got: {cls.MAX_RETRIES}")
        if cls.TARGET_ROW_COUNT <= 0:
            errors.append(f"TARGET_ROW_COUNT must be positive, got: {cls.TARGET_ROW_COUNT}")
        if cls.CHECKPOINT_INTERVAL <= 0:
            errors.append(f"CHECKPOINT_INTERVAL must be positive, got: {cls.CHECKPOINT_INTERVAL}")
        if cls.CONCURRENT_REQUESTS <= 0:
            errors.append(f"CONCURRENT_REQUESTS must be positive, got: {cls.CONCURRENT_REQUESTS}")

        if errors:
            raise ValueError("Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors))

        return True


# Create a singleton instance
settings = Settings()
