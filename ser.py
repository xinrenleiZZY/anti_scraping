import time
import random
import json
import logging
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
from bs4 import BeautifulSoup
from anti_scraping import make_request

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'amazon_scraper_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AdType(Enum):
    """广告类型枚举"""
    ORGANIC = "Organic"          # 自然排名
    SP = "Sponsored_Products"    # 单商品广告
    SB = "Sponsored_Brands"      # 品牌广告（多商品）
    SB_VIDEO = "Sponsored_Brands_Video"  # 视频广告
    UNKNOWN = "Unknown"


@dataclass
class ProductInfo:
    """商品信息数据类"""
    # 排名信息
    rank: int
    page: int
    ad_type: AdType
    ad_rank: int
    
    # 基础信息
    asin: str
    title: str
    url: str
    
    # 图片信息
    image_small: str
    image_large: str
    
    # 价格信息
    price_current: Optional[str]
    price_list: Optional[str]  # 划线原价
    price_unit: Optional[str]   # 单位价格
    
    # 评分信息
    rating_stars: Optional[float]
    rating_count: Optional[int]
    
    # 商品属性
    spec: Optional[str]          # 规格（如：100 Count）
    variation_options: Optional[str]  # 变体选项
    variation_count: Optional[int]    # 变体数量
    
    # 销售数据
    sales: Optional[str]         # 销量信息
    
    # 优惠信息
    coupon: Optional[str]        # 优惠券
    
    # 配送信息
    delivery_primary: Optional[str]
    delivery_secondary: Optional[str]
    
    # 标识信息
    is_prime: bool
    is_amazon_fulfilled: bool
    is_best_seller: bool
    is_amazon_choice: bool
    
    # 卖家信息
    seller_name: Optional[str]
    
    # 内部商品（SB广告专用）
    inner_products: List[Dict]
    
    # 时间戳
    scraped_at: str


