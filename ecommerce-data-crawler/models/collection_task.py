# models/collection_task.py
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class CollectionTask(Base):
    """采集任务模型"""
    __tablename__ = 'collection_tasks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(100), nullable=False)
    platform = Column(String(50), nullable=False)
    status = Column(String(20), default='pending')
    items_collected = Column(Integer, default=0)
    total_items = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<CollectionTask(category='{self.category}', platform='{self.platform}', status='{self.status}')>"


class ScrapingRecord(Base):
    """采集记录模型"""
    __tablename__ = 'scraping_records'

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String(50), nullable=False)
    category = Column(String(100), nullable=False)
    items_scraped = Column(Integer, default=0)
    success = Column(Boolean, default=True)
    error_msg = Column(Text, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<ScrapingRecord(platform='{self.platform}', category='{self.category}', items={self.items_scraped})>"
