# models/product.py
from pathlib import Path
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

Base = declarative_base()


class Product(Base):
    """商品数据模型"""
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(String(100), unique=True, nullable=False, index=True)  # 商品唯一ID
    title = Column(String(500), nullable=False)  # 商品标题
    price = Column(Float, nullable=False)  # 价格
    original_price = Column(Float, nullable=True)  # 原价
    sales = Column(String(50), nullable=True)  # 销量
    shop_name = Column(String(200), nullable=True)  # 店铺名称
    platform = Column(String(50), nullable=False, index=True)  # 平台: jd, tmall
    category = Column(String(100), nullable=False, index=True)  # 类目
    image_url = Column(String(500), nullable=True)  # 图片URL
    product_url = Column(String(500), nullable=True)  # 商品链接
    ratings = Column(Float, nullable=True)  # 评分
    comments_count = Column(Integer, nullable=True)  # 评论数
    is_in_stock = Column(Boolean, default=True)  # 是否有货
    scraped_at = Column(DateTime, default=datetime.utcnow)  # 爬取时间
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 更新时间
    raw_data = Column(Text, nullable=True)  # 原始数据(JSON)

    def __repr__(self):
        return f"<Product(id={self.id}, title='{self.title[:30]}...', price={self.price})>"


class Category(Base):
    """类目数据模型"""
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)  # 类目名称
    platform = Column(String(50), nullable=False)  # 所属平台
    product_count = Column(Integer, default=0)  # 商品数量
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Category(name='{self.name}', platform='{self.platform}')>"


class CollectionTask(Base):
    """采集任务模型"""
    __tablename__ = 'collection_tasks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(100), nullable=False)
    platform = Column(String(50), nullable=False)
    status = Column(String(20), default='pending')  # pending, running, completed, failed
    items_collected = Column(Integer, default=0)
    total_items = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<CollectionTask(category='{self.category}', platform='{self.platform}', status='{self.status}')>"


def init_db(db_url: str = "sqlite:///./data/products.db"):
    """初始化数据库"""
    if db_url.startswith("sqlite:///"):
        db_path = db_url.replace("sqlite:///", "")
        path_obj = Path(db_path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(db_url, echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, SessionLocal
