# run_amazon_scraper.py - 完整集成反爬模块版

import time
import random
import json
import re
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from bs4 import BeautifulSoup
import pandas as pd

# ✅ 导入你的完整反爬模块
from anti_scraping import (
    AntiScrapingConfig, 
    SafeMode,
    RequestExecutor,
    HeadersManager,
    ProxyManager,
    CaptchaDetector,
    CaptchaSolver
)

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AmazonRequestExecutor:
    """
    专门为亚马逊定制的请求执行器
    集成所有反爬模块
    """
    
    def __init__(self, postal_code="10001", use_proxy=False, delay_range=(5, 10)):
        self.postal_code = postal_code
        
        # 创建配置
        self.config = SafeMode() if use_proxy else AntiScrapingConfig()
        self.config.MIN_DELAY = delay_range[0]
        self.config.MAX_DELAY = delay_range[1]
        self.config.USE_PROXY = use_proxy
        
        # ✅ 使用完整的 RequestExecutor（集成了所有模块）
        self.executor = RequestExecutor(self.config)
        
        # ✅ 额外获取 HeadersManager 用于动态请求头
        self.headers_manager = self.executor.headers_manager
        
        # 设置亚马逊特定的请求头
        self._setup_amazon_headers()
        
        # 初始化亚马逊会话（先访问首页）
        self._init_amazon_session()
        
        logger.info(f"亚马逊请求器初始化完成，邮编: {postal_code}")
    
    def _setup_amazon_headers(self):
        """设置亚马逊特定的请求头"""
        # 获取动态生成的请求头并添加亚马逊特定字段
        headers = self.headers_manager.get_headers()
        headers.update({
            'x-amzn-postal-code': self.postal_code,
            'x-amzn-postalcode': self.postal_code,
        })
        
        # 注意：RequestExecutor 每次请求都会重新生成 headers
        # 所以这里的设置会通过 get 方法传递
    
    def _init_amazon_session(self):
        """初始化亚马逊会话 - 关键步骤！"""
        logger.info("正在初始化亚马逊美国会话...")
        
        try:
            # 使用 executor 的 session 直接访问首页
            response = self.executor.session.get(
                'https://www.amazon.com/',
                headers=self.headers_manager.get_headers(),
                timeout=30
            )
            
            if response.status_code == 200:
                # 检查是否是美国站
                if 'cny' not in response.text[:1000].lower():
                    logger.info("✅ 亚马逊美国会话初始化成功")
                else:
                    logger.warning("⚠️ 首页显示人民币，可能需要检查VPN")
            else:
                logger.warning(f"会话初始化状态码: {response.status_code}")
                
        except Exception as e:
            logger.error(f"会话初始化失败: {e}")
        
        # 设置邮编 Cookie
        self.executor.session.cookies.set('postalCode', self.postal_code, domain='.amazon.com')
        self.executor.session.cookies.set('shippingPostalCode', self.postal_code, domain='.amazon.com')
        self.executor.session.cookies.set('lc-main', 'en_US', domain='.amazon.com')
    
    def get(self, url):
        """发送GET请求 - 使用完整的反爬模块"""
        # 生成动态请求头
        headers = self.headers_manager.get_headers()
        headers['x-amzn-postal-code'] = self.postal_code
        
        # 使用 executor 的 get 方法（自动处理限流、重试、代理、验证码）
        response = self.executor.get(url, headers=headers)
        
        # 调试检查
        if response and response.status_code == 200:
            preview = response.text[:2000].lower()
            if 'cny' in preview or '￥' in preview:
                logger.warning("⚠️ 检测到人民币价格")
            elif '$' in preview:
                logger.info("✅ 检测到美元价格")
        
        return response
    
    def close(self):
        self.executor.close()


