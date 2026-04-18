# session_manager.py - 增强版会话管理
import time
import random
from typing import Optional, Tuple
from curl_cffi.requests import Session
from PIL import Image
import pytesseract
import requests

class SessionManager:
    """游客会话管理 + 验证码处理"""
    
    def __init__(self, proxy=None, captcha_handler=None):
        self.proxy = proxy
        self.captcha_handler = captcha_handler or self._default_captcha_handler
        self.session = self._create_session()
        self.cookie_jar = {}
        
    def _create_session(self):
        """创建带浏览器指纹的会话"""
        browsers = ["chrome120", "chrome123", "safari15_5"]
        return Session(impersonate=random.choice(browsers), proxy=self.proxy)
    
    def _default_captcha_handler(self, captcha_url: str) -> str:
        """默认验证码处理（可替换为打码平台）"""
        # 下载验证码图片
        resp = requests.get(captcha_url)
        with open("captcha.png", "wb") as f:
            f.write(resp.content)
        
        # OCR识别（效果有限，建议接入2Captcha/打码兔）
        image = Image.open("captcha.png")
        code = pytesseract.image_to_string(image).strip()
        return code
    
    def request_with_captcha_retry(self, url: str, max_retries=3):
        """带验证码处理的请求"""
        for attempt in range(max_retries):
            response = self.session.get(url, timeout=30)
            
            # 检测验证码
            if "captcha" in response.url.lower() or "robot" in response.text.lower():
                logger.warning(f"遇到验证码，尝试解决 (第{attempt+1}次)")
                
                # 提取验证码图片URL
                soup = BeautifulSoup(response.text, 'html.parser')
                img = soup.select_one('form img')
                if img and img.get('src'):
                    captcha_url = img['src']
                    if not captcha_url.startswith('http'):
                        captcha_url = f"https://www.amazon.com{captcha_url}"
                    
                    # 调用验证码处理器
                    solution = self.captcha_handler(captcha_url)
                    
                    # 提交验证码
                    form_data = {
                        'field-keywords': solution,
                        'action': '验证'
                    }
                    response = self.session.post(response.url, data=form_data)
                    
                    if "captcha" not in response.url:
                        logger.info("验证码解决成功")
                        return response
            
            elif response.status_code == 200:
                return response
            
            time.sleep(random.uniform(5, 10) * (attempt + 1))
        
        return None