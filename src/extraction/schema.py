"""
Pydantic schema for the 15 product features used in Heartisans ML model.
All prices are in INR. Fields are Optional where the LLM may not find data —
we accept partial data rather than rejecting entire products.
"""
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class WorkType(str, Enum):
    HANDWORK = "Handwork"
    MACHINE_WORK = "Machine work"
    UNKNOWN = "Unknown"


class ProductData(BaseModel):
    """
    15-feature product schema. Only current_market_price is hard-required.
    All other fields gracefully fall back to None/Unknown so valid products
    with partial info are still captured rather than discarded.
    """

    # 1. Material
    material_used: Optional[str] = Field(None, description="Primary material")

    # 2. Valuable gem
    valuable_gem: Optional[str] = Field(None, description="Gemstone type if present")

    # 3. Expensive material
    expensive_material: Optional[str] = Field(None, description="Precious metals / luxury materials")

    # 4. Origin
    origin: Optional[str] = Field(None, description="Country or region of origin")

    # 5. Date of manufacture
    date_of_manufacture: Optional[str] = Field(None, description="Year or era")

    # 6. Defects
    defects: Optional[str] = Field(None, description="Any defects or damage")

    # 7. Scratches
    scratches: Optional[bool] = Field(None, description="Scratches present?")

    # 8. Colour
    colour: Optional[str] = Field(None, description="Primary colour")

    # 9. Price in INR
    current_market_price: Optional[float] = Field(
        None,
        description="Listed price in INR",
    )

    # 10. Seller reputation
    seller_reputation: Optional[str] = Field(None)

    # 11. Dimensions
    dimensions: Optional[str] = Field(None, description="H x W x D")

    # 12. Weight
    weight: Optional[str] = Field(None, description="e.g. 50g, 2kg")

    # 13. Work type
    work_type: WorkType = Field(default=WorkType.UNKNOWN)

    # 14. Brand
    brand: Optional[str] = Field(None)

    # 15. Limited edition
    limited_edition: Optional[bool] = Field(None)

    @field_validator('current_market_price')
    @classmethod
    def price_must_be_positive_or_none(cls, v: Optional[float]) -> Optional[float]:
        if v is None or v <= 0:
            return None
        # Hard ceiling: INR 83 Cr (~$10M) — anything above is LLM hallucination
        if v > 830_000_000:
            return None
        return round(v, 2)

    @field_validator('material_used', 'origin', 'date_of_manufacture', 'colour',
                     'valuable_gem', 'expensive_material', 'defects', 'brand',
                     mode='before')
    @classmethod
    def empty_string_to_none(cls, v):
        """Convert empty strings to None rather than failing validation."""
        if isinstance(v, str):
            v = v.strip()
            return v if v else None
        return v

    def __str__(self) -> str:
        price_str = f"INR {self.current_market_price:,.0f}" if self.current_market_price else "N/A"
        return (
            f"ProductData(material={self.material_used or 'N/A'}, "
            f"origin={self.origin or 'N/A'}, "
            f"price={price_str}, "
            f"brand={self.brand or 'N/A'})"
        )
