import requests
from bs4 import BeautifulSoup
import json
import time
import random
import os
from pathlib import Path
from fake_useragent import UserAgent
from merge_json_words import merge_all_json_files
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from queue import Queue

# ===================== 配置 =====================
RESULT_JSON = "ASIN_Related_Data_Set/stream_results.jsonl"
FAILED_JSON = "ASIN_Related_Data_Set/stream_failed.json"

DELAY_MIN = 3      # 最小延迟（秒）
DELAY_MAX = 8      # 最大延迟
MAX_RETRIES = 3    # 最大重试次数
MAX_WORKERS = 8    # 线程数（建议3-4个，不要太多）
BATCH_SIZE = 50    # 每批处理数量，批次间增加休息
# ===================================================

# 全局锁，保护文件写入
write_lock = threading.Lock()
session_local = threading.local()

# 代理池
PROXY_POOL = [
    "http://127.0.0.1:7890",
    "http://13.36.243.194:862",
]

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

def crawl_one(asin, worker_id):
    """爬取单个商品（线程安全）"""
    url = f"https://www.amazon.com/dp/{asin}"
    headers = get_random_headers()
    proxies = get_random_proxy()
    
    try:
        session = get_session()
        resp = session.get(
            url,
            headers=headers,
            timeout=25,
            # proxies=proxies,  # 根据需要启用代理
            allow_redirects=True
        )
        
        # 状态码检查
        if resp.status_code in [403, 404, 500, 503]:
            return {"success": False, "error": f"HTTP {resp.status_code}"}
        
        # 反爬检查
        if "To discuss automated access to Amazon data" in resp.text:
            return {"success": False, "error": "反爬拦截"}
        if "Sorry, we just need to make sure you're not a robot" in resp.text:
            return {"success": False, "error": "验证码"}
        
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # 解析标题
        title_elem = soup.find("span", id="productTitle") or soup.find("h1")
        title = title_elem.get_text(strip=True) if title_elem else "无标题"
        
        # 解析卖点
        feature = soup.find("div", id="feature-bullets")
        bullets = []
        
        if feature:
            items = feature.find_all("span", class_="a-list-item")
            bullets = [i.get_text(strip=True) for i in items if i.get_text(strip=True)]
        
        if not bullets:
            bullet_elements = soup.select("ul.a-unordered-list.a-vertical.a-spacing-mini li span")
            bullets = [b.get_text(strip=True) for b in bullet_elements if b.get_text(strip=True)]
        
        # 随机延迟，模拟人类行为
        time.sleep(random.uniform(0.5, 1.5))
        
        return {
            "success": True,
            "title": title,
            "bullets": bullets,
            "content": "\n".join(bullets),
            "error": None
        }
        
    except Exception as e:
        return {"success": False, "error": f"异常: {str(e)}"}

def write_stream_result(item):
    """线程安全的写入"""
    with write_lock:
        os.makedirs(os.path.dirname(RESULT_JSON), exist_ok=True)
        with open(RESULT_JSON, "a", encoding="utf-8") as f:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

def get_crawled_asins():
    """获取已爬取的ASIN"""
    crawled = set()
    if os.path.exists(RESULT_JSON):
        with open(RESULT_JSON, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    crawled.add(data["ASIN"])
                except:
                    continue
    return crawled

def get_asins_from_merged():
    """获取ASIN列表"""
    print("🔄 正在获取最新的ASIN列表...")
    asin_list = merge_all_json_files()
    
    if not asin_list:
        print("❌ 合并数据失败")
        return []
    
    asins = [item.get("asin") for item in asin_list if item.get("asin")]
    print(f"✅ 成功获取 {len(asins)} 个ASIN")
    return asins

def process_asin(asin, worker_id):
    """处理单个ASIN（带重试）"""
    for retry in range(MAX_RETRIES):
        result = crawl_one(asin, worker_id)
        if result["success"]:
            break
        # 重试延迟递增
        time.sleep(2 ** retry + random.uniform(1, 2))
    
    item = {
        "ASIN": asin,
        "title": result.get("title", ""),
        "bullets": result.get("bullets", []),
        "bullets_count": len(result.get("bullets", [])),
        "content": result.get("content", ""),
        "success": result["success"],
        "error": result.get("error")
    }
    
    write_stream_result(item)
    return item

def main():
    print("="*60)
    print("🚀 启动多线程爬虫程序")
    print(f"⚙️  配置信息:")
    print(f"   - 线程数: {MAX_WORKERS}")
    print(f"   - 延迟范围: {DELAY_MIN}-{DELAY_MAX}秒")
    print(f"   - 批次大小: {BATCH_SIZE}")
    print("="*60)
    
    # 获取ASIN列表
    all_asins = get_asins_from_merged()
    if not all_asins:
        print("❌ 无法获取ASIN列表")
        return
    
    # 过滤已爬取的
    crawled_asins = get_crawled_asins()
    todo_asins = [a for a in all_asins if a not in crawled_asins]
    
    print(f"📊 统计:")
    print(f"   - 总ASIN: {len(all_asins)}")
    print(f"   - 已完成: {len(crawled_asins)}")
    print(f"   - 待爬取: {len(todo_asins)}")
    
    if not todo_asins:
        print("🎉 全部已爬完！")
        return
    
    # 分批处理
    batches = [todo_asins[i:i+BATCH_SIZE] for i in range(0, len(todo_asins), BATCH_SIZE)]
    print(f"📦 分 {len(batches)} 批处理，每批最多 {BATCH_SIZE} 个\n")
    
    success_count = 0
    failed_asins = []
    
    for batch_idx, batch in enumerate(batches, 1):
        print(f"\n{'='*60}")
        print(f"开始处理第 {batch_idx}/{len(batches)} 批")
        print(f"{'='*60}")
        
        # 使用线程池处理当前批次
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(process_asin, asin, i % MAX_WORKERS): asin 
                for i, asin in enumerate(batch)
            }
            
            for future in as_completed(futures):
                asin = futures[future]
                try:
                    result = future.result()
                    if result["success"]:
                        success_count += 1
                        print(f"✅ [{success_count}/{len(todo_asins)}] {asin} - {result['bullets_count']}个卖点")
                    else:
                        failed_asins.append({"asin": asin, "error": result["error"]})
                        print(f"❌ {asin} - {result['error']}")
                except Exception as e:
                    failed_asins.append({"asin": asin, "error": str(e)})
                    print(f"❌ {asin} - 处理异常: {e}")
        
        # 批次间休息，避免请求过于密集
        if batch_idx < len(batches):
            rest_time = random.uniform(10, 20)
            print(f"\n⏸️  批次完成，休息 {rest_time:.1f} 秒...")
            time.sleep(rest_time)
    
    # 保存失败记录
    with open(FAILED_JSON, "w", encoding="utf-8") as f:
        json.dump(failed_asins, f, ensure_ascii=False, indent=2)
    
    print("\n" + "="*60)
    print("🎉 爬取完成！")
    print(f"✅ 成功: {success_count}")
    print(f"❌ 失败: {len(failed_asins)}")
    print(f"📁 结果保存: {RESULT_JSON}")
    print(f"📁 失败记录: {FAILED_JSON}")
    print("="*60)

if __name__ == "__main__":
    main()