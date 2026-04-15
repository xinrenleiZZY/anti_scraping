方案1：使用Selenium（模拟浏览器，最接近人工）
此方案通过控制一个真实的浏览器（如Chrome）来访问网页，能完美执行页面JavaScript，最不容易被基础的反爬机制识别。

优点：可以处理复杂的JS加载页面，行为接近真实用户。

缺点：速度慢、资源占用高，且亚马逊仍可能通过行为分析封禁，需要配合代理使用。

测试代码示例：
你可以复制这段代码，直接运行试试看。它会打开一个真实的浏览器窗口，加载亚马逊搜索页。

python
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
运行说明：你需要先安装 selenium 库 (pip install selenium)，并下载与本地Chrome浏览器版本匹配的 chromedriver 驱动。

方案2：使用Requests + 硬核伪装（最轻量，但最不稳定）
这是你最初尝试的方法，虽然可以通过添加Headers绕过一些基础检测，但面对亚马逊复杂的反爬机制，成功率很低，且非常容易被封IP。

优点：无需额外工具，代码轻量快速。

缺点：稳定性极差，需要维护复杂的Headers和代理IP池。

测试代码示例（尝试修复503错误）：
这段代码模仿了之前一些文章里的做法，通过添加完整的Headers来尝试规避。但请注意，这种方法现在成功率不高。

python
import requests
from bs4 import BeautifulSoup

# 1. 使用完整的浏览器头信息来伪装
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Referer': 'https://www.google.com/', # 关键伪装
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'cross-site',
}

# 2. 发起请求（仍然可能失败）
search_keyword = "laptop stand"
url = f"https://www.amazon.com/s?k={search_keyword}"

try:
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    
    # 如果成功，开始解析
    soup = BeautifulSoup(response.text, 'html.parser')
    print("状态码: 200, 请求成功!")
    
    # 这里可以添加你的解析逻辑，但注意，这个方法极不稳定。
    
except requests.exceptions.RequestException as e:
    print(f"请求失败: {e}")
    print("这证明简单的Headers伪装已经很难突破亚马逊的封锁了。")