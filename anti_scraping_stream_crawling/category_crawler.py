# category_crawler.py - 类目树爬虫
from collections import deque
from typing import Set, List, Dict
import time

class CategoryCrawler:
    """榜单类目树爬虫 - 支持广度/深度优先"""
    
    def __init__(self, session_manager, max_depth=5, strategy='bfs'):
        self.session = session_manager
        self.max_depth = max_depth
        self.strategy = strategy  # 'bfs' or 'dfs'
        self.visited_urls: Set[str] = set()
        self.category_tree: Dict = {}
    
    def crawl_category_tree(self, start_url: str) -> Dict:
        """
        爬取完整的类目树结构
        返回: {
            'url': '...',
            'name': 'Electronics',
            'children': [...],
            'products': ['B01N123...', ...]  # 叶子节点才有
        }
        """
        if self.strategy == 'bfs':
            return self._bfs_crawl(start_url)
        else:
            return self._dfs_crawl(start_url)
    
    def _bfs_crawl(self, start_url: str) -> Dict:
        """广度优先遍历类目树"""
        queue = deque([(start_url, 0, None)])  # (url, depth, parent)
        root = None
        
        while queue:
            url, depth, parent = queue.popleft()
            
            if depth > self.max_depth:
                continue
            
            if url in self.visited_urls:
                continue
            
            self.visited_urls.add(url)
            logger.info(f"爬取类目 [深度{depth}]: {url}")
            
            # 解析页面
            response = self.session_manager.request_with_captcha_retry(url)
            if not response:
                continue
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 提取当前类目信息
            category_node = self._parse_category_page(soup, url, depth)
            
            # 建立树结构
            if parent:
                parent['children'].append(category_node)
            else:
                root = category_node
            
            # 提取子类目链接
            sub_categories = self._extract_subcategories(soup, url)
            
            # 如果到达叶子节点（没有子类目），提取产品ASIN
            if not sub_categories:
                category_node['products'] = self._extract_product_asins(soup)
                logger.info(f"叶子类目，发现 {len(category_node['products'])} 个产品")
            else:
                # 将子类目加入队列
                for sub_url, sub_name in sub_categories:
                    queue.append((sub_url, depth + 1, category_node))
            
            # 礼貌延迟
            time.sleep(random.uniform(2, 4))
        
        return root
    
    def _parse_category_page(self, soup, url: str, depth: int) -> Dict:
        """解析类目页面基本信息"""
        # 提取类目名称
        name_selectors = [
            'h1 span.a-size-base',
            'h1.a-size-large',
            '.category-name',
            'title'
        ]
        
        name = "Unknown"
        for selector in name_selectors:
            el = soup.select_one(selector)
            if el:
                name = el.text.strip()
                break
        
        # 如果是title，去掉"Amazon.com: "前缀
        if selector == 'title' and name.startswith('Amazon.com: '):
            name = name.replace('Amazon.com: ', '')
        
        return {
            'url': url,
            'name': name,
            'depth': depth,
            'children': [],
            'products': []
        }
    
    def _extract_subcategories(self, soup, current_url: str) -> List[tuple]:
        """提取子类目链接和名称"""
        sub_categories = []
        
        # 子类目通常出现在侧边栏或面包屑下方
        selectors = [
            'div#s-refinements ul li a',
            '.categoryRefinementsSection a',
            '.a-unordered-list.a-nostyle a',
            'a.nav-a[href*="/b/ref="]'
        ]
        
        for selector in selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href', '')
                if not href.startswith('http'):
                    href = f"https://www.amazon.com{href}"
                
                # 过滤掉非类目链接
                if '/b/ref=' in href or '/s?i=' in href:
                    name = link.text.strip()
                    if name and href not in self.visited_urls:
                        sub_categories.append((href, name))
            
            if sub_categories:  # 找到子类目就停止
                break
        
        return sub_categories
    
    def _extract_product_asins(self, soup) -> List[str]:
        """从类目列表页提取产品ASIN"""
        asins = []
        
        # ASIN通常在data-asin属性中
        selectors = [
            'div[data-asin]',
            'li[data-asin]',
            'div[data-component-type="s-search-result"]'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            for el in elements:
                asin = el.get('data-asin', '')
                if asin and len(asin) == 10:  # ASIN长度固定10
                    asins.append(asin)
            
            if asins:
                break
        
        return list(set(asins))  # 去重