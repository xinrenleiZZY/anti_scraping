# postgresql_single_table.py
import psycopg2
from psycopg2.extras import Json, execute_values
from typing import List, Dict, Optional
import json
from datetime import datetime

class PostgreSQLSingleTable:
    def __init__(self, dsn: str):
        self.conn = psycopg2.connect(dsn)
        self.cursor = self.conn.cursor()
    
    def save_products(self, keyword: str, items: List, postal_code: str = "90060"):
        """批量保存产品到单表"""
        
        search_id = f"{keyword}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 准备批量插入数据
        products_data = []
        for item in items:
            # 解析价格数值
            price_current_num = self._parse_price_numeric(item.price_current)
            price_list_num = self._parse_price_numeric(item.price_list)
            
            # 处理inner_products（转为JSONB）
            inner_products_json = item.inner_products if item.inner_products else []
            inner_count = len(inner_products_json)
            
            product_record = (
                search_id,
                keyword,
                item.page,
                item.data_index,
                item.asin,
                item.title[:5000] if item.title else None,  # 限制长度
                item.url,
                item.brand_name,
                item.price_current,
                price_current_num,
                item.price_list,
                price_list_num,
                item.rating_stars,
                item.rating_count,
                item.ad_type,
                item.ad_rank,
                item.organic_rank,
                item.is_prime,
                getattr(item, 'has_video', False),
                item.image_small,
                item.image_large,
                Json(inner_products_json),  # PostgreSQL JSONB
                inner_count,
                datetime.now()
            )
            products_data.append(product_record)
        
        # 批量插入（性能更好）
        execute_values(self.cursor, """
            INSERT INTO amazon_products (
                search_id, keyword, search_page, data_index,
                asin, title, url, brand_name,
                price_current, price_current_numeric,
                price_list, price_list_numeric,
                rating_stars, rating_count,
                ad_type, ad_rank, organic_rank,
                is_prime, has_video,
                image_small, image_large,
                inner_products, inner_products_count,
                scraped_at
            ) VALUES %s
        """, products_data)
        
        self.conn.commit()
        print(f"✅ 成功保存 {len(products_data)} 条记录")
        return search_id
    
    def _parse_price_numeric(self, price_str: str) -> Optional[float]:
        """将价格字符串转换为数值"""
        if not price_str:
            return None
        try:
            # 移除 $, 逗号, 空格
            cleaned = price_str.replace('$', '').replace(',', '').strip()
            return float(cleaned)
        except:
            return None
    
    # ========== 查询方法 ==========
    
    def get_products_by_keyword(self, keyword: str, limit: int = 100):
        """查询指定关键词的所有产品"""
        self.cursor.execute("""
            SELECT asin, title, price_current, ad_type, ad_rank, organic_rank
            FROM amazon_products
            WHERE keyword = %s
            ORDER BY search_page, data_index
            LIMIT %s
        """, (keyword, limit))
        return self.cursor.fetchall()
    
    def get_sponsored_ads(self, keyword: str):
        """查询SP广告"""
        self.cursor.execute("""
            SELECT asin, title, price_current, ad_rank
            FROM amazon_products
            WHERE keyword = %s AND ad_type = 'SP'
            ORDER BY ad_rank
        """, (keyword,))
        return self.cursor.fetchall()
    
    def get_sb_ads_with_products(self, keyword: str):
        """查询SB广告及其内部商品（JSONB解析）"""
        self.cursor.execute("""
            SELECT 
                brand_name,
                title,
                inner_products,
                inner_products_count
            FROM amazon_products
            WHERE keyword = %s AND ad_type = 'SB'
            ORDER BY ad_rank
        """, (keyword,))
        
        results = []
        for row in self.cursor.fetchall():
            brand, title, inner_products, count = row
            results.append({
                'brand': brand,
                'title': title,
                'products': inner_products,  # 已经是Python列表
                'product_count': count
            })
        return results
    
    def search_inner_products_by_asin(self, asin: str):
        """查询包含特定ASIN的SB广告（JSONB查询）"""
        self.cursor.execute("""
            SELECT 
                keyword,
                brand_name,
                title,
                inner_products
            FROM amazon_products
            WHERE ad_type = 'SB' 
              AND inner_products @> %s
            ORDER BY scraped_at DESC
        """, (json.dumps([{'asin': asin}]),))
        return self.cursor.fetchall()
    
    def get_statistics(self, keyword: str = None):
        """获取统计信息"""
        where_clause = f"WHERE keyword = '{keyword}'" if keyword else ""
        
        self.cursor.execute(f"""
            SELECT 
                ad_type,
                COUNT(*) as total_count,
                AVG(price_current_numeric) as avg_price,
                AVG(rating_stars) as avg_rating,
                SUM(inner_products_count) as total_inner_products,
                COUNT(DISTINCT asin) as unique_asins
            FROM amazon_products
            {where_clause}
            GROUP BY ad_type
            ORDER BY 
                CASE ad_type
                    WHEN 'Title' THEN 1
                    WHEN 'SB' THEN 2
                    WHEN 'SP' THEN 3
                    WHEN 'Organic' THEN 4
                    ELSE 5
                END
        """)
        return self.cursor.fetchall()
    
    def get_top_ranked_organic(self, keyword: str, limit: int = 20):
        """获取自然排名前N的商品"""
        self.cursor.execute("""
            SELECT 
                organic_rank,
                asin,
                title,
                price_current,
                rating_stars,
                rating_count
            FROM amazon_products
            WHERE keyword = %s 
              AND ad_type = 'Organic'
              AND organic_rank IS NOT NULL
            ORDER BY organic_rank
            LIMIT %s
        """, (keyword, limit))
        return self.cursor.fetchall()
    
    def get_price_range_analysis(self, keyword: str):
        """价格区间分析"""
        self.cursor.execute("""
            SELECT 
                CASE 
                    WHEN price_current_numeric < 10 THEN '0-10'
                    WHEN price_current_numeric < 25 THEN '10-25'
                    WHEN price_current_numeric < 50 THEN '25-50'
                    WHEN price_current_numeric < 100 THEN '50-100'
                    ELSE '100+'
                END as price_range,
                COUNT(*) as product_count,
                AVG(rating_stars) as avg_rating
            FROM amazon_products
            WHERE keyword = %s 
              AND ad_type IN ('Organic', 'SP')
              AND price_current_numeric IS NOT NULL
            GROUP BY price_range
            ORDER BY MIN(price_current_numeric)
        """, (keyword,))
        return self.cursor.fetchall()
    
    def search_by_title_keyword(self, keyword: str, search_term: str):
        """标题关键词搜索（全文检索）"""
        self.cursor.execute("""
            SELECT asin, title, price_current, ad_type
            FROM amazon_products
            WHERE keyword = %s 
              AND title ILIKE %s
            ORDER BY organic_rank NULLS LAST, ad_rank
            LIMIT 50
        """, (keyword, f'%{search_term}%'))
        return self.cursor.fetchall()
    
    def close(self):
        self.cursor.close()
        self.conn.close()