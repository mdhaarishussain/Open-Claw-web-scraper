"""
LLM extractor for structured data extraction from raw HTML/text.
Supports multiple LLM providers: Ollama (local), OpenAI, Anthropic, and Cerebras.
"""
import json
import logging
import re
from typing import Optional, Dict, Any

from src.extraction.schema import ProductData
from config.settings import settings

logger = logging.getLogger(__name__)


class LLMExtractor:
    """
    Base class for LLM-based data extraction.
    Extracts structured ProductData from raw content using LLMs.
    """

    def __init__(self, provider: Optional[str] = None):
        """
        Initialize LLM extractor.

        Args:
            provider: LLM provider ('ollama', 'openai', 'anthropic', 'cerebras')
                     Uses settings default if None
        """
        self.provider = provider or settings.LLM_PROVIDER
        self.extraction_prompt = settings.load_extraction_prompt()

        # Initialize the appropriate extractor
        if self.provider == 'ollama':
            self.extractor = OllamaExtractor()
        elif self.provider == 'openai':
            self.extractor = OpenAIExtractor()
        elif self.provider == 'anthropic':
            self.extractor = AnthropicExtractor()
        elif self.provider == 'cerebras':
            self.extractor = CerebrasExtractor()
        elif self.provider == 'groq':
            self.extractor = GroqExtractor()
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

        logger.info(f"LLMExtractor initialized with provider: {self.provider}")

    def extract(self, raw_content: str, url: Optional[str] = None) -> ProductData:
        """
        Extract structured product data from raw content.

        Args:
            raw_content: Raw HTML or text content
            url: Optional source URL for context

        Returns:
            ProductData: Validated Pydantic model

        Raises:
            ValueError: If extraction or validation fails
        """
        try:
            # Call provider-specific extractor
            result_json = self.extractor.extract_json(
                system_prompt=self.extraction_prompt,
                content=raw_content
            )

            # --- DETERMINISTIC MATH LAYER ---
            price_key = "current_market_price" if "current_market_price" in result_json else "raw_price"
            if price_key in result_json and result_json[price_key] not in [None, "N/A", "", 0, "0", 0.0]:
                try:
                    price_val = float(re.sub(r'[^\d.]', '', str(result_json[price_key])))
                    curr = str(result_json.get("detected_currency", "INR")).upper()
                    
                    # Global Domain Failsafe Matrix
                    url_lower = url.lower() if url else ""
                    if any(x in url_lower for x in ['novica.com', 'therealreal.com', '1stdibs.com', 'rebag.com', 'grailed.com', 'saffronart.com']):
                        curr = "USD"
                    elif any(x in url_lower for x in ['catawiki.com', 'pamono.com']):
                        curr = "EUR"
                    elif any(x in url_lower for x in ['bonhams.com']):
                        curr = "GBP"

                    if curr == "USD":
                        result_json["current_market_price"] = round(price_val * 83.0, 2)
                    elif curr == "EUR":
                        result_json["current_market_price"] = round(price_val * 90.0, 2)
                    elif curr == "GBP":
                        result_json["current_market_price"] = round(price_val * 107.0, 2)
                    else:
                        result_json["current_market_price"] = price_val
                except Exception as ex:
                    logger.warning(f"Failed to parse price: {ex}")
            # ----------------------------------------

            # Parse and validate with Pydantic
            product_data = ProductData.model_validate(result_json)

            price_out = f"₹{product_data.current_market_price:,.2f}" if product_data.current_market_price else "N/A"
            logger.info(
                f"Successfully extracted data: "
                f"price={price_out}, "
                f"brand={product_data.brand or 'N/A'}"
            )

            return product_data

        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            raise


