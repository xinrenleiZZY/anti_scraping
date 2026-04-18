# test_amazon.py
from curl_cffi.requests import Session

def test_amazon_access():
    session = Session(impersonate="chrome120")
    
    # 设置请求头
    session.headers.update({
        'Accept-Language': 'en-US,en;q=0.9',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    })
    
    # 1. 先访问首页
    print("1. 访问首页...")
    resp1 = session.get('https://www.amazon.com/')
    print(f"   状态码: {resp1.status_code}")
    
    # 2. 设置邮编
    print("2. 设置邮编...")
    session.cookies.set('postalCode', '10001')
    session.cookies.set('shippingPostalCode', '10001')
    
    # 3. 搜索商品
    print("3. 搜索商品...")
    resp2 = session.get('https://www.amazon.com/s?k=towels')
    print(f"   状态码: {resp2.status_code}")
    
    # 4. 检查结果
    text = resp2.text[:2000].lower()
    if 'cny' in text or '￥' in text:
        print("❌ 结果: 中国站 (人民币)")
    elif '$' in text:
        print("✅ 结果: 美国站 (美元)")
    else:
        print("⚠️ 无法确定，请检查")
    
    # 5. 保存HTML
    with open("test_result.html", "w", encoding="utf-8") as f:
        f.write(resp2.text)
    print("HTML已保存到 test_result.html")

if __name__ == "__main__":
    test_amazon_access()