"""
SQLAlchemy ORM models for storing product data in SQLite database.
Maps the 15 Pydantic features to database columns.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Product(Base):
    """
    Database model for luxury/antique product data.
    Stores all 15 required features plus metadata.
    """
    __tablename__ = 'products'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Metadata
    source_url = Column(String(1000), unique=True, nullable=False, index=True)
    scrape_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    extraction_confidence = Column(Float, nullable=True)  # Optional confidence score

    # The 15 required features
    # 1. Material used
    material_used = Column(String(255), nullable=False)

    # 2. Valuable gem
    valuable_gem = Column(String(255), nullable=True)

    # 3. Expensive material
    expensive_material = Column(String(255), nullable=True)

    # 4. Origin
    origin = Column(String(255), nullable=False)

    # 5. Date of manufacture
    date_of_manufacture = Column(String(255), nullable=False)

    # 6. Defects
    defects = Column(Text, nullable=True)

    # 7. Scratches
    scratches = Column(Boolean, nullable=False)

    # 8. Colour
    colour = Column(String(100), nullable=False)

    # 9. Current market price (CRITICAL - target variable for ML)
    current_market_price = Column(Float, nullable=False, index=True)

    # 10. Seller reputation
    seller_reputation = Column(Float, nullable=True)

    # 11. Dimensions
    dimensions = Column(String(255), nullable=True)

    # 12. Weight
    weight = Column(String(100), nullable=True)

    # 13. Work type
    work_type = Column(String(50), nullable=False)

    # 14. Brand
    brand = Column(String(255), nullable=True, index=True)

    # 15. Limited edition
    limited_edition = Column(Boolean, nullable=False, default=False)

    def __repr__(self) -> str:
        """String representation for debugging"""
        return (f"<Product(id={self.id}, brand={self.brand}, "
                f"price=${self.current_market_price:,.2f}, "
                f"origin={self.origin})>")

    def to_dict(self) -> dict:
        """Convert model to dictionary for serialization"""
        return {
            'id': self.id,
            'source_url': self.source_url,
            'scrape_timestamp': self.scrape_timestamp.isoformat() if self.scrape_timestamp else None,
            'extraction_confidence': self.extraction_confidence,
            'material_used': self.material_used,
            'valuable_gem': self.valuable_gem,
            'expensive_material': self.expensive_material,
            'origin': self.origin,
            'date_of_manufacture': self.date_of_manufacture,
            'defects': self.defects,
            'scratches': self.scratches,
            'colour': self.colour,
            'current_market_price': self.current_market_price,
            'seller_reputation': self.seller_reputation,
            'dimensions': self.dimensions,
            'weight': self.weight,
            'work_type': self.work_type,
            'brand': self.brand,
            'limited_edition': self.limited_edition
        }
