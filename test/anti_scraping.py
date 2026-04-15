import requests
import random
import threading
import time
from fake_useragent import UserAgent

# 代理池
PROXY_POOL = [
    "http://127.0.0.1:7890",
    "http://13.36.243.194:862",
]

# 线程本地存储
session_local = threading.local()

def get_session():
    """为每个线程创建独立的session"""
    if not hasattr(session_local, "session"):
        session_local.session = requests.Session()
        # 初始化会话
        session_local.session.get("https://www.amazon.com", headers=get_random_headers(), timeout=20)
    return session_local.session

def get_random_headers():
    """动态生成请求头"""
    ua = UserAgent()
    return {
        "User-Agent": ua.random,
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "sec-ch-ua": '"Not A;Brand";v="99", "Chromium";v="131", "Google Chrome";v="131"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "Connection": "keep-alive",
        "Referer": "https://www.amazon.com/"
    }

def get_random_proxy():
    """随机获取代理"""
    if not PROXY_POOL:
        return None
    proxy = random.choice(PROXY_POOL)
    return {"http": proxy, "https": proxy}

def make_request(url, max_retries=3):
    """发送请求，带重试机制"""
    session = get_session()
    
    for retry in range(max_retries):
        headers = get_random_headers()
        proxies = get_random_proxy()
        
        try:
            resp = session.get(
                url,
                headers=headers,
                timeout=25,
                # proxies=proxies,  # 根据需要启用代理
                allow_redirects=True
            )
            
            # 状态码检查
            if resp.status_code == 200:
                # 反爬检查
                if "To discuss automated access to Amazon data" in resp.text:
                    print("反爬拦截，重试中...")
                    time.sleep(2 ** retry + random.uniform(1, 2))
                    continue
                if "Sorry, we just need to make sure you're not a robot" in resp.text:
                    print("验证码，重试中...")
                    time.sleep(2 ** retry + random.uniform(1, 2))
                    continue
                return resp
            else:
                print(f"HTTP {resp.status_code}，重试中...")
                time.sleep(2 ** retry + random.uniform(1, 2))
                continue
        except Exception as e:
            print(f"异常: {str(e)}，重试中...")
            time.sleep(2 ** retry + random.uniform(1, 2))
            continue
    
    return None
