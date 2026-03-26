"""
Validator for extracted product data.
Performs additional validation beyond Pydantic schema validation.
"""
import logging
from typing import Tuple, Optional

from src.extraction.schema import ProductData

logger = logging.getLogger(__name__)


# Approximate exchange rates (as of 2024)
EXCHANGE_RATES = {
    'USD': 1.0,
    'EUR': 1.08,
    'GBP': 1.27,
    'JPY': 0.0067,
    'CHF': 1.12,
    'CAD': 0.74,
    'AUD': 0.65,
    'CNY': 0.14,
}


class Validator:
    """
    Validates extracted product data for quality and consistency.
    """

    def __init__(self):
        """Initialize validator"""
        logger.info("Validator initialized")

    def validate(self, product_data: ProductData) -> Tuple[bool, Optional[str], float]:
        """
        Validate product data beyond Pydantic schema validation.

        Args:
            product_data: Pydantic ProductData model to validate

        Returns:
            Tuple of (is_valid, error_message, confidence_score)
            - is_valid: Whether the data passes validation
            - error_message: Reason for failure if invalid, None if valid
            - confidence_score: Quality score 0-1
        """
        try:
            # Critical validation: Price must exist and be reasonable
            if not product_data.current_market_price or product_data.current_market_price <= 0:
                return False, "Missing or invalid price", 0.0

            # Price sanity check
            if product_data.current_market_price > 10_000_000:
                return False, f"Price too high (likely hallucination): ${product_data.current_market_price:,.2f}", 0.0

            if product_data.current_market_price < 1:
                return False, f"Price too low: ${product_data.current_market_price:,.2f}", 0.0

            # Calculate confidence score
            confidence = self._calculate_confidence(product_data)

            # All checks passed
            logger.debug(f"Validation passed with confidence {confidence:.2f}")
            return True, None, confidence

        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False, f"Validation exception: {str(e)}", 0.0

    def _calculate_confidence(self, product_data: ProductData) -> float:
        """
        Calculate a confidence score for the extracted data.

        Args:
            product_data: Product data to score

        Returns:
            Confidence score between 0 and 1
        """
        score = 0.0
        max_score = 0.0

        # Price exists (critical - highest weight)
        max_score += 30
        if product_data.current_market_price and product_data.current_market_price > 0:
            score += 30

        # Required fields are populated
        required_fields = [
            product_data.material_used,
            product_data.origin,
            product_data.date_of_manufacture,
            product_data.colour
        ]
        max_score += 20
        score += (sum(1 for f in required_fields if f and f.strip()) / len(required_fields)) * 20

        # Optional but valuable fields
        optional_fields = [
            product_data.valuable_gem,
            product_data.expensive_material,
            product_data.brand,
            product_data.dimensions,
            product_data.weight,
            product_data.seller_reputation
        ]
        max_score += 15
        score += (sum(1 for f in optional_fields if f) / len(optional_fields)) * 15

        # Brand often indicates higher quality data
        max_score += 10
        if product_data.brand and product_data.brand.strip():
            score += 10

        # Detailed descriptions
        max_score += 10
        if product_data.defects or product_data.expensive_material or product_data.valuable_gem:
            score += 5
        if len(product_data.material_used) > 10:  # Detailed material description
            score += 5

        # Work type is not "Unknown"
        max_score += 5
        if product_data.work_type.value != "Unknown":
            score += 5

        # Price is in reasonable range for luxury items
        max_score += 10
        if 100 <= product_data.current_market_price <= 1_000_000:
            score += 10
        elif 1 <= product_data.current_market_price <= 100:
            score += 5  # Lower confidence for very cheap items

        # Normalize to 0-1
        confidence = score / max_score if max_score > 0 else 0.0

        return round(confidence, 2)

    @staticmethod
    def normalize_price_to_usd(price: float, currency: str) -> float:
        """
        Convert a price in any currency to USD.

        Args:
            price: Price amount
            currency: Currency code (e.g., 'EUR', 'GBP')

        Returns:
            Price in USD

        Raises:
            ValueError: If currency is unknown
        """
        currency_upper = currency.upper()

        if currency_upper not in EXCHANGE_RATES:
            logger.warning(f"Unknown currency: {currency}, assuming USD")
            return price

        usd_price = price * EXCHANGE_RATES[currency_upper]
        logger.debug(f"Converted {price} {currency} to ${usd_price:.2f} USD")

        return round(usd_price, 2)
