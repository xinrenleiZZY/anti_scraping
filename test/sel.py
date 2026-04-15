from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time

# 1. 设置浏览器选项，伪装一下
options = Options()
options.add_argument("--window-size=1920,1080")
options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

# 2. 启动浏览器（需要先下载 chromedriver 并放到 PATH 里）
driver = webdriver.Chrome(options=options)

# 3. 访问亚马逊搜索页
search_keyword = "laptop stand"
url = f"https://www.amazon.com/s?k={search_keyword}"
print(f"正在访问: {url}")
driver.get(url)

# 4. 等待页面加载完成
time.sleep(5)

# 5. 提取所有商品卡片（不论是否广告）
# 商品卡片的通用选择器
product_cards = driver.find_elements(By.CSS_SELECTOR, "[data-component-type='s-search-result']")

print(f"\n=== 第一页前5个商品信息 ===")
for i, card in enumerate(product_cards[:5]):
    # 判断是否带广告标识
    is_sponsored = len(card.find_elements(By.CSS_SELECTOR, "[aria-label='Sponsored Ad']")) > 0
    
    # 提取ASIN
    asin = card.get_attribute("data-asin")
    
    # 提取商品标题
    try:
        title = card.find_element(By.CSS_SELECTOR, "h2 a span").text
    except:
        title = "N/A"
    
    # 输出信息
    ad_type = "广告 (SP)" if is_sponsored else "自然排名"
    print(f"排名 {i+1}: {ad_type}")
    print(f"  ASIN: {asin}")
    print(f"  标题: {title[:80]}...")

# 6. 关闭浏览器
driver.quit()