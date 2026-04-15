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