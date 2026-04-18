# detail_spider.py - 详情页爬虫
from typing import Dict, Optional, List
from functools import lru_cache

class DetailSpider:
    """产品详情爬虫 - 支持多重XPath降级"""
    
    def __init__(self, session_manager):
        self.session = session_manager
        
        # 为每个字段定义多个XPath备选方案
        self.xpath_patterns = {
            'price': [
                '//span[@class="a-price-whole"]/text()',
                '//span[@class="a-offscreen"]/text()',
                '//span[@data-a-price]/@data-a-price',
                '//span[@id="priceblock_ourprice"]/text()',
                '//span[@id="priceblock_dealprice"]/text()',
                '//span[@class="a-price"]//span[@class="a-price-whole"]/text()',
            ],
            'title': [
                '//span[@id="productTitle"]/text()',
                '//h1[@class="a-size-large"]/text()',
                '//meta[@property="og:title"]/@content',
            ],
            'rating': [
                '//span[@data-hook="rating-out-of-text"]/text()',
                '//span[@class="a-icon-alt"]/text()',
                '//div[@id="averageCustomerReviews"]//span[@class="a-icon-alt"]/text()',
            ],
            'review_count': [
                '//span[@data-hook="total-review-count"]/text()',
                '//div[@id="averageCustomerReviews"]//span[@data-hook="total-review-count"]/text()',
                '//a[@data-hook="see-all-reviews-link-foot"]/text()',
            ],
            'bsr_rank': [
                '//th[contains(text(),"Best Sellers Rank")]/following-sibling::td/span/text()',
                '//tr[td[contains(text(),"Best Sellers Rank")]]/td[2]/text()',
                '//li[@id="SalesRank"]/text()',
            ],
            'brand': [
                '//a[@id="bylineInfo"]/text()',
                '//tr[td[contains(text(),"Brand")]]/td[2]/text()',
                '//div[@id="brand"]/a/text()',
            ],
        }
        
        # 缓存解析器，避免重复解析
        self._soup_cache = {}
    
    def extract_field(self, soup, field_name: str, clean_func=None) -> Optional[str]:
        """通用字段提取器，按优先级尝试所有XPath"""
        if field_name not in self.xpath_patterns:
            return None
        
        for xpath in self.xpath_patterns[field_name]:
            try:
                elements = soup.xpath(xpath)
                if elements:
                    value = elements[0].strip() if elements[0] else None
                    if value and clean_func:
                        value = clean_func(value)
                    if value:  # 非空即成功
                        logger.debug(f"成功提取 {field_name} 使用: {xpath[:50]}...")
                        return value
            except Exception as e:
                logger.debug(f"XPath失败 {xpath}: {e}")
                continue
        
        logger.warning(f"所有XPath尝试失败，未能提取 {field_name}")
        return None
    
    def parse_price(self, price_str: str) -> float:
        """价格清洗：$24.99 -> 24.99"""
        if not price_str:
            return None
        import re
        match = re.search(r'[\d,]+\.?\d*', price_str)
        return float(match.group().replace(',', '')) if match else None
    
    def parse_rating(self, rating_str: str) -> float:
        """评分清洗：4.5 out of 5 stars -> 4.5"""
        if not rating_str:
            return None
        import re
        match = re.search(r'(\d+\.?\d*)', rating_str)
        return float(match.group(1)) if match else None
    
    @lru_cache(maxsize=1000)
    def get_product_detail(self, asin: str) -> Dict:
        """获取产品详情（带缓存）"""
        url = f"https://www.amazon.com/dp/{asin}"
        response = self.session_manager.request_with_captcha_retry(url)
        
        if not response:
            return {'asin': asin, 'error': '请求失败'}
        
        from lxml import html
        tree = html.fromstring(response.content)
        
        detail = {
            'asin': asin,
            'url': url,
            'scraped_at': time.time()
        }
        
        # 提取各字段
        detail['price'] = self.parse_price(
            self.extract_field(tree, 'price')
        )
        detail['title'] = self.extract_field(tree, 'title')
        detail['rating'] = self.parse_rating(
            self.extract_field(tree, 'rating')
        )
        detail['review_count'] = self.extract_field(
            tree, 'review_count', 
            clean_func=lambda x: int(re.sub(r'[^\d]', '', x))
        )
        detail['brand'] = self.extract_field(tree, 'brand')
        
        # BSR排名特殊处理（包含类目信息）
        bsr_raw = self.extract_field(tree, 'bsr_rank')
        if bsr_raw:
            detail['bsr_rank'], detail['bsr_category'] = self.parse_bsr(bsr_raw)
        
        return detail
    
    def parse_bsr(self, bsr_text: str) -> Tuple[Optional[int], Optional[str]]:
        """解析BSR排名：'#12 in Sports & Outdoors' -> (12, 'Sports & Outdoors')"""
        import re
        match = re.search(r'#(\d+)\s+in\s+(.+)', bsr_text)
        if match:
            return int(match.group(1)), match.group(2).strip()
        return None, None