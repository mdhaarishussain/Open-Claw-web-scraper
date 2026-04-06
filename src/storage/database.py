"""
Storage for Heartisans product data.
Primary output: CSV (human-readable, directly openable in Excel/Sheets).
Secondary: SQLite (kept for efficient dedup checking and queries).
"""
import csv
import logging
import threading
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

# All columns written to CSV - matches the 15 ML model columns + metadata
CSV_FIELDNAMES = [
    'id',
    'scrape_timestamp',
    'source_url',
    'extraction_confidence',
    # 15 product columns for ML
    'material_used',
    'valuable_gem',
    'expensive_material',
    'origin',
    'date_of_manufacture',
    'defects',
    'scratches',
    'colour',
    'current_market_price_inr',
    'seller_reputation',
    'dimensions',
    'weight',
    'work_type',
    'brand',
    'limited_edition',
]


class Database:
    """
    Product storage with CSV as primary output and SQLite for dedup/query.

    Every successful extraction is immediately appended to heartisans.csv
    so you can open it in Excel at any time during a run.
    """

    def __init__(self, db_path: Optional[str] = None, csv_path: Optional[str] = None):
        self.db_path = db_path or settings.DATABASE_PATH
        self.csv_path = Path(csv_path or settings.CSV_PATH)
        self._csv_lock = threading.Lock()  # Thread-safe CSV writes
        self._row_counter = 0

        # SQLite for dedup + queryability
        self.engine = create_engine(f'sqlite:///{self.db_path}', echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        self._create_tables()

        # Initialize CSV file (write header if new file)
        self._init_csv()

        existing = self.count()
        logger.info(f"Storage ready | CSV: {self.csv_path} | DB: {self.db_path} | Existing rows: {existing}")

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _create_tables(self):
        """Create SQLite tables if they don't exist."""
        try:
            Base.metadata.create_all(bind=self.engine)
        except SQLAlchemyError as e:
            logger.error(f"Failed to create database tables: {e}")
            raise

    def _init_csv(self):
        """Create CSV with header if it doesn't exist yet."""
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.csv_path.exists():
            with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
                writer.writeheader()
            logger.info(f"Created new CSV: {self.csv_path}")
        else:
            logger.info(f"Appending to existing CSV: {self.csv_path}")

    # ------------------------------------------------------------------
    # Core write operation
    # ------------------------------------------------------------------

    def insert(self, product_data: ProductData, source_url: str, confidence: Optional[float] = None) -> Optional[int]:
        """
        Store a product.
        - Appends a row to CSV immediately (primary output).
        - Also inserts into SQLite for dedup/query support.

        Returns:
            Row ID if inserted, None if duplicate.
        """
        # 1. Write to SQLite first (handles dedup via unique URL constraint)
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
                work_type=product_data.work_type.value if product_data.work_type else None,
                brand=product_data.brand,
                limited_edition=product_data.limited_edition,
            )
            session.add(product)
            session.commit()
            session.refresh(product)
            row_id = product.id

        except IntegrityError:
            session.rollback()
            logger.debug(f"Duplicate URL skipped: {source_url[:60]}")
            return None
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"SQLite insert failed: {e}")
            raise
        finally:
            session.close()

        # 2. Append to CSV (thread-safe)
        with self._csv_lock:
            self._row_counter += 1
            row = {
                'id': row_id,
                'scrape_timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                'source_url': source_url,
                'extraction_confidence': f"{confidence:.3f}" if confidence else '',
                'material_used': product_data.material_used or '',
                'valuable_gem': product_data.valuable_gem or '',
                'expensive_material': product_data.expensive_material or '',
                'origin': product_data.origin or '',
                'date_of_manufacture': product_data.date_of_manufacture or '',
                'defects': product_data.defects or '',
                'scratches': str(product_data.scratches) if product_data.scratches is not None else '',
                'colour': product_data.colour or '',
                'current_market_price_inr': f"{product_data.current_market_price:.2f}" if product_data.current_market_price else '',
                'seller_reputation': product_data.seller_reputation or '',
                'dimensions': product_data.dimensions or '',
                'weight': product_data.weight or '',
                'work_type': product_data.work_type.value if product_data.work_type else '',
                'brand': product_data.brand or '',
                'limited_edition': str(product_data.limited_edition) if product_data.limited_edition is not None else '',
            }
            with open(self.csv_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
                writer.writerow(row)

        logger.info(f"[CSV row #{self._row_counter}] INR {product_data.current_market_price:,.0f} | {product_data.brand or product_data.material_used or 'N/A'} | {source_url[:50]}")
        return row_id

    # ------------------------------------------------------------------
    # Query helpers (use SQLite for speed)
    # ------------------------------------------------------------------

    def get_session(self) -> Session:
        return self.SessionLocal()

    def count(self) -> int:
        session = self.get_session()
        try:
            return session.query(func.count(Product.id)).scalar() or 0
        finally:
            session.close()

    def url_exists(self, url: str) -> bool:
        session = self.get_session()
        try:
            return session.query(Product).filter(Product.source_url == url).first() is not None
        finally:
            session.close()

    def get_all(self, limit: Optional[int] = None, offset: int = 0) -> List[Product]:
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

    def get_price_statistics(self) -> dict:
        session = self.get_session()
        try:
            prices = [p.current_market_price for p in session.query(Product.current_market_price).all()
                      if p.current_market_price]
            if not prices:
                return {'min': 0, 'max': 0, 'avg': 0, 'median': 0, 'count': 0}
            prices.sort()
            return {
                'min': min(prices),
                'max': max(prices),
                'avg': sum(prices) / len(prices),
                'median': prices[len(prices) // 2],
                'count': len(prices),
            }
        finally:
            session.close()

    def export_to_csv(self, output_path: Optional[str] = None):
        """
        Re-export everything to a CSV. By default just returns the path
        of the live CSV since we already write directly to it.
        """
        if output_path is None:
            logger.info(f"Live CSV already at: {self.csv_path}")
            return str(self.csv_path)

        products = self.get_all()
        if not products:
            logger.warning("No products to export")
            return None

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
            writer.writeheader()
            for p in products:
                d = p.to_dict()
                d['current_market_price_inr'] = d.pop('current_market_price', '')
                writer.writerow({k: d.get(k, '') for k in CSV_FIELDNAMES})
        logger.info(f"Exported {len(products)} rows to {output_path}")
        return output_path

    def close(self):
        """Close database engine."""
        self.engine.dispose()