class OllamaExtractor:
    """Ollama local LLM extractor"""

    def __init__(self):
        """Initialize Ollama client"""
        try:
            import ollama
            self.client = ollama
            self.model = settings.OLLAMA_MODEL
            logger.info(f"Ollama initialized with model: {self.model}")
        except ImportError:
            raise ImportError("ollama package not installed. Run: pip install ollama")

    def extract_json(self, system_prompt: str, content: str) -> Dict[str, Any]:
        """Extract JSON from content using Ollama"""
        try:
            response = self.client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Extract product data from:\n\n{content[:5000]}"}  # Limit content length
                ],
                format="json"  # Request JSON format
            )

            json_str = response['message']['content']
            return json.loads(json_str)

        except Exception as e:
            logger.error(f"Ollama extraction error: {e}")
            raise


class OpenAIExtractor:
    """OpenAI API extractor"""

    def __init__(self):
        """Initialize OpenAI client"""
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
            self.model = settings.OPENAI_MODEL
            logger.info(f"OpenAI initialized with model: {self.model}")
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

    def extract_json(self, system_prompt: str, content: str) -> Dict[str, Any]:
        """Extract JSON from content using OpenAI"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Extract product data from:\n\n{content[:8000]}"}
                ],
                response_format={"type": "json_object"},
                temperature=0.1  # Low temperature for consistent extraction
            )

            json_str = response.choices[0].message.content
            return json.loads(json_str)

        except Exception as e:
            logger.error(f"OpenAI extraction error: {e}")
            raise


class AnthropicExtractor:
    """Anthropic Claude API extractor"""

    def __init__(self):
        """Initialize Anthropic client"""
        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            self.model = settings.ANTHROPIC_MODEL
            logger.info(f"Anthropic initialized with model: {self.model}")
        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")

    def extract_json(self, system_prompt: str, content: str) -> Dict[str, Any]:
        """Extract JSON from content using Anthropic"""
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": f"Extract product data from:\n\n{content[:8000]}"}
                ],
                temperature=0.1
            )

            json_str = message.content[0].text
            # Extract JSON from response (Claude might add explanation)
            if '{' in json_str:
                json_start = json_str.index('{')
                json_end = json_str.rindex('}') + 1
                json_str = json_str[json_start:json_end]

            return json.loads(json_str)

        except Exception as e:
            logger.error(f"Anthropic extraction error: {e}")
            raise


class CerebrasExtractor:
    """Cerebras Inference API extractor (fast inference with Llama models)"""

    def __init__(self):
        """Initialize Cerebras client"""
        try:
            from openai import OpenAI
            # Cerebras uses OpenAI-compatible API
            self.client = OpenAI(
                api_key=settings.CEREBRAS_API_KEY,
                base_url="https://api.cerebras.ai/v1"
            )
            self.model = settings.CEREBRAS_MODEL
            logger.info(f"Cerebras initialized with model: {self.model}")
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

    def extract_json(self, system_prompt: str, content: str) -> Dict[str, Any]:
        """Extract JSON from content using Cerebras"""
        try:
            # Try with json_object format first (not all models support it)
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Extract product data from:\n\n{content[:10000]}"}
                    ],
                    temperature=0.1,
                    max_tokens=2048,
                    response_format={"type": "json_object"}
                )
            except Exception:
                # Fallback: no response_format constraint
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt + "\n\nYou MUST respond with valid JSON only. No markdown, no explanation."},
                        {"role": "user", "content": f"Extract product data from:\n\n{content[:10000]}"}
                    ],
                    temperature=0.1,
                    max_tokens=2048,
                )

            json_str = response.choices[0].message.content

            # Extract JSON if wrapped in markdown or text
            if '```json' in json_str:
                json_start = json_str.index('```json') + 7
                json_end = json_str.rindex('```')
                json_str = json_str[json_start:json_end].strip()
            elif '{' in json_str:
                json_start = json_str.index('{')
                json_end = json_str.rindex('}') + 1
                json_str = json_str[json_start:json_end]

            return json.loads(json_str)

        except Exception as e:
            logger.error(f"Cerebras extraction error: {e}")
            raise


class GroqExtractor:
    """Groq API extractor with rate limit rotation"""

    def __init__(self):
        """Initialize Groq client"""
        try:
            from openai import OpenAI
            import os
            self.keys = []
            for k, v in os.environ.items():
                if ('GROQ' in k or 'stupidtakey' in k.lower()) and type(v) == str and v.startswith('gsk_'):
                    self.keys.append(v)
            if not self.keys:
                self.keys = [settings.GROQ_API_KEY]
            
            self.current_key_idx = 0
            self.client = OpenAI(
                api_key=self.keys[0],
                base_url="https://api.groq.com/openai/v1"
            )
            self.model = settings.GROQ_MODEL
            logger.info(f"Groq initialized with model: {self.model} and {len(self.keys)} loaded API Keys for auto-rotation.")
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

    def extract_json(self, system_prompt: str, content: str) -> Dict[str, Any]:
        """Extract JSON from content using Groq with automatic Key Swapping on 429"""
        max_retries = len(self.keys) * 2
        for attempt in range(max_retries):
            try:
                try:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"Extract product data from:\n\n{content[:10000]}"}
                        ],
                        temperature=0.1,
                        max_tokens=2048,
                        response_format={"type": "json_object"}
                    )
                except Exception as e:
                    if 'rate_limit_exceeded' in str(e).lower() or '429' in str(e):
                        raise e  # Bubble up to trigger rotation
                    
                    # Fallback: no response_format constraint
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": system_prompt + "\n\nYou MUST respond with valid JSON only. No markdown, no explanation."},
                            {"role": "user", "content": f"Extract product data from:\n\n{content[:10000]}"}
                        ],
                        temperature=0.1,
                        max_tokens=2048,
                    )

                json_str = response.choices[0].message.content

                if '```json' in json_str:
                    json_start = json_str.index('```json') + 7
                    json_end = json_str.rindex('```')
                    json_str = json_str[json_start:json_end].strip()
                elif '{' in json_str:
                    json_start = json_str.index('{')
                    json_end = json_str.rindex('}') + 1
                    json_str = json_str[json_start:json_end]

                return json.loads(json_str)

            except Exception as e:
                # Hot-swap on Rate Limit or Dead Key
                error_str = str(e).lower()
                if any(x in error_str for x in ['rate_limit_exceeded', '429', '401', 'invalid_api_key']):
                    if len(self.keys) > 1:
                        self.current_key_idx = (self.current_key_idx + 1) % len(self.keys)
                        logger.warning(f"Groq API Error ({error_str[:30]}...)! Hot-swapping to API Key #{self.current_key_idx+1}/{len(self.keys)}...")
                        self.client.api_key = self.keys[self.current_key_idx]
                        continue
                    else:
                        logger.error("Groq key failed, but no backup keys found. Pausing...")
                        import time
                        time.sleep(10)
                        
                logger.error(f"Groq extraction error: {e}")
                if attempt == max_retries - 1:
                    raise e


class SmartExtractor:
    """
    Smart extractor with fallback support.
    Tries primary LLM, falls back to secondary if configured.
    """

    def __init__(self):
        """Initialize smart extractor with fallback"""
        self.primary = LLMExtractor(provider=settings.LLM_PROVIDER)
        self.fallback = None

        if settings.LLM_FALLBACK:
            try:
                self.fallback = LLMExtractor(provider=settings.LLM_FALLBACK)
                logger.info(f"Fallback LLM configured: {settings.LLM_FALLBACK}")
            except Exception as e:
                logger.warning(f"Could not initialize fallback LLM: {e}")

    def extract(self, raw_content: str, url: Optional[str] = None) -> ProductData:
        """
        Extract with fallback support.

        Args:
            raw_content: Raw content to extract from
            url: Optional source URL

        Returns:
            ProductData: Extracted and validated data

        Raises:
            ValueError: If both primary and fallback fail
        """
        try:
            return self.primary.extract(raw_content, url)

        except Exception as e:
            logger.warning(f"Primary LLM failed: {e}")

            if self.fallback:
                logger.info("Attempting fallback LLM...")
                try:
                    return self.fallback.extract(raw_content, url)
                except Exception as fallback_error:
                    logger.error(f"Fallback LLM also failed: {fallback_error}")
                    raise ValueError(f"Both primary and fallback LLMs failed")
            else:
                raise
