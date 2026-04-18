# run_amazon_scraper.py - 完整版（包含所有广告类型）

import time
import random
import json
import re
import logging
from curl_cffi.requests import Session as CurlSession
from datetime import datetime
from typing import List, Dict, Optional, Any
from bs4 import BeautifulSoup
import pandas as pd
from config import AntiScrapingConfig
from headers_manager import HeadersManager

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SimpleRequestExecutor:
    """请求执行器"""
    
    def __init__(self, delay_range=(3, 6), postal_code="90060"):
        self.delay_range = delay_range
        self.postal_code = postal_code
        self.session = CurlSession(impersonate="chrome120")

        # 创建 HeadersManager 实例
        config = AntiScrapingConfig()
        config.RANDOM_USER_AGENT = True
        self.headers_manager = HeadersManager(config)
        
        # ========== 先访问首页建立会话 ==========
        logger.info("正在初始化亚马逊美国会话...")
        init_headers = self.headers_manager.get_headers()  # 使用动态请求头
        try:
            init_response = self.session.get('https://www.amazon.com/', headers=init_headers, timeout=30)
            if init_response.status_code == 200:
                if '$' in init_response.text[:500]:
                    logger.info("✅ 美国站会话建立成功")
                else:
                    logger.warning("⚠️ 首页未检测到美元")
            else:
                logger.warning(f"会话初始化状态码: {init_response.status_code}")
        except Exception as e:
            logger.error(f"会话初始化失败: {e}")
        
        # 设置语言和国家
        self.session.cookies.set('lc-main', 'en_US')
        # 🔑 关键：设置配送地址邮编
        self.session.cookies.set('postalCode', self.postal_code)
        self.session.cookies.set('shippingPostalCode', self.postal_code)
        self.session.cookies.set('delivery-postal-code', self.postal_code)
        
        # 在请求头中添加邮编
        self.session.headers.update({
            'x-amzn-postal-code': self.postal_code,
            'x-amzn-postalcode': self.postal_code,
        })
        
        logger.info(f"初始化请求器，默认邮编: {self.postal_code}")

    def get(self, url):
        """发送GET请求"""
        # time.sleep(random.uniform(*self.delay_range))
        # if '?' in url:
        #     url += f"&postalCode={self.postal_code}"
        # else:
        #     url += f"?postalCode={self.postal_code}"

        delay = random.uniform(*self.delay_range)
        time.sleep(delay)
        
        # 每次请求生成新的动态请求头
        headers = self.headers_manager.get_headers()
        headers['x-amzn-postal-code'] = self.postal_code

        try:
            response = self.session.get(url, timeout=30)
             # 🔍 调试：检查返回的页面类型
            if response and response.status_code == 200:
                # 检查前2000个字符
                preview = response.text[:20000].lower()
                
                if 'cn' in response.url or 'amazon.cn' in response.url:
                    logger.error(f"❌ 被重定向到中国站: {response.url}")
                elif 'cny' in preview or 'CNY' in preview or '¥' in preview:
                    logger.warning("⚠️ 检测到人民币价格，可能还是中国站")
                    # 保存HTML用于分析
                    with open("debug_china_page.html", "w", encoding="utf-8") as f:
                        f.write(response.text)
                    logger.info("已保存到 debug_china_page.html")
                elif '$' in preview and 'cny' not in preview:
                    logger.info("✅ 检测到美元价格，成功获取美国站数据")
                else:
                    logger.info("无法判断货币类型，请检查页面")
                
                return response
            if response.status_code == 503:
                logger.warning(f"访问被拒绝 (503)，可能被亚马逊屏蔽了IP。URL: {url}")
                return None
            return response if response.status_code == 200 else None
        except Exception as e:
            logger.error(f"请求失败: {e}")
            return None
    
    def close(self):
        self.session.close()


