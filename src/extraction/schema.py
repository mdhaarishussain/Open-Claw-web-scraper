"""
Pydantic schema definitions for the 15 required features of luxury and antique items.
These models enforce strict data validation and type safety.
"""
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator


class WorkType(str, Enum):
    """Type of craftsmanship"""
    HANDWORK = "Handwork"
    MACHINE_WORK = "Machine work"
    UNKNOWN = "Unknown"


class ProductData(BaseModel):
    """
    Schema for luxury/antique product data with 15 required features.
    This model enforces strict validation, especially for the critical price field.
    """

    # 1. Material used (required)
    material_used: str = Field(
        ...,
        min_length=1,
        description="Primary material the item is made from"
    )

    # 2. Valuable gem (optional)
    valuable_gem: Optional[str] = Field(
        None,
        description="Type of valuable gemstone if present"
    )

    # 3. Expensive material (optional)
    expensive_material: Optional[str] = Field(
        None,
        description="Precious metals or expensive materials used"
    )

    # 4. Origin (required)
    origin: str = Field(
        ...,
        min_length=1,
        description="Country or region of origin/manufacture"
    )

    # 5. Date of manufacture (required)
    date_of_manufacture: str = Field(
        ...,
        min_length=1,
        description="Year or era of manufacture"
    )

    # 6. Defects (optional)
    defects: Optional[str] = Field(
        None,
        description="Description of any defects or damage"
    )

    # 7. Scratches (required)
    scratches: bool = Field(
        ...,
        description="Presence of scratches"
    )

    # 8. Colour (required)
    colour: str = Field(
        ...,
        min_length=1,
        description="Primary color of the item"
    )

    # 9. Current market price (required, CRITICAL field)
    current_market_price: float = Field(
        ...,
        gt=0,
        description="Listed price in USD, must be positive"
    )

    # 10. Seller reputation (optional, 0-10 scale)
    seller_reputation: Optional[float] = Field(
        None,
        ge=0,
        le=10,
        description="Normalized seller reputation score (0-10)"
    )

    # 11. Dimensions (optional)
    dimensions: Optional[str] = Field(
        None,
        description="Physical dimensions (Height x Width x Depth)"
    )

    # 12. Weight (optional)
    weight: Optional[str] = Field(
        None,
        description="Weight with unit (e.g., 50g, 2kg)"
    )

    # 13. Work type (required)
    work_type: WorkType = Field(
        default=WorkType.UNKNOWN,
        description="Type of craftsmanship: Handwork, Machine work, or Unknown"
    )

    # 14. Brand (optional)
    brand: Optional[str] = Field(
        None,
        description="Brand name if from a recognized brand"
    )

    # 15. Limited edition (required)
    limited_edition: bool = Field(
        default=False,
        description="Whether the item is limited edition/rare/collectible"
    )

    @field_validator('current_market_price')
    @classmethod
    def price_must_be_positive(cls, v: float) -> float:
        """
        CRITICAL VALIDATOR: Price must be positive.
        This is the ML target variable and cannot be missing or invalid.
        """
        if v is None or v <= 0:
            raise ValueError('current_market_price must be positive and cannot be null')
        if v > 10_000_000:  # Sanity check: >$10M seems like hallucination
            raise ValueError(f'current_market_price seems unrealistic: ${v:,.2f}')
        return v

    @field_validator('seller_reputation')
    @classmethod
    def reputation_in_range(cls, v: Optional[float]) -> Optional[float]:
        """Ensure seller reputation is in valid range if provided"""
        if v is not None and (v < 0 or v > 10):
            raise ValueError(f'seller_reputation must be between 0 and 10, got {v}')
        return v

    @field_validator('material_used', 'origin', 'date_of_manufacture', 'colour')
    @classmethod
    def required_fields_not_empty(cls, v: str) -> str:
        """Ensure required string fields are not just whitespace"""
        if not v or not v.strip():
            raise ValueError('Required field cannot be empty or whitespace')
        return v.strip()

    @model_validator(mode='after')
    def validate_consistency(self):
        """Cross-field validation for logical consistency"""
        # If expensive_material is set, it should match material_used context
        if self.expensive_material and self.material_used:
            expensive_keywords = ['gold', 'platinum', 'silver', 'diamond']
            if any(kw in self.expensive_material.lower() for kw in expensive_keywords):
                if not any(kw in self.material_used.lower() for kw in expensive_keywords):
                    # This is just a warning, not a hard error
                    pass

        # If limited_edition is true, there's often a brand associated
        # (but not always, so not a hard rule)

        return self

    model_config = {
        "json_schema_extra": {
            "example": {
                "material_used": "18k Gold",
                "valuable_gem": "Diamond",
                "expensive_material": "White Gold",
                "origin": "Switzerland",
                "date_of_manufacture": "2020",
                "defects": None,
                "scratches": False,
                "colour": "Gold",
                "current_market_price": 5500.00,
                "seller_reputation": 9.2,
                "dimensions": "40mm diameter",
                "weight": "150g",
                "work_type": "Handwork",
                "brand": "Rolex",
                "limited_edition": True
            }
        }
    }

    def __str__(self) -> str:
        """String representation for logging"""
        return (f"ProductData(material={self.material_used}, "
                f"origin={self.origin}, price=${self.current_market_price:,.2f}, "
                f"brand={self.brand or 'N/A'})")
