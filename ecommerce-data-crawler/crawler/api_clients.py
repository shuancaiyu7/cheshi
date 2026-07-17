import base64
import hashlib
import hmac
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import quote

import aiohttp

from .base_crawler import ProductData

logger = logging.getLogger(__name__)


@dataclass
class APIClientConfig:
    provider: str
    enabled: bool = False
    base_url: str = ""
    app_key: str = ""
    app_secret: str = ""
    access_token: str = ""
    timeout: int = 30
    method: str = ""
    version: str = "2.0"
    sign_method: str = "md5"
    response_path: str = ""
    data_path: str = ""
    extra_params: Dict[str, Any] = field(default_factory=dict)


class OfficialAPIClient:
    def __init__(self, config: APIClientConfig):
        self.config = config

    def is_enabled(self) -> bool:
        return bool(self.config.enabled and self.config.base_url and self.config.app_key and self.config.app_secret)

    async def fetch_products(self, category: str, count: int = 50, page: int = 1) -> List[ProductData]:
        provider = self.config.provider.lower()
        if provider == "jd":
            return await self._fetch_jd(category, count, page)
        if provider in {"tmall", "taobao"}:
            return await self._fetch_taobao(category, count, page)
        logger.warning("Unsupported provider for official API: %s", provider)
        return []

    async def _fetch_jd(self, category: str, count: int, page: int) -> List[ProductData]:
        request = self._build_jd_request(category=category, count=count, page=page)
        data = await self._request_json(request["params"], request["headers"])
        if not data:
            return []
        items = self._extract_items(data, self.config.response_path)
        return [self._map_jd_item(item, category) for item in items[:count]]

    async def _fetch_taobao(self, category: str, count: int, page: int) -> List[ProductData]:
        request = self._build_taobao_request(category=category, count=count, page=page)
        data = await self._request_json(request["params"], request["headers"])
        if not data:
            return []
        items = self._extract_items(data, self.config.response_path)
        return [self._map_taobao_item(item, category) for item in items[:count]]

    def _build_jd_request(self, category: str, count: int, page: int) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "app_key": self.config.app_key,
            "method": self.config.method or "jd.union.open.goods.jsearch",
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "format": "json",
            "v": self.config.version,
            "sign_method": self.config.sign_method,
            "page_no": page,
            "page_size": count,
            "keyword": category,
        }
        if self.config.access_token:
            params["access_token"] = self.config.access_token
        params.update(self.config.extra_params)
        params["sign"] = self._jd_sign(params)
        return {"params": params, "headers": self._build_headers()}

    def _build_taobao_request(self, category: str, count: int, page: int) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "app_key": self.config.app_key,
            "method": self.config.method or "taobao.tbk.dg.material.optional",
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "format": "json",
            "v": self.config.version,
            "sign_method": self.config.sign_method,
            "page_no": page,
            "page_size": count,
            "q": category,
            "adzone_id": self.config.extra_params.get("adzone_id", ""),
        }
        if self.config.access_token:
            params["session"] = self.config.access_token
        params.update({k: v for k, v in self.config.extra_params.items() if k not in params})
        params["sign"] = self._taobao_sign(params)
        return {"params": params, "headers": self._build_headers()}

    async def _request_json(self, params: Dict[str, Any], headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
        try:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as client:
                async with client.get(self.config.base_url, params=params, headers=headers) as response:
                    response.raise_for_status()
                    text = await response.text()
                    try:
                        return json.loads(text)
                    except json.JSONDecodeError:
                        return await response.json()
        except Exception as exc:
            logger.error("Official API request failed for %s: %s", self.config.provider, exc)
            return None

    def _build_headers(self) -> Dict[str, str]:
        return {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        }

    def _extract_items(self, payload: Dict[str, Any], response_path: str = "") -> List[Dict[str, Any]]:
        if response_path:
            value = self._get_by_path(payload, response_path)
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                for key in ("items", "list", "result", "data"):
                    nested = value.get(key)
                    if isinstance(nested, list):
                        return nested

        for key in ("items", "data", "result", "list", "results", "model"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                for nested_key in ("items", "list", "result", "data", "results", "item_list", "goods_list"):
                    nested = value.get(nested_key)
                    if isinstance(nested, list):
                        return nested
        return []

    def _get_by_path(self, payload: Dict[str, Any], path: str) -> Any:
        current: Any = payload
        for part in path.split("."):
            if not isinstance(current, dict):
                return None
            current = current.get(part)
        return current

    def _map_jd_item(self, item: Dict[str, Any], category: str) -> ProductData:
        title = str(item.get("title") or item.get("skuName") or item.get("sku_name") or item.get("name") or "京东商品")
        price = self._to_float(item.get("price") or item.get("jdPrice") or item.get("salePrice") or item.get("unitPrice"))
        original_price = self._to_float(item.get("originalPrice") or item.get("marketPrice") or item.get("priceInfo"))
        sales = item.get("sales") or item.get("saleCount") or item.get("comments") or item.get("inOrderCount30Days")
        shop_name = item.get("shopName") or item.get("sellerName") or item.get("shop_name") or "京东"
        return ProductData(
            product_id=self._build_id("jd", title, item.get("skuId") or item.get("id") or item.get("goodsId")),
            title=title,
            price=price or 0.0,
            original_price=original_price,
            sales=str(sales) if sales is not None else None,
            shop_name=shop_name,
            platform="jd",
            category=category,
            image_url=item.get("imageUrl") or item.get("img") or item.get("image") or item.get("image_info"),
            product_url=item.get("productUrl") or item.get("url") or item.get("materialUrl"),
            ratings=self._to_float(item.get("rating") or item.get("score") or item.get("goodCommentsShare")),
            comments_count=self._to_int(item.get("commentsCount") or item.get("commentCount") or item.get("commentNum")),
            is_in_stock=bool(item.get("inStock", item.get("isStock", True))),
            scraped_at=datetime.utcnow(),
            raw_data=item,
        )

    def _map_taobao_item(self, item: Dict[str, Any], category: str) -> ProductData:
        title = str(item.get("title") or item.get("item_title") or item.get("name") or "淘宝商品")
        price = self._to_float(item.get("zk_final_price") or item.get("price") or item.get("sale_price") or item.get("coupon_price"))
        original_price = self._to_float(item.get("reserve_price") or item.get("original_price") or item.get("raw_price"))
        sales = item.get("volume") or item.get("sales") or item.get("sale_count") or item.get("comment_count")
        shop_name = item.get("shopTitle") or item.get("nick") or item.get("shop_name") or item.get("sellerNick") or "淘宝/天猫"
        return ProductData(
            product_id=self._build_id("taobao", title, item.get("item_id") or item.get("auctionId") or item.get("id")),
            title=title,
            price=price or 0.0,
            original_price=original_price,
            sales=str(sales) if sales is not None else None,
            shop_name=shop_name,
            platform="tmall",
            category=category,
            image_url=item.get("pict_url") or item.get("image_url") or item.get("pic_url") or item.get("pic"),
            product_url=item.get("item_url") or item.get("url") or item.get("detail_url"),
            ratings=self._to_float(item.get("shop_score") or item.get("rating")),
            comments_count=self._to_int(item.get("comment_count") or item.get("comments_count")),
            is_in_stock=bool(item.get("in_stock", item.get("quantity", 1))),
            scraped_at=datetime.utcnow(),
            raw_data=item,
        )

    def _jd_sign(self, params: Dict[str, Any]) -> str:
        normalized = {k: v for k, v in params.items() if k != "sign" and v is not None and v != ""}
        sorted_items = sorted(normalized.items(), key=lambda item: item[0])
        base = self.config.app_secret + "".join(f"{key}{self._stringify(value)}" for key, value in sorted_items) + self.config.app_secret
        return hashlib.md5(base.encode("utf-8")).hexdigest().upper()

    def _taobao_sign(self, params: Dict[str, Any]) -> str:
        normalized = {k: v for k, v in params.items() if k != "sign" and v is not None and v != ""}
        sorted_items = sorted(normalized.items(), key=lambda item: item[0])
        base = self.config.app_secret + "".join(f"{key}{self._stringify(value)}" for key, value in sorted_items) + self.config.app_secret
        return hashlib.md5(base.encode("utf-8")).hexdigest().upper()

    def _build_id(self, prefix: str, title: str, suffix: Any) -> str:
        basis = f"{prefix}:{title}:{suffix}"
        return hashlib.md5(basis.encode("utf-8")).hexdigest()[:16]

    def _stringify(self, value: Any) -> str:
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        return str(value)

    def _to_float(self, value: Any) -> Optional[float]:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _to_int(self, value: Any) -> Optional[int]:
        if value is None or value == "":
            return None
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None