class ProductInfo:
    """商品/广告信息数据类"""
    def __init__(self, 
                 data_index,              # 页面中的data-index（原始位置）
                 page,                    # 页码
                 ad_type,                 # "SP", "SB", "SB_Video", "Organic", "Title"
                 ad_rank=None,            # 广告类型内的排名
                 organic_rank=None,       # 自然排名
                 asin=None,
                 title=None,
                 url=None,
                 price_current=None,
                 price_list=None,
                 rating_stars=None,
                 rating_count=None,
                 is_prime=False,
                 image_small=None,
                 image_large=None,
                 brand_name=None,
                 inner_products=None,
                 **kwargs):
        self.data_index = data_index          # 原始data-index
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
        self.inner_products = inner_products if inner_products is not None else []
        self.scraped_at = datetime.now().isoformat()
    
    def to_dict(self):
        return self.__dict__


class AmazonSearchScraper:
    """亚马逊搜索爬虫 - 完整版（包含所有广告,基于data-index分析）"""
    
    def __init__(self, request_executor=None, delay_range=(3, 6), output_dir="./amazon_data", postal_code="90060"):
        self.request_executor = request_executor or SimpleRequestExecutor(delay_range, postal_code)
        self.output_dir = output_dir
        self.postal_code = postal_code
        import os
        os.makedirs(output_dir, exist_ok=True)
    
    def _extract_price(self, item):
        """提取价格信息"""
        result = {'price_current': None, 'price_list': None}
        try:
            price_el = item.select_one('.a-price .a-offscreen')
            if price_el:
                result['price_current'] = price_el.text.strip()
            
            list_price_el = item.select_one('.a-text-strike')
            if list_price_el:
                result['price_list'] = list_price_el.text.strip()
        except:
            pass
        return result
    
    def _extract_rating(self, item):
        """提取评分信息"""
        result = {'rating_stars': None, 'rating_count': None}
        try:
            rating_el = item.select_one('.a-icon-star-mini .a-icon-alt')
            if rating_el:
                rating_text = rating_el.text.strip()
                match = re.search(r'(\d+\.?\d*)', rating_text)
                if match:
                    result['rating_stars'] = float(match.group(1))
            
            count_el = item.select_one('[aria-label*="ratings"]')
            if count_el:
                aria_label = count_el.get('aria-label', '')
                match = re.search(r'([\d,]+)', aria_label)
                if match:
                    result['rating_count'] = int(match.group(1).replace(',', ''))
        except:
            pass
        return result
    
    def _extract_image(self, item):
        """提取图片URL"""
        try:
            img_el = item.select_one('.s-image')
            if img_el:
                small = img_el.get('src')
                large = small.replace('_UL320_', '_SL1500_') if small else None
                return small, large
        except:
            pass
        return None, None
    
    def _is_sponsored(self, item) -> bool:
        """判断是否为SP广告"""
        return bool(item.select_one('.puis-sponsored-label-text')) or \
               bool(item.select_one('[aria-label*="Sponsored"]'))
    
    def _has_video(self, item) -> bool:
        """判断是否包含视频"""
        return bool(item.select_one('video'))
    
    def _is_sb_ad(self, item) -> bool:
        """判断是否为SB品牌广告（data-asin为空，有AdHolder类）"""
        asin = item.get('data-asin', '')
        classes = ' '.join(item.get('class', []))
        return not asin and 'AdHolder' in classes and not self._has_video(item)
    
    def _is_title_row(self, item) -> bool:
        """判断是否为标题行（如 "Results"）"""
        asin = item.get('data-asin', '')
        classes = ' '.join(item.get('class', []))
        # 标题行特征：data-asin为空，包含s-widget，但不包含AdHolder
        return not asin and 's-widget' in classes and 'AdHolder' not in classes
    
    def parse_sp_product(self, item, data_index, page, ad_rank=None, organic_rank=None):
        """解析SP广告或自然商品"""
        try:
            asin = item.get('data-asin')
            if not asin:
                return None
            
            is_sponsored = self._is_sponsored(item)
            ad_type = "SP" if is_sponsored else "Organic"
            
            # 标题
            title_el = item.select_one('h2 span')
            title = title_el.text.strip() if title_el else "N/A"
            
            # 链接
            link_el = item.select_one('h2 a')
            url = None
            if link_el and link_el.get('href'):
                href = link_el.get('href')
                url = f"https://www.amazon.com{href}" if href.startswith('/') else href
            
            # 图片
            img_small, img_large = self._extract_image(item)
            
            # 价格和评分
            price_info = self._extract_price(item)
            rating_info = self._extract_rating(item)
            
            # Prime标识
            is_prime = bool(item.select_one('.a-icon-prime'))
            
            return ProductInfo(
                data_index=data_index,
                page=page,
                ad_type=ad_type,
                ad_rank=ad_rank,
                organic_rank=organic_rank,
                asin=asin,
                title=title,
                url=url or "N/A",
                price_current=price_info['price_current'],
                price_list=price_info['price_list'],
                rating_stars=rating_info['rating_stars'],
                rating_count=rating_info['rating_count'],
                is_prime=is_prime,
                image_small=img_small,
                image_large=img_large
            )
        except Exception as e:
            logger.error(f"解析SP商品失败: {e}")
            return None
    
    def parse_sb_ad(self, item, data_index, page, ad_rank):
        """解析SB品牌广告"""
        try:
            # 品牌名称
            title = "N/A"
            title_el = item.select_one('[data-elementid="sb-headline"] span, ._c2Itd_headline_3CcZ9')
            if title_el:
                title = title_el.text.strip()
            
            # 品牌链接
            url = None
            link_el = item.select_one('._c2Itd_link_pJ4S_, a[href*="stores/page"]')
            if link_el and link_el.get('href'):
                href = link_el.get('href')
                url = f"https://www.amazon.com{href}" if href.startswith('/') else href
            
            # 品牌Logo
            brand_logo = None
            logo_el = item.select_one('._c2Itd_logo_1BwG8 img')
            if logo_el:
                brand_logo = logo_el.get('src')
            
            # 内部商品列表
            inner_products = []
            ad_items = item.select('[data-asin][data-asin!=""]')
            for inner_idx, ad_item in enumerate(ad_items, start=1):
                inner_title_el = ad_item.select_one('.a-size-base-plus, .a-truncate-full')
                inner_title = inner_title_el.text.strip() if inner_title_el else "N/A"
                inner_price_el = ad_item.select_one('.a-price .a-offscreen')
                inner_price = inner_price_el.text.strip() if inner_price_el else None
                
                inner_products.append({
                    'position': inner_idx,
                    'asin': ad_item.get('data-asin'),
                    'title': inner_title,
                    'price': inner_price,
                })
            
            return ProductInfo(
                data_index=data_index,
                page=page,
                ad_type="SB",
                ad_rank=ad_rank,
                title=title,
                url=url or "N/A",
                brand_name=title,
                image_small=brand_logo,
                inner_products=inner_products
            )
        except Exception as e:
            logger.error(f"解析SB广告失败: {e}")
            return None
    
    def parse_sb_video_ad(self, item, data_index, page, ad_rank):
        """解析SB视频广告"""
        try:
            # 标题
            title = "N/A"
            title_el = item.select_one('[data-elementid="sb-headline"], ._c2Itd_headline_3CcZ9')
            if title_el:
                title = title_el.text.strip()
            
            # 链接
            url = None
            link_el = item.select_one('._c2Itd_link_pJ4S_')
            if link_el and link_el.get('href'):
                href = link_el.get('href')
                url = f"https://www.amazon.com{href}" if href.startswith('/') else href
            
            # 内部商品
            inner_products = []
            ad_items = item.select('[data-asin][data-asin!=""]')
            for inner_idx, ad_item in enumerate(ad_items, start=1):
                inner_title_el = ad_item.select_one('.a-size-base-plus, .a-truncate-full')
                inner_title = inner_title_el.text.strip() if inner_title_el else "N/A"
                
                inner_products.append({
                    'position': inner_idx,
                    'asin': ad_item.get('data-asin'),
                    'title': inner_title,
                })
            
            return ProductInfo(
                data_index=data_index,
                page=page,
                ad_type="SB_Video",
                ad_rank=ad_rank,
                title=title,
                url=url or "N/A",
                inner_products=inner_products
            )
        except Exception as e:
            logger.error(f"解析SB视频广告失败: {e}")
            return None
    
    def parse_title_row(self, item, data_index, page):
        """解析标题行（如 "Results"）"""
        try:
            title_text = item.get_text(strip=True)
            return ProductInfo(
                data_index=data_index,
                page=page,
                ad_type="Title",
                title=title_text[:100] if title_text else "Unknown Title"
            )
        except Exception as e:
            logger.error(f"解析标题行失败: {e}")
            return None
    
    def scrape_search(self, keyword, pages=1):
        """
        爬取搜索结果 - 基于data-index顺序解析，确保不遗漏
        """
        all_items = []  # 保存所有卡片（包括标题行）
        
        # 各类排名计数器
        organic_rank = 1
        sp_rank = 1
        sb_rank = 1
        sb_video_rank = 1
        
        logger.info(f"开始爬取关键词: {keyword}, 页数: {pages}")
        
        for page in range(1, pages + 1):
            url = f"https://www.amazon.com/s?k={keyword}&page={page}"
            logger.info(f"正在访问第 {page} 页: {url}")
            
            response = self.request_executor.get(url)
            if not response:
                logger.error(f"第 {page} 页请求失败")
                continue
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 方法1：通过 data-index 属性选择所有结果元素
            # 选择所有带有 data-index 属性的 div
            all_divs = soup.find_all('div', attrs={'data-index': True})
            
            # 按 data-index 排序
            all_divs_sorted = sorted(all_divs, key=lambda x: int(x.get('data-index', 0)))
            
            logger.info(f"第 {page} 页找到 {len(all_divs_sorted)} 个带data-index的元素")
            
            for div in all_divs_sorted:
                data_index = int(div.get('data-index', -1))
                asin = div.get('data-asin', '')
                has_video = self._has_video(div)
                is_ad_holder = 'AdHolder' in ' '.join(div.get('class', []))
                is_sponsored = self._is_sponsored(div)
                is_title = self._is_title_row(div)
                
                # 调试：打印前20个元素
                if data_index < 20:
                    logger.debug(f"data-index={data_index}, asin={asin[:15] if asin else 'None'}, "
                               f"AdHolder={is_ad_holder}, video={has_video}, sponsored={is_sponsored}")
                
                product = None
                
                # ========== 分类解析 ==========
                # 1. 标题行（如 "Results"）
                if is_title:
                    product = self.parse_title_row(div, data_index, page)
                    if product:
                        all_items.append(product)
                        logger.debug(f"[标题] data-index={data_index}: {product.title}")
                
                # 2. SB品牌广告（data-asin为空，有AdHolder，无视频）
                elif not asin and is_ad_holder and not has_video:
                    product = self.parse_sb_ad(div, data_index, page, sb_rank)
                    if product:
                        all_items.append(product)
                        logger.info(f"[SB广告] data-index={data_index} SB排名:{sb_rank} - {product.title[:40]}")
                        sb_rank += 1
                
                # 3. SB视频广告（包含video标签）
                elif has_video:
                    product = self.parse_sb_video_ad(div, data_index, page, sb_video_rank)
                    if product:
                        all_items.append(product)
                        logger.info(f"[SB视频] data-index={data_index} 视频排名:{sb_video_rank} - {product.title[:40]}")
                        sb_video_rank += 1
                
                # 4. 有ASIN的卡片（SP广告 或 自然商品）
                elif asin:
                    if is_sponsored:
                        product = self.parse_sp_product(div, data_index, page, ad_rank=sp_rank)
                        if product:
                            all_items.append(product)
                            logger.info(f"[SP广告] data-index={data_index} SP排名:{sp_rank} - {product.title[:40]}")
                            sp_rank += 1
                    else:
                        product = self.parse_sp_product(div, data_index, page, organic_rank=organic_rank)
                        if product:
                            all_items.append(product)
                            logger.info(f"[自然] data-index={data_index} 自然排名:{organic_rank} - {product.title[:40]}")
                            organic_rank += 1
                
                # 5. 其他（可能包含有用信息）
                else:
                    logger.debug(f"[跳过] data-index={data_index}, class={div.get('class', [])[:2]}")
            
            # 翻页间隔
            if page < pages:
                time.sleep(random.uniform(8, 12))
        
        logger.info(f"爬取完成，共获取 {len(all_items)} 个元素")
        logger.info(f"  - 自然商品: {organic_rank - 1} 个")
        logger.info(f"  - SP广告: {sp_rank - 1} 个")
        logger.info(f"  - SB广告: {sb_rank - 1} 个")
        logger.info(f"  - SB视频: {sb_video_rank - 1} 个")
        logger.info(f"  - 标题行: {len([i for i in all_items if i.ad_type == 'Title'])} 个")
        
        return all_items
    
    def save_results(self, items, keyword):
        """保存结果"""
        if not items:
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"{self.output_dir}/{keyword}_{timestamp}"
        
        # 转字典
        items_dict = []
        for item in items:
            d = item.to_dict()
            if 'inner_products' in d and d['inner_products']:
                d['inner_products_count'] = len(d['inner_products'])
            items_dict.append(d)
        
        # 保存JSON
        with open(f"{base_filename}.json", 'w', encoding='utf-8') as f:
            json.dump(items_dict, f, ensure_ascii=False, indent=2)
        
        # 保存CSV（排除inner_products）
        df = pd.DataFrame(items_dict)
        if 'inner_products' in df.columns:
            df = df.drop(columns=['inner_products'])
        df.to_csv(f"{base_filename}.csv", index=False, encoding='utf-8-sig')
        
        # 生成报告
        self._generate_report(items, keyword, timestamp)
        
        logger.info(f"数据已保存到: {base_filename}.json")
        return base_filename
    
    def _generate_report(self, items, keyword, timestamp):
        """生成统计报告"""
        report_path = f"{self.output_dir}/{keyword}_{timestamp}_report.txt"
        
        stats = {
            'total': len(items),
            'organic': len([i for i in items if i.ad_type == 'Organic']),
            'sp': len([i for i in items if i.ad_type == 'SP']),
            'sb': len([i for i in items if i.ad_type == 'SB']),
            'sb_video': len([i for i in items if i.ad_type == 'SB_Video']),
            'title': len([i for i in items if i.ad_type == 'Title']),
        }
        
        total_inner = sum(len(i.inner_products) for i in items if i.inner_products)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write(f"亚马逊搜索爬虫报告\n")
            f.write(f"关键词: {keyword}\n")
            f.write(f"邮编: {self.postal_code}\n")
            f.write(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")
            f.write("【统计摘要】\n")
            f.write(f"总元素数: {stats['total']}\n")
            f.write(f"  - 自然商品: {stats['organic']}\n")
            f.write(f"  - SP广告: {stats['sp']}\n")
            f.write(f"  - SB广告: {stats['sb']}\n")
            f.write(f"  - SB视频: {stats['sb_video']}\n")
            f.write(f"  - 标题行: {stats['title']}\n")
            f.write(f"SB广告内包含商品数: {total_inner}\n")


def main():
    print("=" * 60)
    print("亚马逊商品爬虫 - 基于data-index完整版")
    print("=" * 60)
    
    keyword = input("请输入搜索关键词 (默认: towels): ").strip() or "towels"
    pages = int(input("请输入需要爬取的总页数 (默认: 1): ").strip() or "1")
    postal_code = input("请输入配送邮编 (默认: 90060): ").strip() or "90060"
    
    scraper = AmazonSearchScraper(
        delay_range=(3, 6),
        output_dir="./amazon_data",
        postal_code=postal_code
    )
    try:
        items = scraper.scrape_search(keyword, pages)
        
        if items:
            filepath = scraper.save_results(items, keyword)
            print(f"\n✅ 爬取成功！")
            print(f"📊 共获取 {len(items)} 个元素")
            print(f"   - 自然商品: {len([i for i in items if i.ad_type == 'Organic'])}")
            print(f"   - SP广告: {len([i for i in items if i.ad_type == 'SP'])}")
            print(f"   - SB广告: {len([i for i in items if i.ad_type == 'SB'])}")
            print(f"   - SB视频: {len([i for i in items if i.ad_type == 'SB_Video'])}")
            print(f"📁 数据已保存到: {filepath}")
        else:
            print("\n❌ 未获取到任何数据")
            
    except Exception as e:
        print(f"\n❌ 爬取出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()