# main.py
"""
电商数据爬虫 + 可视化看板 - 主程序入口

使用方法:
    python main.py --mode demo              # 运行演示模式
    python main.py --mode crawl-once --platform jd --category 手机数码  # 单次爬取
    python main.py --mode dashboard          # 启动可视化看板
    python main.py --mode api                # 启动API服务
"""

import argparse
import asyncio
import os
import sys
import time

# 修复Windows控制台编码
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(__file__))

from crawler import JDCrawler, TmallCrawler
from crawler.api_clients import APIClientConfig, OfficialAPIClient
from crawler.base_crawler import CrawlConfig
from storage.database import DatabaseManager
from utils.config import get_api_config, get_crawler_config, get_scraping_config, load_config
from utils.logger import setup_logger


def parse_args():
    parser = argparse.ArgumentParser(description='电商数据爬虫 + 可视化看板')
    parser.add_argument('--mode', type=str, choices=['crawl', 'dashboard', 'api', 'crawl-once', 'demo', 'all'], default='demo')
    parser.add_argument('--platform', type=str, choices=['jd', 'tmall'])
    parser.add_argument('--category', type=str)
    parser.add_argument('--count', type=int, default=50)
    parser.add_argument('--debug', action='store_true')
    return parser.parse_args()


def build_crawler_config(config):
    crawler_config = get_crawler_config(config)
    return CrawlConfig(
        max_concurrent=crawler_config['max_concurrent'],
        request_delay=crawler_config['request_delay'],
        max_retries=crawler_config['max_retries'],
    )


def build_api_client(provider: str, config):
    api_config = get_api_config(config).get(provider, {})
    return OfficialAPIClient(APIClientConfig(provider=provider, **api_config))


async def run_crawler_once(platform, category, count=50, config=None):
    print(f"\n{'='*60}")
    print(f"Start crawl: {platform} - {category}")
    print(f"{'='*60}\n")

    start_time = time.time()
    config = config or load_config()
    crawler_config = build_crawler_config(config)
    api_client = build_api_client(platform, config)
    db = DatabaseManager()

    if platform == 'jd':
        crawler = JDCrawler(config=crawler_config, api_client=api_client)
    elif platform == 'tmall':
        crawler = TmallCrawler(config=crawler_config, api_client=api_client)
    else:
        print(f"Error: Unsupported platform '{platform}'")
        db.close()
        return

    try:
        products = await crawler.crawl_category(category, max_items=count)

        if products:
            saved_count = await db.save_products(products)
            print(f"\nOK: Saved {saved_count}/{len(products)} products")
            await db.update_category_stats(platform, category)

            print(f"\nLatest 5 products:")
            print("-" * 60)
            for i, p in enumerate(products[:5]):
                print(f"  {i+1}. {p.title}")
                print(f"     Price: {p.price:,.2f} | Sales: {p.sales} | Shop: {p.shop_name}")
        else:
            print(f"\nWarning: No products collected")

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await crawler.close()
        db.close()

    duration = time.time() - start_time
    print(f"\nTime taken: {duration:.2f}s")


def run_demo():
    print("\n" + "="*60)
    print("E-commerce Data Crawler - Demo Mode")
    print("="*60)
    print("\nNote: This project prefers official APIs when configured.")
    print("If JD/Tmall API settings are missing, it falls back to HTML parsing or simulated data.\n")

    debug_enabled = "--debug" in sys.argv
    setup_logger(level="DEBUG" if debug_enabled else "INFO")
    config = load_config()
    scraping_config = get_scraping_config(config)
    api_configs = get_api_config(config)

    categories = scraping_config['categories']
    platforms = scraping_config['platforms']
    count = scraping_config['items_per_category']

    print(f"Categories: {', '.join(categories)}")
    print(f"Platforms: {', '.join(platforms)}")
    print(f"Items per category: {count}")
    print("API mode:")
    for provider in ('jd', 'tmall'):
        provider_config = api_configs.get(provider, {})
        enabled = provider_config.get('enabled', False) and provider_config.get('base_url')
        print(f"  {provider}: {'enabled' if enabled else 'fallback to HTML/simulated'}")
    print()

    db = DatabaseManager()

    async def crawl_all():
        for platform in platforms:
            for category in categories:
                await run_crawler_once(platform, category, count, config=config)
                print()

    asyncio.run(crawl_all())

    print("\n" + "="*60)
    print("Statistics")
    print("="*60)

    stats = db.get_statistics()
    print(f"  Total products: {stats.get('total_products', 0)}")
    print(f"  Platforms: {stats.get('total_platforms', 0)}")
    print(f"  Categories: {stats.get('total_categories', 0)}")

    print("\n  Per platform:")
    for plat, data in stats.get('platforms', {}).items():
        print(f"    {plat}: {data['count']} items, avg price {data['avg_price']:,.2f}")

    print("\n  Per category:")
    for cat, data in stats.get('categories', {}).items():
        print(f"    {cat}: {data['count']} items, avg price {data['avg_price']:,.2f}")

    db.close()

    print("\n" + "="*60)
    print("Demo complete!")
    print("="*60)
    print("\nNext steps:")
    print("  1. Dashboard: python main.py --mode dashboard")
    print("  2. API server: python main.py --mode api")
    print("  3. Read docs: README.md")


def run_dashboard():
    import subprocess
    print("Starting dashboard...")
    subprocess.run([sys.executable, "-m", "streamlit", "run", "dashboard/app.py"])


def run_api():
    import uvicorn
    print("Starting API server...")
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)


def main():
    args = parse_args()

    if args.mode == 'demo':
        run_demo()
    elif args.mode == 'crawl':
        print("Running scheduled crawler mode...")
    elif args.mode == 'crawl-once':
        if not args.platform or not args.category:
            print("Error: crawl-once needs --platform and --category")
            sys.exit(1)
        config = load_config()
        asyncio.run(run_crawler_once(args.platform, args.category, args.count, config=config))
    elif args.mode == 'dashboard':
        run_dashboard()
    elif args.mode == 'api':
        run_api()
    elif args.mode == 'all':
        run_demo()
    else:
        print(f"Unknown mode: {args.mode}")
        sys.exit(1)


if __name__ == '__main__':
    main()
