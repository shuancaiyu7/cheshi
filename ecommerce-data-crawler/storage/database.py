# storage/database.py
import asyncio
import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine, desc, func, and_, or_
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from models.product import Product, Category, CollectionTask, init_db
from models.category import CategoryStats
from models.collection_task import ScrapingRecord
from crawler.base_crawler import ProductData
from utils.config import get_db_url, load_config

logger = logging.getLogger(__name__)


class DatabaseManager:
    """数据库管理器"""

    def __init__(self, db_url: str = None):
        if db_url is None:
            config = load_config()
            db_url = get_db_url(config)
        self.db_url = db_url
        self._ensure_data_directory()
        self.engine, self.SessionLocal = init_db(db_url)
        self._create_extra_tables()

    def _ensure_data_directory(self):
        if self.db_url.startswith("sqlite:///"):
            db_path = self.db_url.replace("sqlite:///", "")
            db_path = Path(db_path)
            db_dir = db_path.parent
            db_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Data directory ensured: {db_dir}")

    def _create_extra_tables(self):
        """创建额外的表（CategoryStats, ScrapingRecord）"""
        from sqlalchemy import MetaData
        meta = MetaData()
        meta.reflect(bind=self.engine)
        if 'category_stats' not in meta.tables:
            CategoryStats.__table__.create(self.engine)
            logger.info("Created category_stats table")
        if 'scraping_records' not in meta.tables:
            ScrapingRecord.__table__.create(self.engine)
            logger.info("Created scraping_records table")

    def get_session(self) -> Session:
        return self.SessionLocal()

    def close_session(self, session: Session):
        session.close()

    async def save_product(self, product: ProductData) -> bool:
        session = self.get_session()
        try:
            existing = session.query(Product).filter_by(product_id=product.product_id).first()
            if existing:
                existing.title = product.title
                existing.price = product.price
                existing.original_price = product.original_price
                existing.sales = product.sales
                existing.shop_name = product.shop_name
                existing.ratings = product.ratings
                existing.comments_count = product.comments_count
                existing.is_in_stock = product.is_in_stock
                existing.updated_at = datetime.utcnow()
                existing.raw_data = json.dumps(product.raw_data, ensure_ascii=False) if product.raw_data else None
            else:
                new_product = Product(
                    product_id=product.product_id,
                    title=product.title,
                    price=product.price,
                    original_price=product.original_price,
                    sales=product.sales,
                    shop_name=product.shop_name,
                    platform=product.platform,
                    category=product.category,
                    image_url=product.image_url,
                    product_url=product.product_url,
                    ratings=product.ratings,
                    comments_count=product.comments_count,
                    is_in_stock=product.is_in_stock,
                    scraped_at=product.scraped_at,
                    raw_data=json.dumps(product.raw_data, ensure_ascii=False) if product.raw_data else None
                )
                session.add(new_product)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving product: {e}")
            return False
        finally:
            self.close_session(session)

    async def save_products(self, products: List[ProductData]) -> int:
        saved_count = 0
        for product in products:
            if await self.save_product(product):
                saved_count += 1
        logger.info(f"Saved {saved_count}/{len(products)} products")
        return saved_count

    async def get_products(self, platform=None, category=None,
                          min_price=None, max_price=None,
                          sort_by='price', order='asc',
                          limit=100, offset=0):
        session = self.get_session()
        try:
            query = session.query(Product)
            if platform:
                query = query.filter(Product.platform == platform)
            if category:
                query = query.filter(Product.category == category)
            if min_price is not None:
                query = query.filter(Product.price >= min_price)
            if max_price is not None:
                query = query.filter(Product.price <= max_price)
            sort_field = getattr(Product, sort_by, Product.price)
            if order == 'desc':
                query = query.order_by(desc(sort_field))
            else:
                query = query.order_by(sort_field)
            products = query.limit(limit).offset(offset).all()
            result = []
            for p in products:
                result.append({
                    'id': p.id,
                    'product_id': p.product_id,
                    'title': p.title,
                    'price': p.price,
                    'original_price': p.original_price,
                    'sales': p.sales,
                    'shop_name': p.shop_name,
                    'platform': p.platform,
                    'category': p.category,
                    'ratings': p.ratings,
                    'comments_count': p.comments_count,
                    'is_in_stock': p.is_in_stock,
                    'scraped_at': p.scraped_at.isoformat() if p.scraped_at else None,
                })
            return result
        except Exception as e:
            logger.error(f"Error querying products: {e}")
            return []
        finally:
            self.close_session(session)

    async def get_product_by_id(self, product_id: str):
        session = self.get_session()
        try:
            product = session.query(Product).filter_by(product_id=product_id).first()
            if product:
                return {
                    'id': product.id,
                    'product_id': product.product_id,
                    'title': product.title,
                    'price': product.price,
                    'original_price': product.original_price,
                    'sales': product.sales,
                    'shop_name': product.shop_name,
                    'platform': product.platform,
                    'category': product.category,
                    'ratings': product.ratings,
                    'comments_count': product.comments_count,
                    'is_in_stock': product.is_in_stock,
                    'scraped_at': product.scraped_at.isoformat() if product.scraped_at else None,
                }
            return None
        finally:
            self.close_session(session)

    def get_statistics(self):
        """同步方法获取统计数据"""
        session = self.get_session()
        try:
            stats = {
                'total_products': session.query(func.count(Product.id)).scalar() or 0,
                'total_platforms': session.query(func.count(func.distinct(Product.platform))).scalar() or 0,
                'total_categories': session.query(func.count(func.distinct(Product.category))).scalar() or 0,
                'platforms': {},
                'categories': {},
            }
            platforms = session.query(
                Product.platform,
                func.count(Product.id).label('count'),
                func.avg(Product.price).label('avg_price'),
                func.min(Product.price).label('min_price'),
                func.max(Product.price).label('max_price')
            ).group_by(Product.platform).all()
            for p in platforms:
                stats['platforms'][p.platform] = {
                    'count': p.count,
                    'avg_price': round(float(p.avg_price or 0), 2),
                    'min_price': round(float(p.min_price or 0), 2),
                    'max_price': round(float(p.max_price or 0), 2),
                }
            categories = session.query(
                Product.category,
                func.count(Product.id).label('count'),
                func.avg(Product.price).label('avg_price')
            ).group_by(Product.category).all()
            for c in categories:
                stats['categories'][c.category] = {
                    'count': c.count,
                    'avg_price': round(float(c.avg_price or 0), 2),
                }
            return stats
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {'total_products': 0, 'total_platforms': 0, 'total_categories': 0, 'platforms': {}, 'categories': {}}
        finally:
            self.close_session(session)

    async def update_category_stats(self, platform: str, category: str):
        session = self.get_session()
        try:
            products = session.query(Product).filter_by(platform=platform, category=category).all()
            if not products:
                return
            prices = [p.price for p in products if p.price]
            sales = [p.comments_count for p in products if p.comments_count]
            stats = CategoryStats(
                category=category,
                platform=platform,
                avg_price=round(sum(prices) / len(prices), 2) if prices else None,
                min_price=min(prices) if prices else None,
                max_price=max(prices) if prices else None,
                total_products=len(products),
                total_sales=sum(sales) if sales else 0,
                last_updated=datetime.utcnow()
            )
            existing = session.query(CategoryStats).filter_by(category=category, platform=platform).first()
            if existing:
                existing.avg_price = stats.avg_price
                existing.min_price = stats.min_price
                existing.max_price = stats.max_price
                existing.total_products = stats.total_products
                existing.total_sales = stats.total_sales
                existing.last_updated = stats.last_updated
            else:
                session.add(stats)
            session.commit()
            logger.info(f"Updated category stats: {platform} - {category}")
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating category stats: {e}")
        finally:
            self.close_session(session)

    async def get_price_history(self, product_id: str, limit=100):
        session = self.get_session()
        try:
            product = session.query(Product).filter_by(product_id=product_id).first()
            if product:
                return [{'timestamp': product.scraped_at.isoformat() if product.scraped_at else None, 'price': product.price}]
            return []
        finally:
            self.close_session(session)

    async def export_to_csv(self, filepath, platform=None, category=None):
        import csv
        try:
            products = await self.get_products(platform=platform, category=category, limit=10000)
            if not products:
                return False
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=products[0].keys())
                writer.writeheader()
                writer.writerows(products)
            logger.info(f"Exported {len(products)} products to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")
            return False

    def close(self):
        self.engine.dispose()
        logger.info("Database connection closed")
