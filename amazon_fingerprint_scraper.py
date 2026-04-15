# amazon_fingerprint_scraper.py
# 使用 AdsPower 指纹浏览器 + Selenium 控制

import time
import json
import random
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class AdsPowerScraper:
    """通过 AdsPower 指纹浏览器爬取亚马逊"""
    
    def __init__(self, api_url="http://localhost:50325", open_url="http://local.adspower.net:50325"):
        """
        Args:
            api_url: AdsPower 本地 API 地址
            open_url: AdsPower 启动接口
        """
        self.api_url = api_url
        self.open_url = open_url
        self.driver = None
    
    def create_environment(self, name="amazon_scraper", country="US", postal_code="90060"):
        """创建一个新的浏览器环境"""
        payload = {
            "name": name,
            "group_id": "0",
            "domain_name": "amazon.com",
            "language": "en-US",
            "timezone": "America/New_York",
            "country": country,
            "region": "US",
            "postal_code": postal_code,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "flags": {
                "disable_password_saving": True,
                "disable_autofill": True,
            }
        }
        response = requests.post(f"{self.api_url}/api/v1/user/create", json=payload)
        return response.json()
    
    def open_environment(self, user_id):
        """打开指定的浏览器环境"""
        response = requests.get(f"{self.open_url}/api/v1/browser/start?user_id={user_id}")
        data = response.json()
        if data.get("code") == 0:
            driver_path = data["data"]["webdriver"]
            # 连接到已打开的浏览器
            self.driver = webdriver.Remote(
                command_executor=driver_path,
                options=webdriver.ChromeOptions()
            )
            return True
        return False
    
    def close_environment(self, user_id):
        """关闭浏览器环境"""
        requests.get(f"{self.open_url}/api/v1/browser/stop?user_id={user_id}")
        if self.driver:
            self.driver.quit()
    
    def scrape_search(self, keyword, pages=1):
        """爬取搜索结果"""
        all_products = []
        
        self.driver.get(f"https://www.amazon.com/s?k={keyword}")
        time.sleep(3)  # 等待页面加载
        
        for page in range(1, pages + 1):
            if page > 1:
                # 翻页
                next_btn = self.driver.find_element(By.CSS_SELECTOR, 'a.s-pagination-next')
                next_btn.click()
                time.sleep(random.uniform(3, 6))
            
            # 获取所有商品卡片
            items = self.driver.find_elements(By.CSS_SELECTOR, '[data-component-type="s-search-result"]')
            
            for item in items:
                try:
                    asin = item.get_attribute("data-asin")
                    title_el = item.find_element(By.CSS_SELECTOR, "h2 span")
                    title = title_el.text.strip()
                    
                    # 获取价格
                    try:
                        price_el = item.find_element(By.CSS_SELECTOR, ".a-price .a-offscreen")
                        price = price_el.text.strip()
                    except:
                        price = None
                    
                    all_products.append({
                        "asin": asin,
                        "title": title,
                        "price": price,
                        "page": page,
                    })
                except Exception as e:
                    continue
            
            time.sleep(random.uniform(5, 10))
        
        return all_products


# 使用示例
def main():
    scraper = AdsPowerScraper()
    
    # 1. 创建环境（只需创建一次，记住 user_id）
    # result = scraper.create_environment(name="amazon_prod", postal_code="90060")
    # user_id = result["data"]["id"]
    user_id = "YOUR_USER_ID"  # 替换为你的环境ID
    
    # 2. 打开环境
    if scraper.open_environment(user_id):
        # 3. 爬取数据
        products = scraper.scrape_search("towels", pages=1)
        
        for p in products:
            print(f"ASIN: {p['asin']}, 价格: {p['price']}")
        
        # 4. 关闭
        scraper.close_environment(user_id)

if __name__ == "__main__":
    main()