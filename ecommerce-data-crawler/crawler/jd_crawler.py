# crawler/jd_crawler.py
import logging
import re
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from .api_clients import OfficialAPIClient
from .base_crawler import BaseCrawler, CrawlConfig, ProductData

logger = logging.getLogger(__name__)


class JDCrawler(BaseCrawler):
    """京东爬虫"""

    def __init__(self, config: Optional[CrawlConfig] = None, api_client: Optional[OfficialAPIClient] = None):
        super().__init__(config)
        self.base_search_url = "https://search.jd.com/Search"
        self.api_client = api_client

    def set_api_client(self, api_client: OfficialAPIClient):
        self.api_client = api_client

    def get_platform_name(self) -> str:
        return "jd"

    async def search_products(self, category: str, page: int = 1, count: int = 50) -> List[ProductData]:
        logger.info("Searching JD for category: %s, page: %s, count: %s", category, page, count)

        if self.api_client and self.api_client.is_enabled():
            api_products = await self.api_client.fetch_products(category=category, count=count, page=page)
            if api_products:
                logger.info("JD official API returned %s products", len(api_products))
                return api_products[:count]

        products = await self._search_via_api(category, count)
        if not products:
            logger.warning("API search failed, using simulated data for demonstration")
            products = self._generate_simulated_data(category, count)
        return products[:count]

    async def _search_via_api(self, category: str, count: int) -> List[ProductData]:
        products: List[ProductData] = []
        try:
            params = {"keyword": category, "enc": "utf-8"}
            html = await self._fetch_page(self.base_search_url, params)
            if html:
                products = self._parse_jd_html(html, category)
        except Exception as exc:
            logger.error("JD API search error: %s", exc)
        return products

    def _parse_jd_html(self, html: str, category: str) -> List[ProductData]:
        products: List[ProductData] = []
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")
            for item in soup.select(".gl-item"):
                try:
                    title_elem = item.select_one(".p-name em")
                    price_elem = item.select_one(".p-price strong")
                    sales_elem = item.select_one(".p-statistics")
                    shop_elem = item.select_one(".p-shop")
                    if title_elem and price_elem:
                        products.append(
                            ProductData(
                                product_id="jd_" + self._generate_id(title_elem.get_text()),
                                title=title_elem.get_text().strip(),
                                price=self._parse_price(price_elem.get_text()),
                                sales=sales_elem.get_text().strip() if sales_elem else None,
                                shop_name=shop_elem.get_text().strip() if shop_elem else "京东自营",
                                platform="jd",
                                category=category,
                                scraped_at=datetime.utcnow(),
                            )
                        )
                except Exception as exc:
                    logger.debug("Error parsing product item: %s", exc)
        except ImportError:
            logger.warning("BeautifulSoup not available")
        except Exception as exc:
            logger.error("Error parsing JD HTML: %s", exc)
        return products

    def _generate_simulated_data(self, category: str, count: int) -> List[ProductData]:
        import random

        brands = {
            "手机数码": ["Apple", "华为", "小米", "OPPO", "vivo", "荣耀", "一加", "realme"],
            "笔记本电脑": ["联想", "华为", "苹果", "戴尔", "惠普", "华硕", "小米", "机械革命"],
            "耳机音箱": ["索尼", "BOSE", "苹果", "JBL", "漫步者", "森海塞尔", "铁三角"],
            "智能手表": ["苹果", "华为", "小米", "三星", "荣耀", "OPPO", "Garmin"],
        }
        product_templates = {
            "手机数码": [
                "{} 5G手机 全网通 8GB+256GB",
                "{} 智能手机 拍照手机 轻薄手机",
                "{} 5G游戏手机 高刷屏 大电池",
            ],
            "笔记本电脑": [
                "{} 轻薄笔记本 14英寸 i7处理器 16GB+512GB",
                "{} 游戏本 RTX4060 2.5K屏幕",
                "{} 商务笔记本 超轻薄 长续航",
            ],
            "耳机音箱": [
                "{} 蓝牙耳机 降噪耳机 头戴式",
                "{} 无线音箱 便携音箱 低音炮",
                "{} TWS耳机 主动降噪 长续航",
            ],
            "智能手表": [
                "{} 智能手表 AMOLED屏幕 GPS定位",
                "{} 运动手表 健康监测 防水",
                "{} 儿童电话手表 视频通话",
            ],
        }
        price_ranges = {
            "手机数码": (1000, 10000),
            "笔记本电脑": (3000, 15000),
            "耳机音箱": (50, 3000),
            "智能手表": (200, 5000),
        }
        products: List[ProductData] = []
        brand_list = brands.get(category, ["品牌A", "品牌B", "品牌C"])
        templates = product_templates.get(category, ["{} 商品"])
        price_min, price_max = price_ranges.get(category, (100, 5000))

        for i in range(count):
            brand = random.choice(brand_list)
            template = random.choice(templates)
            title = template.replace("{}", brand, 1)
            price = round(random.uniform(price_min, price_max), 2)
            sales_num = random.randint(0, 10000)
            products.append(
                ProductData(
                    product_id=f"jd_sim_{category}_{i}_{uuid4().hex}",
                    title=title,
                    price=price,
                    original_price=round(price * random.uniform(1.1, 1.5), 2),
                    sales=str(sales_num) + "+条评价" if sales_num > 0 else "0条评价",
                    shop_name=brand + "京东自营旗舰店",
                    platform="jd",
                    category=category,
                    ratings=round(random.uniform(3.5, 5.0), 1),
                    comments_count=sales_num,
                    is_in_stock=random.random() > 0.1,
                    scraped_at=datetime.utcnow(),
                    raw_data={"source": "simulated"},
                )
            )
        logger.info("Generated %s simulated products for category: %s", len(products), category)
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
