# tests/test_database.py
"""
数据库模块单元测试
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from storage.database import DatabaseManager
from crawler.base_crawler import ProductData
from datetime import datetime


class TestDatabaseManager:
    """测试数据库管理器"""
    
    @pytest.fixture
    def db(self):
        """创建测试数据库实例"""
        db = DatabaseManager("sqlite:///./data/test_products.db")
        yield db
        db.close()
    
    def test_save_product(self, db):
        """测试保存商品"""
        product = ProductData(
            product_id="test_prod_001",
            title="测试手机",
            price=2999.00,
            platform="jd",
            category="手机数码"
        )
        result = asyncio.run(db.save_product(product))
        assert result == True
    
    def test_get_products(self, db):
        """测试获取商品列表"""
        # 先保存一些数据
        for i in range(5):
            product = ProductData(
                product_id=f"test_get_{i}",
                title=f"测试商品{i}",
                price=100.0 * (i + 1),
                platform="jd",
                category="测试"
            )
            asyncio.run(db.save_product(product))
        
        # 获取商品
        products = asyncio.run(db.get_products(platform="jd", limit=10))
        assert len(products) >= 5


import asyncio
