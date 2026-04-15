# __init__.py
"""
反爬系统主入口
"""

from .config import AntiScrapingConfig, FastMode, SafeMode, AggressiveMode
from .request_executor import RequestExecutor, make_request
from .proxy_manager import ProxyManager
from .headers_manager import HeadersManager
from .throttler import RequestThrottler, AdaptiveThrottler
from .retry_handler import RetryHandler, retry_on_failure
from .captcha_solver import CaptchaDetector, CaptchaSolver

__all__ = [
    'AntiScrapingConfig',
    'FastMode',
    'SafeMode', 
    'AggressiveMode',
    'RequestExecutor',
    'make_request',
    'ProxyManager',
    'HeadersManager',
    'RequestThrottler',
    'AdaptiveThrottler',
    'RetryHandler',
    'retry_on_failure',
    'CaptchaDetector',
    'CaptchaSolver',
]

# 版本信息
__version__ = '1.0.0'