class AmazonSearchScraper:
    """亚马逊搜索爬虫企业级实现"""
    
    def __init__(self, 
                 delay_range: tuple = (2, 5),
                 max_retries: int = 3,
                 output_dir: str = "./output"):
        """
        初始化爬虫
        
        Args:
            delay_range: 请求延迟范围（秒）
            max_retries: 最大重试次数
            output_dir: 输出目录
        """
        self.delay_range = delay_range
        self.max_retries = max_retries
        self.output_dir = output_dir
        
        # 创建输出目录
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        logger.info(f"爬虫初始化完成 - 延迟范围: {delay_range}s, 输出目录: {output_dir}")
    
    def _extract_price(self, item: BeautifulSoup) -> Dict[str, Optional[str]]:
        """提取价格信息"""
        result = {
            'price_current': None,
            'price_list': None,
            'price_unit': None
        }
        
        try:
            # 当前价格
            price_el = item.select_one('.a-price .a-offscreen')
            if price_el:
                result['price_current'] = price_el.text.strip()
            
            # 划线原价
            list_price_el = item.select_one('.a-text-strike')
            if list_price_el:
                result['price_list'] = list_price_el.text.strip()
            
            # 单位价格
            unit_price_el = item.select_one('.a-price[data-a-size="b"] .a-offscreen')
            if unit_price_el:
                result['price_unit'] = unit_price_el.text.strip()
                
        except Exception as e:
            logger.warning(f"提取价格信息失败: {e}")
        
        return result
    
    def _extract_rating(self, item: BeautifulSoup) -> Dict[str, Optional[Any]]:
        """提取评分信息"""
        result = {
            'rating_stars': None,
            'rating_count': None
        }
        
        try:
            # 评分星级
            rating_el = item.select_one('.a-icon-star-mini .a-icon-alt')
            if rating_el:
                rating_text = rating_el.text.strip()
                # 提取数字，如 "4.8 out of 5 stars" -> 4.8
                import re
                match = re.search(r'(\d+\.?\d*)', rating_text)
                if match:
                    result['rating_stars'] = float(match.group(1))
            
            # 评分人数
            rating_count_el = item.select_one('[aria-label*="rating"]')
            if rating_count_el:
                aria_label = rating_count_el.get('aria-label', '')
                # 提取数字，如 "12,144 ratings" -> 12144
                import re
                match = re.search(r'([\d,]+)\s*ratings?', aria_label)
                if match:
                    result['rating_count'] = int(match.group(1).replace(',', ''))
                    
        except Exception as e:
            logger.warning(f"提取评分信息失败: {e}")
        
        return result
    
    def _extract_variations(self, item: BeautifulSoup) -> Dict[str, Optional[Any]]:
        """提取变体信息"""
        result = {
            'variation_options': None,
            'variation_count': None
        }
        
        try:
            var_el = item.select_one('.s-variation-options-link')
            if var_el:
                var_text = var_el.text.strip()
                result['variation_options'] = var_text
                
                # 提取变体数量，如 "2 sizes" -> 2
                import re
                match = re.search(r'(\d+)\s+', var_text)
                if match:
                    result['variation_count'] = int(match.group(1))
                    
        except Exception as e:
            logger.warning(f"提取变体信息失败: {e}")
        
        return result
    
    def _extract_badges(self, item: BeautifulSoup) -> Dict[str, bool]:
        """提取商品标识（Best Seller, Amazon Choice等）"""
        result = {
            'is_best_seller': False,
            'is_amazon_choice': False
        }
        
        try:
            # Best Seller标识
            if item.select_one('span:contains("Best Seller"), span:contains("Best Sellers")'):
                result['is_best_seller'] = True
            
            # Amazon Choice标识
            if item.select_one('span:contains("Amazon\'s Choice"), span:contains("Amazon Choice")'):
                result['is_amazon_choice'] = True
                
        except Exception as e:
            logger.warning(f"提取标识信息失败: {e}")
        
        return result
    
    def _extract_seller(self, item: BeautifulSoup) -> Optional[str]:
        """提取卖家信息"""
        try:
            seller_el = item.select_one('span:contains("by"), a:contains("by")')
            if seller_el:
                seller_text = seller_el.text.strip()
                # 提取卖家名称
                if 'by ' in seller_text:
                    return seller_text.split('by ')[-1].strip()
        except Exception as e:
            logger.warning(f"提取卖家信息失败: {e}")
        
        return None
    
    def _determine_ad_type(self, item: BeautifulSoup, has_sponsored: bool) -> AdType:
        """判断广告类型"""
        if not has_sponsored:
            return AdType.ORGANIC
        
        # 检查是否为视频广告
        if item.find('video') or item.find('[data-component-type="s-video"]'):
            return AdType.SB_VIDEO
        
        # 检查是否为品牌广告（包含多个商品）
        if item.find('[cel_widget_id*="sb-themed-collection"]') or item.find('.s-flex-grid'):
            return AdType.SB
        
        # 默认为SP广告
        return AdType.SP
    
    def _extract_inner_products(self, item: BeautifulSoup) -> List[Dict]:
        """提取SB广告内的商品列表"""
        inner_products = []
        
        try:
            # 查找内部商品
            inner_items = item.select('[data-asin][data-asin!=""]')
            for inner in inner_items:
                inner_product = {
                    'asin': inner.get('data-asin'),
                    'title': None,
                    'price': None,
                    'rating': None,
                    'url': None
                }
                
                # 标题
                title_el = inner.select_one('.a-size-base-plus, .a-truncate-full')
                if title_el:
                    inner_product['title'] = title_el.text.strip()
                
                # 价格
                price_el = inner.select_one('.a-price .a-offscreen')
                if price_el:
                    inner_product['price'] = price_el.text.strip()
                
                # 评分
                rating_el = inner.select_one('.a-icon-star-mini .a-icon-alt')
                if rating_el:
                    inner_product['rating'] = rating_el.text.strip()
                
                # 链接
                link_el = inner.find('a')
                if link_el and link_el.get('href'):
                    inner_product['url'] = 'https://www.amazon.com' + link_el.get('href')
                
                inner_products.append(inner_product)
                
        except Exception as e:
            logger.warning(f"提取内部商品失败: {e}")
        
        return inner_products
    
    def parse_product(self, item: BeautifulSoup, idx: int, page: int, 
                      organic_rank: int, sponsored_rank: int) -> Optional[ProductInfo]:
        """
        解析单个商品信息
        
        Returns:
            ProductInfo: 商品信息对象，失败返回None
        """
        try:
            # 获取ASIN
            asin = item.get('data-asin')
            if not asin and not item.get('data-cel-widget'):
                return None
            
            # 基础信息
            title_el = item.select_one('h2 span, .a-size-base-plus')
            title = title_el.text.strip() if title_el else "N/A"
            
            # 链接
            link_el = item.select_one('h2 a, a[aria-label*="Sponsored"]')
            url = None
            if link_el and link_el.get('href'):
                href = link_el.get('href')
                url = f"https://www.amazon.com{href}" if href.startswith('/') else href
            
            # 图片
            image_el = item.select_one('.s-image')
            image_small = image_el.get('src') if image_el else None
            image_large = image_small.replace('_UL320_', '_SL1500_') if image_small else None
            
            # 判断是否为广告
            has_sponsored = bool(item.select_one('.puis-sponsored-label-text, [aria-label*="Sponsored"]'))
            
            # 确定广告类型和排名
            ad_type = self._determine_ad_type(item, has_sponsored)
            current_rank = sponsored_rank if has_sponsored else organic_rank
            
            # 提取各类信息
            price_info = self._extract_price(item)
            rating_info = self._extract_rating(item)
            variation_info = self._extract_variations(item)
            badges = self._extract_badges(item)
            seller = self._extract_seller(item)
            
            # 提取配送信息
            delivery_primary_el = item.select_one('.udm-primary-delivery-message')
            delivery_primary = delivery_primary_el.text.strip() if delivery_primary_el else None
            delivery_secondary_el = item.select_one('.udm-secondary-delivery-message')
            delivery_secondary = delivery_secondary_el.text.strip() if delivery_secondary_el else None
            
            # 提取销量
            sales_el = item.select_one('[aria-label*="bought in past month"]')
            sales = sales_el.text.strip() if sales_el else None
            
            # 提取优惠券
            coupon_el = item.select_one('.s-coupon-highlight-color')
            coupon = coupon_el.text.strip() if coupon_el else None
            
            # 提取规格
            spec_el = item.select_one('.s-background-color-platinum')
            spec = spec_el.text.strip() if spec_el else None
            
            # 提取内部商品（SB广告）
            inner_products = self._extract_inner_products(item) if ad_type == AdType.SB else []
            
            # 构建商品信息对象
            product = ProductInfo(
                rank=idx,
                page=page,
                ad_type=ad_type,
                ad_rank=current_rank,
                asin=asin or "N/A",
                title=title,
                url=url or "N/A",
                image_small=image_small or "N/A",
                image_large=image_large or "N/A",
                price_current=price_info['price_current'],
                price_list=price_info['price_list'],
                price_unit=price_info['price_unit'],
                rating_stars=rating_info['rating_stars'],
                rating_count=rating_info['rating_count'],
                spec=spec,
                variation_options=variation_info['variation_options'],
                variation_count=variation_info['variation_count'],
                sales=sales,
                coupon=coupon,
                delivery_primary=delivery_primary,
                delivery_secondary=delivery_secondary,
                is_prime=bool(item.select_one('.a-icon-prime')),
                is_amazon_fulfilled='Ships from Amazon' in item.text if item.text else False,
                is_best_seller=badges['is_best_seller'],
                is_amazon_choice=badges['is_amazon_choice'],
                seller_name=seller,
                inner_products=inner_products,
                scraped_at=datetime.now().isoformat()
            )
            
            return product
            
        except Exception as e:
            logger.error(f"解析商品失败 (索引: {idx}): {e}")
            return None
    
    def scrape_search(self, keyword: str, pages: int = 1) -> List[ProductInfo]:
        """
        爬取亚马逊搜索结果
        
        Args:
            keyword: 搜索关键词
            pages: 爬取页数
            
        Returns:
            List[ProductInfo]: 商品信息列表
        """
        all_products = []
        organic_rank = 1
        sponsored_rank = 1
        
        logger.info(f"开始爬取关键词: {keyword}, 页数: {pages}")
        
        for page in range(1, pages + 1):
            try:
                # 构建URL
                url = f"https://www.amazon.com/s?k={keyword}&page={page}"
                logger.info(f"正在访问第 {page} 页: {url}")
                
                # 发送请求
                response = make_request(url)
                if not response or response.status_code != 200:
                    logger.error(f"请求失败，状态码: {response.status_code if response else 'None'}")
                    continue
                
                # 模拟延迟
                delay = random.uniform(*self.delay_range)
                logger.info(f"等待 {delay:.2f} 秒...")
                time.sleep(delay)
                
                # 解析HTML
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # 查找商品容器
                # 方式1：通过 data-component-type
                items = soup.select('[data-component-type="s-search-result"]')
                
                # 方式2：如果没有找到，尝试其他选择器
                if not items:
                    items = soup.select('.s-result-item[data-asin]')
                
                logger.info(f"第 {page} 页找到 {len(items)} 个商品")
                
                # 解析每个商品
                for idx, item in enumerate(items, start=1):
                    product = self.parse_product(
                        item, idx, page, organic_rank, sponsored_rank
                    )
                    
                    if product:
                        all_products.append(product)
                        
                        # 更新排名计数器
                        if product.ad_type != AdType.ORGANIC:
                            sponsored_rank += 1
                        else:
                            organic_rank += 1
                        
                        # 日志输出
                        logger.info(
                            f"[{product.ad_type.value}] #{product.ad_rank} - "
                            f"ASIN: {product.asin} - {product.title[:50]}..."
                        )
                
                # 页面间延迟
                if page < pages:
                    inter_delay = random.uniform(5, 10)
                    logger.info(f"等待 {inter_delay:.2f} 秒后进入下一页...")
                    time.sleep(inter_delay)
                    
            except Exception as e:
                logger.error(f"爬取第 {page} 页时发生错误: {e}")
                continue
        
        logger.info(f"爬取完成，共获取 {len(all_products)} 个商品")
        return all_products
    
    def save_results(self, products: List[ProductInfo], keyword: str):
        """保存结果到多种格式"""
        if not products:
            logger.warning("没有数据可保存")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"{keyword}_{timestamp}"
        
        # 转换为字典列表
        products_dict = [asdict(p) for p in products]
        
        # 1. 保存为JSON
        json_path = f"{self.output_dir}/{base_filename}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(products_dict, f, ensure_ascii=False, indent=2)
        logger.info(f"JSON保存成功: {json_path}")
        
        # 2. 保存为CSV（扁平化数据）
        csv_path = f"{self.output_dir}/{base_filename}.csv"
        df = pd.DataFrame(products_dict)
        
        # 处理复杂字段
        if 'inner_products' in df.columns:
            df['inner_products_count'] = df['inner_products'].apply(len)
            df['inner_products'] = df['inner_products'].apply(json.dumps)
        
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        logger.info(f"CSV保存成功: {csv_path}")
        
        # 3. 保存为Excel
        excel_path = f"{self.output_dir}/{base_filename}.xlsx"
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            # 主表
            df.to_excel(writer, sheet_name='Products', index=False)
            
            # 统计表
            stats = self.generate_statistics(products)
            stats_df = pd.DataFrame([stats])
            stats_df.to_excel(writer, sheet_name='Statistics', index=False)
            
        logger.info(f"Excel保存成功: {excel_path}")
        
        # 4. 生成报告
        report_path = f"{self.output_dir}/{base_filename}_report.txt"
        self.generate_report(products, keyword, report_path)
        
    def generate_statistics(self, products: List[ProductInfo]) -> Dict:
        """生成统计信息"""
        stats = {
            'total_products': len(products),
            'organic_count': sum(1 for p in products if p.ad_type == AdType.ORGANIC),
            'sp_count': sum(1 for p in products if p.ad_type == AdType.SP),
            'sb_count': sum(1 for p in products if p.ad_type == AdType.SB),
            'sb_video_count': sum(1 for p in products if p.ad_type == AdType.SB_VIDEO),
            'avg_rating': 0,
            'products_with_rating': 0,
            'avg_price': 0,
            'products_with_price': 0,
            'prime_percentage': 0,
            'best_seller_count': 0,
            'amazon_choice_count': 0,
        }
        
        # 计算平均评分和价格
        total_rating = 0
        total_price = 0
        
        for p in products:
            if p.rating_stars:
                stats['products_with_rating'] += 1
                total_rating += p.rating_stars
            
            if p.price_current:
                # 提取数字
                import re
                price_match = re.search(r'[\d\.]+', p.price_current)
                if price_match:
                    stats['products_with_price'] += 1
                    total_price += float(price_match.group())
            
            if p.is_prime:
                stats['prime_percentage'] += 1
            
            if p.is_best_seller:
                stats['best_seller_count'] += 1
            
            if p.is_amazon_choice:
                stats['amazon_choice_count'] += 1
        
        if stats['products_with_rating'] > 0:
            stats['avg_rating'] = total_rating / stats['products_with_rating']
        
        if stats['products_with_price'] > 0:
            stats['avg_price'] = total_price / stats['products_with_price']
        
        stats['prime_percentage'] = (stats['prime_percentage'] / stats['total_products']) * 100
        
        return stats
    
    def generate_report(self, products: List[ProductInfo], keyword: str, report_path: str):
        """生成文本报告"""
        stats = self.generate_statistics(products)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write(f"亚马逊搜索爬虫报告\n")
            f.write(f"关键词: {keyword}\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            
            f.write("【统计概览】\n")
            f.write(f"总商品数: {stats['total_products']}\n")
            f.write(f"自然排名商品: {stats['organic_count']}\n")
            f.write(f"SP广告(单商品): {stats['sp_count']}\n")
            f.write(f"SB广告(品牌): {stats['sb_count']}\n")
            f.write(f"SB视频广告: {stats['sb_video_count']}\n")
            f.write(f"平均评分: {stats['avg_rating']:.2f} (基于{stats['products_with_rating']}个商品)\n")
            f.write(f"平均价格: ${stats['avg_price']:.2f} (基于{stats['products_with_price']}个商品)\n")
            f.write(f"Prime商品占比: {stats['prime_percentage']:.1f}%\n")
            f.write(f"Best Seller商品: {stats['best_seller_count']}\n")
            f.write(f"Amazon Choice商品: {stats['amazon_choice_count']}\n\n")
            
            f.write("【商品详情】\n")
            for product in products:
                f.write("-" * 60 + "\n")
                f.write(f"排名: #{product.ad_rank} ({product.ad_type.value})\n")
                f.write(f"ASIN: {product.asin}\n")
                f.write(f"标题: {product.title}\n")
                if product.price_current:
                    f.write(f"价格: {product.price_current}\n")
                if product.rating_stars:
                    f.write(f"评分: {product.rating_stars} ⭐ ({product.rating_count:,} 条评价)\n")
                if product.sales:
                    f.write(f"销量: {product.sales}\n")
                if product.coupon:
                    f.write(f"优惠: {product.coupon}\n")
                f.write(f"Prime: {'是' if product.is_prime else '否'}\n")
                
                if product.inner_products:
                    f.write(f"包含商品数: {len(product.inner_products)}\n")
                
                f.write(f"爬取时间: {product.scraped_at}\n")
            
            f.write("\n" + "=" * 80 + "\n")
            f.write("报告结束\n")


# ==================== 使用示例 ====================

def main():
    """主函数"""
    # 初始化爬虫
    scraper = AmazonSearchScraper(
        delay_range=(3, 6),      # 延迟3-6秒
        max_retries=3,
        output_dir="./amazon_data"
    )
    
    # 爬取数据
    keyword = "Towel"
    products = scraper.scrape_search(keyword, pages=1)  # pages=1 先测试1页
    
    # 保存结果
    if products:
        scraper.save_results(products, keyword)
        print(f"\n✅ 爬取完成！共获取 {len(products)} 个商品")
        print(f"📁 数据已保存到 {scraper.output_dir} 目录")
    else:
        print("\n❌ 未获取到任何数据")


if __name__ == "__main__":
    main()