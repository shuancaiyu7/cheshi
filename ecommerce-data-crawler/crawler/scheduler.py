# crawler/scheduler.py
import asyncio
import logging
import time
from typing import List, Optional
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


class CrawlScheduler:
    """爬虫任务调度器 - 延迟导入避免循环依赖"""

    def __init__(self, db_manager=None, categories: List[str] = None, 
                 platforms: List[str] = None, interval_hours: int = 6):
        self.db = db_manager
        self.categories = categories or []
        self.platforms = platforms or ['jd', 'tmall']
        self.interval_hours = interval_hours
        self.scheduler = AsyncIOScheduler()
        self.crawlers = {}
        self._running = False

    def register_crawler(self, platform: str, crawler):
        """注册爬虫实例"""
        self.crawlers[platform] = crawler
        logger.info(f"Registered crawler for platform: {platform}")

    def setup_tasks(self):
        """设置定时任务"""
        from .jd_crawler import JDCrawler
        from .tmall_crawler import TmallCrawler
        
        for platform in self.platforms:
            if platform not in self.crawlers:
                self._create_default_crawler(platform)
        
        for platform in self.platforms:
            for category in self.categories:
                self.scheduler.add_job(
                    self._crawl_single,
                    trigger=IntervalTrigger(hours=self.interval_hours),
                    args=[platform, category],
                    id=f"{platform}_{category}",
                    name=f"Crawl {category} from {platform}",
                    replace_existing=True
                )
                logger.info(f"Scheduled task: {platform} - {category} (every {self.interval_hours}h)")

    def _create_default_crawler(self, platform: str):
        """创建默认爬虫"""
        from .jd_crawler import JDCrawler
        from .tmall_crawler import TmallCrawler
        
        if platform == 'jd':
            self.crawlers[platform] = JDCrawler()
        elif platform == 'tmall':
            self.crawlers[platform] = TmallCrawler()
        else:
            logger.warning(f"Unknown platform: {platform}")

    async def _crawl_single(self, platform: str, category: str):
        """执行单个爬取任务"""
        from .jd_crawler import JDCrawler
        from .tmall_crawler import TmallCrawler
        from crawler.base_crawler import BaseCrawler
        
        logger.info(f"=== Starting crawl: {platform} - {category} ===")
        start_time = time.time()
        
        try:
            if platform not in self.crawlers:
                self._create_default_crawler(platform)
            
            crawler = self.crawlers[platform]
            products = await crawler.crawl_category(category, max_items=50)
            
            if products and self.db:
                saved_count = await self.db.save_products(products)
                logger.info(f"Saved {saved_count} products to database")
                await self.db.update_category_stats(platform, category)
            elif not products:
                logger.warning(f"No products found for {platform} - {category}")
                
            duration = time.time() - start_time
            logger.info(f"=== Completed crawl: {platform} - {category} in {duration:.2f}s ===")
            
        except Exception as e:
            logger.error(f"Error crawling {platform} - {category}: {e}", exc_info=True)
            duration = time.time() - start_time
            logger.error(f"=== Failed crawl: {platform} - {category} after {duration:.2f}s ===")

    def start(self, startup_delay: int = 5):
        """启动调度器"""
        self._running = True
        if startup_delay > 0:
            logger.info(f"Starting scheduler with {startup_delay}s delay...")
            self.scheduler.add_job(
                self._delayed_start,
                trigger='date',
                args=[startup_delay],
                id='delayed_start',
                replace_existing=True
            )
        else:
            self.scheduler.start()
            logger.info("Scheduler started immediately")

    async def _delayed_start(self, delay_seconds: int):
        await asyncio.sleep(delay_seconds)
        self.scheduler.start()
        logger.info("Scheduler started!")

    def stop(self):
        self._running = False
        self.scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")

    async def run_once(self, platform: str, category: str):
        await self._crawl_single(platform, category)

    async def run_all(self):
        logger.info("Running all crawl tasks manually...")
        for platform in self.platforms:
            for category in self.categories:
                await self._crawl_single(platform, category)
        logger.info("All crawl tasks completed")
