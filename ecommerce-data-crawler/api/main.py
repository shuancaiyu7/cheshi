# api/main.py
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawler import JDCrawler, TmallCrawler
from crawler.api_clients import APIClientConfig, OfficialAPIClient
from storage.database import DatabaseManager
from utils.config import get_api_config, load_config

# 创建FastAPI应用
app = FastAPI(
    title="电商数据爬虫API",
    description="电商数据采集、查询与分析RESTful API",
    version="1.0.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局数据库管理器
db_manager: Optional[DatabaseManager] = None
runtime_config = None


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库"""
    global db_manager, runtime_config
    runtime_config = load_config()
    db_url = "sqlite:///./data/products.db"
    db_manager = DatabaseManager(db_url)
    print("Database initialized successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理资源"""
    global db_manager
    if db_manager:
        db_manager.close()
        print("Database connection closed")


# ==================== Pydantic Models ====================

class ProductResponse(BaseModel):
    """商品响应模型"""
    id: Optional[int] = None
    product_id: str
    title: str
    price: float
    original_price: Optional[float] = None
    sales: Optional[str] = None
    shop_name: Optional[str] = None
    platform: str
    category: str
    ratings: Optional[float] = None
    comments_count: Optional[int] = None
    is_in_stock: bool = True
    scraped_at: Optional[str] = None


class ProductsListResponse(BaseModel):
    """商品列表响应"""
    total: int
    limit: int
    offset: int
    products: List[ProductResponse]


class StatisticsResponse(BaseModel):
    """统计数据响应"""
    total_products: int
    total_platforms: int
    total_categories: int
    platforms: dict
    categories: dict


class CrawlRequest(BaseModel):
    """爬取请求"""
    platform: str = Field(..., description="平台: jd 或 tmall")
    category: str = Field(..., description="商品类目")
    count: int = Field(default=50, ge=1, le=200, description="采集数量")


class CrawlResponse(BaseModel):
    """爬取响应"""
    success: bool
    platform: str
    category: str
    items_collected: int
    message: str


def build_api_client(provider: str) -> OfficialAPIClient:
    if runtime_config is None:
        config = load_config()
    else:
        config = runtime_config
    api_config = get_api_config(config).get(provider, {})
    return OfficialAPIClient(APIClientConfig(provider=provider, **api_config))


# ==================== API路由 ====================

@app.get("/", tags=["Root"])
async def root():
    """根路径 - API信息"""
    return {
        "message": "欢迎使用电商数据爬虫API",
        "version": "1.0.0",
        "endpoints": {
            "products": "/api/products",
            "statistics": "/api/statistics",
            "crawl": "/api/crawl",
            "export": "/api/export"
        }
    }


@app.get("/api/products", response_model=ProductsListResponse, tags=["商品查询"])
async def get_products(
    platform: Optional[str] = Query(None, description="平台过滤: jd, tmall"),
    category: Optional[str] = Query(None, description="类目过滤"),
    min_price: Optional[float] = Query(None, description="最低价格"),
    max_price: Optional[float] = Query(None, description="最高价格"),
    sort_by: str = Query("price", description="排序字段: price, comments_count, ratings"),
    order: str = Query("asc", regex="^(asc|desc)$", description="排序方向"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量")
):
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not initialized")

    try:
        products = await db_manager.get_products(
            platform=platform,
            category=category,
            min_price=min_price,
            max_price=max_price,
            sort_by=sort_by,
            order=order,
            limit=limit,
            offset=offset
        )

        return ProductsListResponse(
            total=len(products),
            limit=limit,
            offset=offset,
            products=[ProductResponse(**p) for p in products]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/products/{product_id}", response_model=ProductResponse, tags=["商品查询"])
async def get_product(product_id: str):
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not initialized")

    product = await db_manager.get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return ProductResponse(**product)


@app.get("/api/statistics", response_model=StatisticsResponse, tags=["统计分析"])
async def get_statistics():
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not initialized")

    try:
        stats = await db_manager.get_statistics()
        return StatisticsResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/crawl", response_model=CrawlResponse, tags=["爬虫控制"])
async def trigger_crawl(request: CrawlRequest):
    if request.platform == "jd":
        crawler = JDCrawler(api_client=build_api_client("jd"))
    elif request.platform == "tmall":
        crawler = TmallCrawler(api_client=build_api_client("tmall"))
    else:
        raise HTTPException(status_code=400, detail="Invalid platform. Use 'jd' or 'tmall'")

    try:
        products = await crawler.crawl_category(request.category, max_items=request.count)

        if db_manager:
            saved_count = await db_manager.save_products(products)
        else:
            saved_count = len(products)

        return CrawlResponse(
            success=True,
            platform=request.platform,
            category=request.category,
            items_collected=saved_count,
            message=f"Successfully collected {saved_count} products"
        )
    except Exception as e:
        return CrawlResponse(
            success=False,
            platform=request.platform,
            category=request.category,
            items_collected=0,
            message=str(e)
        )
    finally:
        await crawler.close()


@app.get("/api/export", tags=["数据导出"])
async def export_data(
    format: str = Query("csv", regex="^(csv|json)$", description="导出格式"),
    platform: Optional[str] = Query(None, description="平台过滤"),
    category: Optional[str] = Query(None, description="类目过滤")
):
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not initialized")

    import io
    import csv

    products = await db_manager.get_products(
        platform=platform,
        category=category,
        limit=10000
    )

    if not products:
        raise HTTPException(status_code=404, detail="No products found")

    if format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=products[0].keys())
        writer.writeheader()
        writer.writerows(products)
        output.seek(0)

        from fastapi.responses import StreamingResponse
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
        )
    else:
        from fastapi.responses import JSONResponse
        return JSONResponse(content={"products": products, "total": len(products)})


@app.get("/api/health", tags=["系统监控"])
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "connected" if db_manager else "disconnected"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
