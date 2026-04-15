# retry_handler.py
"""
重试处理器
功能：处理请求失败重试、指数退避
"""

import time
import random
import logging
from functools import wraps
from typing import Callable, Optional, Any

logger = logging.getLogger(__name__)


class RetryHandler:
    """重试处理器"""
    
    def __init__(self, config):
        self.config = config
        self.retry_count = {}
    
    def should_retry(self, error: Exception, attempt: int) -> tuple[bool, float]:
        """
        判断是否应该重试
        
        Returns:
            (是否重试, 等待秒数)
        """
        if attempt >= self.config.MAX_RETRIES:
            return False, 0
        
        # 根据错误类型判断
        error_str = str(error).lower()
        
        # 这些错误不应该重试
        no_retry_errors = [
            '404', '403', '401',  # 客户端错误
            'invalid', 'bad request'
        ]
        
        for err in no_retry_errors:
            if err in error_str:
                return False, 0
        
        # 计算等待时间（指数退避 + 随机抖动）
        wait_time = self._calculate_wait_time(attempt, error_str)
        
        return True, wait_time
    
    def _calculate_wait_time(self, attempt: int, error_str: str) -> float:
        """计算等待时间"""
        base_wait = 2 ** attempt  # 指数: 2, 4, 8, 16
        
        # 根据错误类型增加等待
        if 'timeout' in error_str:
            base_wait *= 1.5
        elif 'captcha' in error_str:
            base_wait *= 3
        elif 'blocked' in error_str or 'ban' in error_str:
            base_wait *= 5
        
        # 添加随机抖动
        jitter = random.uniform(0.8, 1.2)
        
        return base_wait * jitter
    
    def execute_with_retry(self, func: Callable, *args, **kwargs) -> Optional[Any]:
        """执行函数并自动重试"""
        for attempt in range(1, self.config.MAX_RETRIES + 1):
            try:
                return func(*args, **kwargs)
                
            except Exception as e:
                should_retry, wait_time = self.should_retry(e, attempt)
                
                if not should_retry:
                    logger.error(f"函数执行失败，不重试: {e}")
                    raise
                
                logger.warning(f"第 {attempt}/{self.config.MAX_RETRIES} 次重试，等待 {wait_time:.2f} 秒: {e}")
                time.sleep(wait_time)
        
        return None


def retry_on_failure(max_retries: int = 3, backoff_factor: float = 2):
    """重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries:
                        raise
                    
                    wait_time = backoff_factor ** attempt * random.uniform(0.8, 1.2)
                    logger.warning(f"重试 {attempt}/{max_retries}，等待 {wait_time:.2f}s: {e}")
                    time.sleep(wait_time)
            return None
        return wrapper
    return decorator