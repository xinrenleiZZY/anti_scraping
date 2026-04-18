# request_executor.py
"""
请求执行器
功能：整合所有反爬模块，执行实际请求
"""

import time
import random
import logging
from typing import Optional, Dict, Any
from curl_cffi import requests
from curl_cffi.requests import Session

from .proxy_manager import ProxyManager
from .headers_manager import HeadersManager
from .throttler import AdaptiveThrottler
from .retry_handler import RetryHandler
from .captcha_solver import CaptchaDetector, CaptchaSolver

logger = logging.getLogger(__name__)


class RequestExecutor:
    """请求执行器 - 整合所有反爬模块"""
    
    def __init__(self, config):
        self.config = config
        self.session = None
        
        # 初始化各模块
        self.proxy_manager = ProxyManager(config)
        self.headers_manager = HeadersManager(config)
        self.throttler = AdaptiveThrottler(config)
        self.retry_handler = RetryHandler(config)
        self.captcha_detector = CaptchaDetector()
        self.captcha_solver = CaptchaSolver(config)
        
        # 初始化会话
        self._init_session()
    
    def _init_session(self):
        """初始化请求会话"""
        self.session = Session(impersonate="chrome120")
    
    def _get_proxies(self) -> Optional[Dict[str, str]]:
        """获取代理"""
        if not self.config.USE_PROXY:
            return None
        
        proxy = self.proxy_manager.get_proxy()
        if proxy:
            logger.debug(f"使用代理: {proxy.get('http', 'unknown')}")
        
        return proxy
    
    def _handle_response(self, response: requests.Response, url: str) -> Optional[requests.Response]:
        """处理响应（验证码检测等）"""
        if not response:
            return None
        
        # 检测验证码
        if self.captcha_detector.has_captcha(response.text):
            logger.warning(f"遇到验证码: {url}")
            
            # 尝试解决验证码
            captcha_result = self.captcha_solver.solve(response.text, url)
            
            if captcha_result:
                # 有验证码结果，重新请求
                logger.info("验证码已解决，重新请求")
                return self._execute_request(url, response.request.headers)
            else:
                # 无法解决，等待后重试
                logger.warning("无法解决验证码，等待30秒")
                time.sleep(30)
                return None
        
        return response
    
    def _execute_request(self, url: str, headers: Dict, proxies: Optional[Dict] = None) -> Optional[requests.Response]:
        """执行实际请求"""
        try:
            start_time = time.time()
            
            response = self.session.get(
                url,
                headers=headers,
                proxies=proxies,
                timeout=self.config.DEFAULT_TIMEOUT,
                allow_redirects=True
            )
            
            response_time = time.time() - start_time
            self.throttler.on_success(response_time)
            
            # 处理响应
            response = self._handle_response(response, url)
            
            if response and response.status_code == 200:
                if proxies:
                    self.proxy_manager.mark_success(proxies)
                return response
            else:
                status = response.status_code if response else 'No Response'
                logger.warning(f"请求失败，状态码: {status}")
                
                if proxies:
                    self.proxy_manager.mark_failed(proxies)
                
                self.throttler.on_failure('blocked' if status == 403 else 'error')
                return None
                
        except requests.errors.RequestsError as e:
            err_str = str(e).lower()
            if 'timeout' in err_str:
                logger.warning(f"请求超时: {url}")
                self.throttler.on_failure('timeout')
            else:
                logger.warning(f"连接错误: {e}")
                self.throttler.on_failure('connection')
            if proxies:
                self.proxy_manager.mark_failed(proxies)
            return None
            
        except Exception as e:
            logger.error(f"请求异常: {e}")
            if proxies:
                self.proxy_manager.mark_failed(proxies)
            return None
    
    def get(self, url: str, headers: Optional[Dict] = None, **kwargs) -> Optional[requests.Response]:
        """
        发送GET请求（带反爬）
        
        Args:
            url: 请求URL
            headers: 自定义请求头（可选）
            **kwargs: 其他参数
        
        Returns:
            Response对象或None
        """
        # 限流等待
        self.throttler.wait_if_needed()
        
        # 生成请求头
        if headers is None:
            headers = self.headers_manager.get_headers()
        
        # 添加随机延迟
        delay = random.uniform(self.config.MIN_DELAY, self.config.MAX_DELAY)
        if delay > 0:
            time.sleep(delay)
        
        # 获取代理
        proxies = self._get_proxies()
        
        # 执行请求（带重试）
        def make_request():
            return self._execute_request(url, headers, proxies)
        
        response = self.retry_handler.execute_with_retry(make_request)
        
        return response
    
    def post(self, url: str, data: Optional[Dict] = None, headers: Optional[Dict] = None, **kwargs) -> Optional[requests.Response]:
        """发送POST请求"""
        # 类似GET的实现
        self.throttler.wait_if_needed()
        
        if headers is None:
            headers = self.headers_manager.get_headers()
        
        delay = random.uniform(self.config.MIN_DELAY, self.config.MAX_DELAY)
        if delay > 0:
            time.sleep(delay)
        
        proxies = self._get_proxies()
        
        try:
            start_time = time.time()
            response = self.session.post(
                url,
                data=data,
                headers=headers,
                proxies=proxies,
                timeout=self.config.DEFAULT_TIMEOUT,
                **kwargs
            )
            
            response_time = time.time() - start_time
            self.throttler.on_success(response_time)
            
            return response
            
        except Exception as e:
            logger.error(f"POST请求失败: {e}")
            if proxies:
                self.proxy_manager.mark_failed(proxies)
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'throttler': self.throttler.get_stats(),
            'proxy': self.proxy_manager.get_stats(),
            'session_active': self.session is not None
        }
    
    def close(self):
        """关闭会话"""
        if self.session:
            self.session.close()


# 简单工厂函数
def make_request(url: str, **kwargs) -> Optional[requests.Response]:
    """
    简单接口，兼容原有代码
    
    使用方式：
        from anti_scraping import make_request
        response = make_request("https://www.amazon.com/s?k=towel")
    """
    from .config import AntiScrapingConfig
    
    executor = RequestExecutor(AntiScrapingConfig())
    try:
        return executor.get(url, **kwargs)
    finally:
        executor.close()