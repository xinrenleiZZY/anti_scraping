# throttler.py
"""
限流器
功能：控制请求频率，防止被封
"""

import time
import threading
from collections import deque
from datetime import datetime, timedelta
import logging
import random

logger = logging.getLogger(__name__)


class RequestThrottler:
    """请求限流器"""
    
    def __init__(self, config):
        self.config = config
        
        # 记录请求时间
        self.request_times_minute = deque()
        self.request_times_hour = deque()
        
        # 锁
        self.lock = threading.Lock()
        
        # 统计
        self.stats = {
            'total_requests': 0,
            'blocked_requests': 0,
            'last_request_time': None
        }
    
    def wait_if_needed(self):
        """如果需要，等待"""
        with self.lock:
            now = time.time()
            
            # 清理过期记录
            self._clean_old_records(now)
            
            # 检查分钟限制
            if len(self.request_times_minute) >= self.config.REQUESTS_PER_MINUTE:
                oldest = self.request_times_minute[0]
                wait_time = 60 - (now - oldest)
                if wait_time > 0:
                    logger.info(f"达到分钟限制，等待 {wait_time:.2f} 秒")
                    self.stats['blocked_requests'] += 1
                    time.sleep(wait_time)
                    return self.wait_if_needed()  # 递归检查
            
            # 检查小时限制
            if len(self.request_times_hour) >= self.config.REQUESTS_PER_HOUR:
                oldest = self.request_times_hour[0]
                wait_time = 3600 - (now - oldest)
                if wait_time > 0:
                    logger.info(f"达到小时限制，等待 {wait_time:.2f} 秒")
                    self.stats['blocked_requests'] += 1
                    time.sleep(wait_time)
                    return self.wait_if_needed()
            
            # 记录本次请求
            self.request_times_minute.append(now)
            self.request_times_hour.append(now)
            self.stats['total_requests'] += 1
            self.stats['last_request_time'] = now
    
    def _clean_old_records(self, now: float):
        """清理过期记录"""
        # 清理1分钟前的记录
        while self.request_times_minute and now - self.request_times_minute[0] > 60:
            self.request_times_minute.popleft()
        
        # 清理1小时前的记录
        while self.request_times_hour and now - self.request_times_hour[0] > 3600:
            self.request_times_hour.popleft()
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        with self.lock:
            now = time.time()
            self._clean_old_records(now)
            
            return {
                **self.stats,
                'requests_last_minute': len(self.request_times_minute),
                'requests_last_hour': len(self.request_times_hour),
            }


class AdaptiveThrottler(RequestThrottler):
    """自适应限流器 - 根据响应自动调整频率"""
    
    def __init__(self, config):
        super().__init__(config)
        self.consecutive_failures = 0
        self.current_delay = config.MIN_DELAY
        self.last_response_time = None
    
    def on_success(self, response_time: float):
        """请求成功时的处理"""
        self.consecutive_failures = 0
        
        # 逐渐减少延迟
        if self.current_delay > self.config.MIN_DELAY:
            self.current_delay = max(self.config.MIN_DELAY, self.current_delay * 0.9)
        
        self.last_response_time = response_time
    
    def on_failure(self, error_type: str):
        """请求失败时的处理"""
        self.consecutive_failures += 1
        
        # 根据失败类型增加延迟
        if error_type == 'captcha':
            self.current_delay = min(60, self.current_delay * 3)
        elif error_type == 'blocked':
            self.current_delay = min(120, self.current_delay * 2)
        else:
            self.current_delay = min(30, self.current_delay * 1.5)
        
        logger.warning(f"请求失败 ({error_type})，延迟调整为 {self.current_delay:.2f} 秒")
    
    def wait_if_needed(self):
        """等待（使用自适应延迟）"""
        if self.current_delay > 0:
            # 添加随机抖动
            delay = self.current_delay * random.uniform(0.8, 1.2)
            time.sleep(delay)
        
        super().wait_if_needed()