# crawler/tmall_crawler.py
import logging
import re
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from .api_clients import OfficialAPIClient
from .base_crawler import BaseCrawler, CrawlConfig, ProductData

logger = logging.getLogger(__name__)


class TmallCrawler(BaseCrawler):
    """天猫/淘宝爬虫"""

    def __init__(self, config: Optional[CrawlConfig] = None, api_client: Optional[OfficialAPIClient] = None):
        super().__init__(config)
        self.base_search_url = "https://s.taobao.com/search"
        self.api_client = api_client

    def set_api_client(self, api_client: OfficialAPIClient):
        self.api_client = api_client

    def get_platform_name(self) -> str:
        return "tmall"

    async def search_products(self, category: str, page: int = 1, count: int = 50) -> List[ProductData]:
        logger.info("Searching Tmall for category: %s, page: %s, count: %s", category, page, count)

        if self.api_client and self.api_client.is_enabled():
            api_products = await self.api_client.fetch_products(category=category, count=count, page=page)
            if api_products:
                logger.info("Tmall official API returned %s products", len(api_products))
                return api_products[:count]

        products = await self._search_via_api(category, count)
        if not products:
            logger.warning("API search failed, using simulated data for demonstration")
            products = self._generate_simulated_data(category, count)
        return products[:count]

    async def _search_via_api(self, category: str, count: int) -> List[ProductData]:
        products: List[ProductData] = []
        try:
            params = {"q": category, "ie": "utf8"}
            html = await self._fetch_page(self.base_search_url, params)
            if html:
                products = self._parse_tmall_html(html, category)
        except Exception as exc:
            logger.error("Tmall API search error: %s", exc)
        return products

    def _parse_tmall_html(self, html: str, category: str) -> List[ProductData]:
        products: List[ProductData] = []
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")
            for item in soup.select(".item, .gl-item")[:20]:
                try:
                    title_elem = item.select_one(".title a, .itemTitle")
                    price_elem = item.select_one(".price, .g_price")
                    if title_elem and price_elem:
                        products.append(
                            ProductData(
                                product_id="tmall_" + self._generate_id(title_elem.get_text()),
                                title=title_elem.get_text().strip(),
                                price=self._parse_price(price_elem.get_text()),
                                shop_name="天猫旗舰店",
                                platform="tmall",
                                category=category,
                                scraped_at=datetime.utcnow(),
                            )
                        )
                except Exception as exc:
                    logger.debug("Error parsing tmall product: %s", exc)
        except ImportError:
            logger.warning("BeautifulSoup not available")
        except Exception as exc:
            logger.error("Error parsing Tmall HTML: %s", exc)
        return products

    def _generate_simulated_data(self, category: str, count: int) -> List[ProductData]:
        import random

        brands = {
            "手机数码": ["Apple", "华为", "小米", "三星", "索尼", "OPPO"],
            "笔记本电脑": ["联想", "惠普", "戴尔", "苹果", "华硕", "微软"],
            "耳机音箱": ["索尼", "BOSE", "苹果", "森海塞尔", "JBL", "漫步者"],
            "智能手表": ["苹果", "华为", "小米", "三星", "Garmin", "卡西欧"],
        }
        product_templates = {
            "手机数码": [
                "[天猫旗舰店] {} 5G手机 官方正品 全国联保",
                "{} 智能手机 新品首发 分期免息",
            ],
            "笔记本电脑": [
                "[旗舰店] {} 轻薄笔记本 学生办公 教育优惠",
                "{} 游戏本 高性能 定制版",
            ],
            "耳机音箱": [
                "[官方正品] {} 蓝牙耳机 降噪 长续航",
                "{} 无线音箱 户外便携 防水",
            ],
            "智能手表": [
                "[旗舰店] {} 智能手表 运动健康 防水",
                "{} 手表 血氧监测 NFC支付",
            ],
        }
        price_ranges = {
            "手机数码": (1500, 12000),
            "笔记本电脑": (4000, 20000),
            "耳机音箱": (100, 4000),
            "智能手表": (300, 8000),
        }
        products: List[ProductData] = []
        brand_list = brands.get(category, ["品牌A", "品牌B"])
        templates = product_templates.get(category, ["{} 商品"])
        price_min, price_max = price_ranges.get(category, (100, 5000))

        for i in range(count):
            brand = random.choice(brand_list)
            template = random.choice(templates)
            title = template.replace("{}", brand, 1)
            price = round(random.uniform(price_min, price_max), 2)
            sales_num = random.randint(100, 5000)
            products.append(
                ProductData(
                    product_id=f"tmall_sim_{category}_{i}_{uuid4().hex}",
                    title=title,
                    price=price,
                    original_price=round(price * random.uniform(1.1, 1.6), 2),
                    sales=str(sales_num) + "+人付款",
                    shop_name=brand + "天猫旗舰店",
                    platform="tmall",
                    category=category,
                    ratings=round(random.uniform(4.0, 5.0), 1),
                    comments_count=sales_num,
                    is_in_stock=True,
                    scraped_at=datetime.utcnow(),
                    raw_data={"source": "simulated"},
                )
            )
        logger.info("Generated %s simulated products for Tmall category: %s", len(products), category)
        return products

    def _parse_price(self, price_str: str) -> float:
        cleaned = re.sub(r"[^\d.]", "", price_str)
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def _generate_id(self, text: str) -> str:
        import hashlib

        return hashlib.md5(text.encode()).hexdigest()[:12]
