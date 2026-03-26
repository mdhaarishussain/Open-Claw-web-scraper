"""
Database operations for storing and retrieving product data.
Provides CRUD operations, connection management, and data export functionality.
"""
import logging
import csv
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src.storage.models import Base, Product
from src.extraction.schema import ProductData
from config.settings import settings

logger = logging.getLogger(__name__)


class Database:
    """
    Database manager for product storage with CRUD operations.
    Uses SQLite as the backend storage engine.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file. Uses settings default if not provided.
        """
        self.db_path = db_path or settings.DATABASE_PATH
        self.engine = create_engine(f'sqlite:///{self.db_path}', echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)

        # Create tables if they don't exist
        self._create_tables()
        logger.info(f"Database initialized at {self.db_path}")

    def _create_tables(self):
        """Create all tables defined in models"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.debug("Database tables created/verified")
        except SQLAlchemyError as e:
            logger.error(f"Failed to create database tables: {e}")
            raise

    def get_session(self) -> Session:
        """Get a new database session"""
        return self.SessionLocal()

    def insert(self, product_data: ProductData, source_url: str, confidence: Optional[float] = None) -> Optional[Product]:
        """
        Insert a new product into the database.

        Args:
            product_data: Pydantic ProductData model
            source_url: URL where the product was scraped from
            confidence: Optional extraction confidence score (0-1)

        Returns:
            Product: The inserted Product model, or None if insertion failed

        Raises:
            IntegrityError: If product with same URL already exists
        """
        session = self.get_session()
        try:
            product = Product(
                source_url=source_url,
                scrape_timestamp=datetime.utcnow(),
                extraction_confidence=confidence,
                material_used=product_data.material_used,
                valuable_gem=product_data.valuable_gem,
                expensive_material=product_data.expensive_material,
                origin=product_data.origin,
                date_of_manufacture=product_data.date_of_manufacture,
                defects=product_data.defects,
                scratches=product_data.scratches,
                colour=product_data.colour,
                current_market_price=product_data.current_market_price,
                seller_reputation=product_data.seller_reputation,
                dimensions=product_data.dimensions,
                weight=product_data.weight,
                work_type=product_data.work_type.value,
                brand=product_data.brand,
                limited_edition=product_data.limited_edition
            )

            session.add(product)
            session.commit()
            session.refresh(product)

            logger.info(f"Inserted product {product.id} from {source_url[:50]}...")
            return product

        except IntegrityError:
            session.rollback()
            logger.warning(f"Duplicate URL, skipping: {source_url}")
            return None
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to insert product: {e}")
            raise
        finally:
            session.close()

    def get_by_url(self, url: str) -> Optional[Product]:
        """
        Retrieve a product by its source URL.

        Args:
            url: Source URL

        Returns:
            Product model or None if not found
        """
        session = self.get_session()
        try:
            product = session.query(Product).filter(Product.source_url == url).first()
            return product
        finally:
            session.close()

    def get_by_id(self, product_id: int) -> Optional[Product]:
        """
        Retrieve a product by its ID.

        Args:
            product_id: Product ID

        Returns:
            Product model or None if not found
        """
        session = self.get_session()
        try:
            product = session.query(Product).filter(Product.id == product_id).first()
            return product
        finally:
            session.close()

    def get_all(self, limit: Optional[int] = None, offset: int = 0) -> List[Product]:
        """
        Retrieve all products with optional pagination.

        Args:
            limit: Maximum number of products to return
            offset: Number of products to skip

        Returns:
            List of Product models
        """
        session = self.get_session()
        try:
            query = session.query(Product).order_by(Product.id)
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            return query.all()
        finally:
            session.close()

    def count(self) -> int:
        """
        Count total number of products in database.

        Returns:
            Total product count
        """
        session = self.get_session()
        try:
            return session.query(func.count(Product.id)).scalar()
        finally:
            session.close()

    def url_exists(self, url: str) -> bool:
        """
        Check if a URL already exists in the database.

        Args:
            url: Source URL to check

        Returns:
            True if URL exists, False otherwise
        """
        session = self.get_session()
        try:
            return session.query(Product).filter(Product.source_url == url).first() is not None
        finally:
            session.close()

    def get_price_statistics(self) -> dict:
        """
        Calculate price statistics for stored products.

        Returns:
            Dictionary with min, max, avg, and median prices
        """
        session = self.get_session()
        try:
            prices = [p.current_market_price for p in session.query(Product.current_market_price).all()]
            if not prices:
                return {'min': 0, 'max': 0, 'avg': 0, 'median': 0, 'count': 0}

            prices.sort()
            return {
                'min': min(prices),
                'max': max(prices),
                'avg': sum(prices) / len(prices),
                'median': prices[len(prices) // 2],
                'count': len(prices)
            }
        finally:
            session.close()

    def export_to_csv(self, output_path: str):
        """
        Export all products to a CSV file.

        Args:
            output_path: Path to output CSV file
        """
        products = self.get_all()

        if not products:
            logger.warning("No products to export")
            return

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            'id', 'source_url', 'scrape_timestamp', 'extraction_confidence',
            'material_used', 'valuable_gem', 'expensive_material', 'origin',
            'date_of_manufacture', 'defects', 'scratches', 'colour',
            'current_market_price', 'seller_reputation', 'dimensions',
            'weight', 'work_type', 'brand', 'limited_edition'
        ]

        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for product in products:
                writer.writerow(product.to_dict())

        logger.info(f"Exported {len(products)} products to {output_path}")

    def delete_by_id(self, product_id: int) -> bool:
        """
        Delete a product by ID.

        Args:
            product_id: Product ID to delete

        Returns:
            True if deleted, False if not found
        """
        session = self.get_session()
        try:
            product = session.query(Product).filter(Product.id == product_id).first()
            if product:
                session.delete(product)
                session.commit()
                logger.info(f"Deleted product {product_id}")
                return True
            return False
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to delete product {product_id}: {e}")
            raise
        finally:
            session.close()

    def clear_all(self):
        """
        Clear all products from the database. USE WITH CAUTION!
        """
        session = self.get_session()
        try:
            count = session.query(Product).delete()
            session.commit()
            logger.warning(f"Cleared {count} products from database")
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to clear database: {e}")
            raise
        finally:
            session.close()

    def close(self):
        """Close database engine"""
        self.engine.dispose()
        logger.debug("Database connection closed")
