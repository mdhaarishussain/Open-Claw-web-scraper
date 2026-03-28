"""
Validator for extracted product data.
Performs additional validation beyond Pydantic schema validation.
All prices are in INR (Indian Rupees).
"""
import logging
from typing import Tuple, Optional

from src.extraction.schema import ProductData

logger = logging.getLogger(__name__)


# Exchange rates: other currencies → INR (approximate, as of 2026)
EXCHANGE_RATES_TO_INR = {
    'INR': 1.0,
    'USD': 83.0,
    'EUR': 90.0,
    'GBP': 105.0,
    'JPY': 0.56,
    'CHF': 93.0,
    'CAD': 61.0,
    'AUD': 54.0,
    'CNY': 11.5,
    'SGD': 62.0,
    'AED': 22.6,
    'HKD': 10.6,
}


class Validator:
    """
    Validates extracted product data for quality and consistency.
    All prices expected in INR (Indian Rupees).
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

            # Price sanity check (INR) — ₹83Cr ≈ $10M
            if product_data.current_market_price > 830_000_000:
                return (
                    False,
                    f"Price too high (likely hallucination): ₹{product_data.current_market_price:,.2f}",
                    0.0,
                )

            # ₹10 or less is suspiciously cheap for luxury/antiques
            if product_data.current_market_price < 10:
                return (
                    False,
                    f"Price too low for luxury item: ₹{product_data.current_market_price:,.2f}",
                    0.0,
                )

            # Calculate confidence score
            confidence = self._calculate_confidence(product_data)

            logger.debug(f"Validation passed with confidence {confidence:.2f}")
            return True, None, confidence

        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False, f"Validation exception: {str(e)}", 0.0

    def _calculate_confidence(self, product_data: ProductData) -> float:
        """
        Calculate a confidence score for the extracted data.

        Returns:
            Confidence score between 0 and 1
        """
        score = 0.0
        max_score = 0.0

        # Price exists (critical — highest weight)
        max_score += 30
        if product_data.current_market_price and product_data.current_market_price > 0:
            score += 30

        # Required fields are populated
        required_fields = [
            product_data.material_used,
            product_data.origin,
            product_data.date_of_manufacture,
            product_data.colour,
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
            product_data.seller_reputation,
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
        if len(product_data.material_used) > 10:
            score += 5

        # Work type is not "Unknown"
        max_score += 5
        if product_data.work_type.value != "Unknown":
            score += 5

        # Price is in reasonable range for luxury items (INR)
        # ₹8,300 ≈ $100 — ₹8,30,00,000 ≈ $1M
        max_score += 10
        if 8_300 <= product_data.current_market_price <= 83_000_000:
            score += 10
        elif 10 <= product_data.current_market_price < 8_300:
            score += 5  # Lower confidence for very cheap items

        # Normalize to 0-1
        confidence = score / max_score if max_score > 0 else 0.0

        return round(confidence, 2)

    @staticmethod
    def normalize_price_to_inr(price: float, currency: str) -> float:
        """
        Convert a price in any currency to INR.

        Args:
            price: Price amount
            currency: Currency code (e.g., 'USD', 'EUR')

        Returns:
            Price in INR

        Raises:
            ValueError: If currency is unknown
        """
        currency_upper = currency.upper()

        if currency_upper not in EXCHANGE_RATES_TO_INR:
            logger.warning(f"Unknown currency: {currency}, assuming INR")
            return price

        inr_price = price * EXCHANGE_RATES_TO_INR[currency_upper]
        logger.debug(f"Converted {price} {currency} to ₹{inr_price:,.2f} INR")

        return round(inr_price, 2)
