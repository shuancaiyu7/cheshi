# models/category.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, create_engine
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


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


class CategoryStats(Base):
    """类目统计模型"""
    __tablename__ = 'category_stats'

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(100), nullable=False, index=True)
    platform = Column(String(50), nullable=False)
    avg_price = Column(Float, nullable=True)
    min_price = Column(Float, nullable=True)
    max_price = Column(Float, nullable=True)
    total_products = Column(Integer, default=0)
    total_sales = Column(Integer, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<CategoryStats(category='{self.category}', products={self.total_products})>"
