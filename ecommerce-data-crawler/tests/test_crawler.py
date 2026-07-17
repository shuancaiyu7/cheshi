# tests/test_crawler.py
import pytest
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawler.base_crawler import CrawlConfig, ProductData
from datetime import datetime


class TestCrawlConfig:
    def test_default_config(self):
        config = CrawlConfig()
        assert config.max_concurrent == 3
        assert config.request_delay == 2.0
        assert config.max_retries == 3
        assert len(config.user_agents) > 0

    def test_custom_config(self):
        config = CrawlConfig(max_concurrent=5, request_delay=1.0)
        assert config.max_concurrent == 5
        assert config.request_delay == 1.0

    def test_get_random_user_agent(self):
        config = CrawlConfig()
        ua = config.get_random_user_agent()
        assert isinstance(ua, str)
        assert len(ua) > 10


class TestProductData:
    def test_create_product(self):
        product = ProductData(
            product_id="test_001",
            title="测试商品",
            price=99.99,
            platform="jd",
            category="测试类目"
        )
        assert product.product_id == "test_001"
        assert product.price == 99.99
        assert product.scraped_at is not None

    def test_to_dict(self):
        product = ProductData(
            product_id="test_002",
            title="测试商品2",
            price=199.99,
            platform="tmall"
        )
        data = product.to_dict()
        assert data['product_id'] == "test_002"
        assert data['price'] == 199.99
        assert 'scraped_at' in data

    def test_from_dict(self):
        data = {
            'product_id': 'test_003',
            'title': '测试商品3',
            'price': 299.99,
            'platform': 'jd',
            'scraped_at': datetime.now().isoformat()
        }
        product = ProductData.from_dict(data)
        assert product.product_id == "test_003"
        assert product.price == 299.99


class TestSimulatedData:
    """测试模拟数据生成（不依赖aiohttp事件循环）"""
    
    def test_jd_simulated_data_structure(self):
        """验证京东模拟数据结构正确"""
        import sys
        from crawler.jd_crawler import JDCrawler
        # 直接测试生成逻辑，不初始化aiohttp session
        import random
        random.seed(42)
        products = JDCrawler._generate_simulated_data(JDCrawler.__new__(JDCrawler), "手机数码", 10)
        assert len(products) == 10
        assert all(p.platform == "jd" for p in products)
        assert all(p.category == "手机数码" for p in products)
        assert all(p.price > 0 for p in products)
        assert all(isinstance(p.title, str) and len(p.title) > 0 for p in products)

    def test_tmall_simulated_data_structure(self):
        """验证天猫模拟数据结构正确"""
        import random
        random.seed(42)
        from crawler.tmall_crawler import TmallCrawler
        products = TmallCrawler._generate_simulated_data(TmallCrawler.__new__(TmallCrawler), "笔记本电脑", 10)
        assert len(products) == 10
        assert all(p.platform == "tmall" for p in products)
        assert all(p.price > 0 for p in products)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
