# coordinator.py - 任务协调器
from concurrent.futures import ThreadPoolExecutor, as_completed
import sqlite3

class AmazonScrapingCoordinator:
    """协调各模块完成复杂任务"""
    
    def __init__(self, session_manager):
        self.session = session_manager
        self.detail_spider = DetailSpider(session_manager)
        self.category_crawler = CategoryCrawler(session_manager)
        self.search_spider = AmazonSearchScraper(...)  # 你现有的
        
        # 数据库存储
        self.conn = sqlite3.connect('amazon_data.db')
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS products (
                asin TEXT PRIMARY KEY,
                title TEXT,
                price REAL,
                rating REAL,
                review_count INTEGER,
                brand TEXT,
                bsr_rank INTEGER,
                bsr_category TEXT,
                scraped_at REAL
            )
        ''')
        
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS category_products (
                category_url TEXT,
                asin TEXT,
                depth INTEGER,
                scraped_at REAL,
                FOREIGN KEY(asin) REFERENCES products(asin)
            )
        ''')
    
    def analyze_category(self, category_url: str, max_depth=3):
        """分析整个类目：爬取树结构 + 所有产品详情"""
        logger.info(f"开始分析类目: {category_url}")
        
        # 1. 爬取类目树
        tree = self.category_crawler.crawl_category_tree(category_url)
        
        # 2. 收集所有叶子节点的产品ASIN
        all_asins = set()
        
        def collect_asins(node):
            if node.get('products'):
                all_asins.update(node['products'])
            for child in node.get('children', []):
                collect_asins(child)
        
        collect_asins(tree)
        logger.info(f"共发现 {len(all_asins)} 个唯一产品")
        
        # 3. 批量获取产品详情（并发）
        self._batch_get_details(list(all_asins))
        
        # 4. 保存类目关系
        self._save_category_relations(tree)
        
        return tree
    
    def _batch_get_details(self, asins: List[str], max_workers=5):
        """并发获取产品详情"""
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_asin = {
                executor.submit(self.detail_spider.get_product_detail, asin): asin 
                for asin in asins
            }
            
            for future in as_completed(future_to_asin):
                asin = future_to_asin[future]
                try:
                    detail = future.result()
                    results[asin] = detail
                    
                    # 存入数据库
                    self._save_product_detail(detail)
                    
                    logger.info(f"✓ {asin} - {detail.get('title', 'N/A')[:30]}")
                except Exception as e:
                    logger.error(f"✗ {asin} 失败: {e}")
                
                # 控制请求频率
                time.sleep(random.uniform(1, 2))
        
        return results
    
    def _save_product_detail(self, detail: Dict):
        """保存产品详情到数据库"""
        self.conn.execute('''
            INSERT OR REPLACE INTO products 
            (asin, title, price, rating, review_count, brand, bsr_rank, bsr_category, scraped_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            detail.get('asin'),
            detail.get('title'),
            detail.get('price'),
            detail.get('rating'),
            detail.get('review_count'),
            detail.get('brand'),
            detail.get('bsr_rank'),
            detail.get('bsr_category'),
            detail.get('scraped_at')
        ))
        self.conn.commit()