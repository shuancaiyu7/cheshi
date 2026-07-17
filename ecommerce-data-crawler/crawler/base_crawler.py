# crawler/base_crawler.py
import asyncio
import random
import time
import json
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field, asdict
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class CrawlConfig:
    """爬虫配置"""
    max_concurrent: int = 3
    request_delay: float = 2.0
    max_retries: int = 3
    timeout: int = 30
    user_agents: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.user_agents:
            self.user_agents = self._get_default_user_agents()

    def _get_default_user_agents(self) -> List[str]:
        """获取默认User-Agent列表"""
        return [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
        ]

    def get_random_user_agent(self) -> str:
        """获取随机User-Agent"""
        return random.choice(self.user_agents)


@dataclass
class ProductData:
    """商品数据结构"""
    product_id: str
    title: str
    price: float
    original_price: Optional[float] = None
    sales: Optional[str] = None
    shop_name: Optional[str] = None
    platform: str = ""
    category: str = ""
    image_url: Optional[str] = None
    product_url: Optional[str] = None
    ratings: Optional[float] = None
    comments_count: Optional[int] = None
    is_in_stock: bool = True
    scraped_at: Optional[datetime] = None
    raw_data: Optional[Dict] = None

    def __post_init__(self):
        if self.scraped_at is None:
            self.scraped_at = datetime.utcnow()
        if self.raw_data is None:
            self.raw_data = {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        if self.scraped_at:
            data['scraped_at'] = self.scraped_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'ProductData':
        """从字典创建"""
        if 'scraped_at' in data and data['scraped_at']:
            data['scraped_at'] = datetime.fromisoformat(data['scraped_at'])
        return cls(**data)


class BaseCrawler(ABC):
    """爬虫基类"""

    def __init__(self, config: Optional[CrawlConfig] = None):
        self.config = config or CrawlConfig()
        self.session = None
        self._init_session()

    def _init_session(self):
        """初始化HTTP会话"""
        import aiohttp
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        self.session = aiohttp.ClientSession(timeout=timeout)

    async def close(self):
        """关闭会话"""
        if self.session and not self.session.closed:
            await self.session.close()

    @abstractmethod
    async def search_products(self, category: str, page: int = 1, count: int = 50) -> List[ProductData]:
        """搜索商品 - 子类必须实现"""
        pass

    @abstractmethod
    def get_platform_name(self) -> str:
        """获取平台名称 - 子类必须实现"""
        pass

    async def _fetch_page(self, url: str, params: Optional[Dict] = None, retries: int = 0) -> Optional[str]:
        """
        获取页面内容
        
        Args:
            url: 请求URL
            params: 请求参数
            retries: 重试次数
            
        Returns:
            页面HTML内容
        """
        headers = {
            'User-Agent': self.config.get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }

        try:
            logger.debug(f"Fetching: {url}")
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    html = await response.text(encoding='utf-8')
                    await asyncio.sleep(self.config.request_delay)
                    return html
                elif response.status == 429:
                    # 频率限制，等待后重试
                    wait_time = self.config.request_delay * (retries + 1) * 2
                    logger.warning(f"Rate limited. Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                    if retries < self.config.max_retries:
                        return await self._fetch_page(url, params, retries + 1)
                    else:
                        logger.error(f"Max retries reached for {url}")
                        return None
                else:
                    logger.warning(f"HTTP {response.status} for {url}")
                    if retries < self.config.max_retries:
                        await asyncio.sleep(self.config.request_delay)
                        return await self._fetch_page(url, params, retries + 1)
                    return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            if retries < self.config.max_retries:
                await asyncio.sleep(self.config.request_delay)
                return await self._fetch_page(url, params, retries + 1)
            return None

    async def _fetch_json(self, url: str, params: Optional[Dict] = None, retries: int = 0) -> Optional[Dict]:
        """获取JSON数据"""
        headers = {
            'User-Agent': self.config.get_random_user_agent(),
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }

        try:
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    await asyncio.sleep(self.config.request_delay)
                    return data
                elif response.status == 429:
                    wait_time = self.config.request_delay * (retries + 1) * 2
                    logger.warning(f"Rate limited. Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                    if retries < self.config.max_retries:
                        return await self._fetch_json(url, params, retries + 1)
                    return None
                else:
                    logger.warning(f"HTTP {response.status} for {url}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching JSON from {url}: {e}")
            if retries < self.config.max_retries:
                await asyncio.sleep(self.config.request_delay)
                return await self._fetch_json(url, params, retries + 1)
            return None

    async def crawl_category(self, category: str, max_items: int = 50) -> List[ProductData]:
        """
        爬取指定类目的商品
        
        Args:
            category: 商品类目
            max_items: 最大采集数量
            
        Returns:
            商品列表
        """
        logger.info(f"Starting crawl for category '{category}' on {self.get_platform_name()}")
        start_time = time.time()
        
        try:
            products = await self.search_products(category, count=max_items)
            duration = time.time() - start_time
            
            logger.info(f"Crawled {len(products)} products from '{category}' in {duration:.2f}s")
            return products
        except Exception as e:
            logger.error(f"Error crawling category '{category}': {e}")
            return []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