class ProductInfo:
    """商品/广告信息数据类"""
    def __init__(self, 
                 data_index, page, ad_type, ad_rank=None, organic_rank=None,
                 asin=None, title=None, url=None, price_current=None, price_list=None,
                 rating_stars=None, rating_count=None, is_prime=False,
                 image_small=None, image_large=None, brand_name=None, inner_products=None):
        self.data_index = data_index
        self.page = page
        self.ad_type = ad_type
        self.ad_rank = ad_rank
        self.organic_rank = organic_rank
        self.asin = asin
        self.title = title
        self.url = url
        self.price_current = price_current
        self.price_list = price_list
        self.rating_stars = rating_stars
        self.rating_count = rating_count
        self.is_prime = is_prime
        self.image_small = image_small
        self.image_large = image_large
        self.brand_name = brand_name
        self.inner_products = inner_products if inner_products else []
        self.scraped_at = datetime.now().isoformat()
    
    def to_dict(self):
        return self.__dict__


class AmazonSearchScraper:
    """亚马逊搜索爬虫 - 完整集成反爬模块"""
    
    def __init__(self, postal_code="10001", use_proxy=False, delay_range=(5, 10), output_dir="./amazon_data"):
        self.request_executor = AmazonRequestExecutor(postal_code, use_proxy, delay_range)
        self.output_dir = output_dir
        self.postal_code = postal_code
        
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        # ✅ 可以使用验证码检测器
        self.captcha_detector = CaptchaDetector()
    
    def scrape_search(self, keyword, pages=1):
        """爬取搜索结果"""
        all_items = []
        organic_rank, sp_rank, sb_rank, sb_video_rank = 1, 1, 1, 1
        
        logger.info(f"开始爬取关键词: {keyword}, 页数: {pages}")
        
        for page in range(1, pages + 1):
            url = f"https://www.amazon.com/s?k={keyword}&page={page}"
            logger.info(f"正在访问第 {page} 页")
            
            response = self.request_executor.get(url)
            if not response:
                logger.error(f"第 {page} 页请求失败")
                continue
            
            # ✅ 检测验证码
            if self.captcha_detector.has_captcha(response.text):
                logger.error("检测到验证码页面，需要处理")
                continue
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 通过 data-index 获取所有结果
            all_divs = soup.find_all('div', attrs={'data-index': True})
            all_divs_sorted = sorted(all_divs, key=lambda x: int(x.get('data-index', 0)))
            
            logger.info(f"第 {page} 页找到 {len(all_divs_sorted)} 个元素")
            
            for div in all_divs_sorted:
                data_index = int(div.get('data-index', -1))
                asin = div.get('data-asin', '')
                has_video = bool(div.select_one('video'))
                is_ad_holder = 'AdHolder' in ' '.join(div.get('class', []))
                is_sponsored = bool(div.select_one('.puis-sponsored-label-text'))
                
                # 解析逻辑（保持你原有的）
                # ... 这里放你原有的解析代码 ...
                
            # 翻页间隔
            if page < pages:
                time.sleep(random.uniform(8, 12))
        
        return all_items
    
    def close(self):
        self.request_executor.close()


def main():
    print("=" * 60)
    print("亚马逊商品爬虫 - 完整集成反爬模块版")
    print("=" * 60)
    
    keyword = input("请输入搜索关键词 (默认: towels): ").strip() or "towels"
    pages = int(input("请输入需要爬取的总页数 (默认: 1): ").strip() or "1")
    postal_code = input("请输入配送邮编 (默认: 10001): ").strip() or "10001"
    use_proxy = input("是否使用代理? (y/n, 默认: n): ").strip().lower() == 'y'
    
    scraper = AmazonSearchScraper(
        postal_code=postal_code,
        use_proxy=use_proxy,
        delay_range=(5, 10),
        output_dir="./amazon_data"
    )
    
    try:
        items = scraper.scrape_search(keyword, pages)
        print(f"\n✅ 爬取完成，获取 {len(items)} 个元素")
    except Exception as e:
        print(f"\n❌ 爬取出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        scraper.close()


if __name__ == "__main__":
    main()