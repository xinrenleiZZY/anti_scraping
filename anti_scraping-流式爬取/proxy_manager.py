# proxy_manager.py
"""
代理管理器
功能：管理代理IP的获取、轮询、失败标记
"""

import random
import time
import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ProxyManager:
    """代理管理器"""
    
    def __init__(self, config):
        self.config = config
        self.proxies = []
        self.current_index = 0
        self.failed_proxies = {}  # {proxy_hash: last_fail_time}
        self.proxy_stats = {}      # {proxy_hash: {success_count, fail_count}}
        
        self.load_proxies()
    
    def load_proxies(self):
        """加载代理列表"""
        # 方式1：从文件加载
        if self.config.PROXY_FILE and self._file_exists(self.config.PROXY_FILE):
            self._load_from_file()
        
        # 方式2：从API获取（需要自己实现）
        # self._fetch_from_api()
        
        # 方式3：手动添加测试代理
        if not self.proxies:
            self._add_test_proxies()
        
        logger.info(f"加载了 {len(self.proxies)} 个代理")
    
    def _file_exists(self, filepath: str) -> bool:
        """检查文件是否存在"""
        import os
        return os.path.exists(filepath)
    
    def _load_from_file(self):
        """从文件加载代理"""
        try:
            with open(self.config.PROXY_FILE, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        proxy = self._parse_proxy_line(line)
                        if proxy:
                            self.proxies.append(proxy)
        except Exception as e:
            logger.error(f"加载代理文件失败: {e}")
    
    def _parse_proxy_line(self, line: str) -> Optional[Dict[str, str]]:
        """解析代理行"""
        # 支持格式：
        # ip:port
        # http://ip:port
        # http://user:pass@ip:port
        
        line = line.strip()
        
        # 如果包含@，说明有认证
        if '@' in line:
            # 格式: protocol://user:pass@ip:port
            if '://' not in line:
                line = f"{self.config.PROXY_TYPE}://{line}"
            
            return {
                'http': line,
                'https': line
            }
        
        # 无认证代理
        if '://' not in line:
            line = f"{self.config.PROXY_TYPE}://{line}"
        
        return {
            'http': line,
            'https': line
        }
    
    def _add_test_proxies(self):
        """添加测试代理（仅用于开发测试）"""
        # 生产环境请使用真实代理
        pass
    
    def get_proxy(self) -> Optional[Dict[str, str]]:
        """获取一个可用的代理"""
        if not self.proxies:
            return None
        
        if not self.config.USE_PROXY:
            return None
        
        # 获取可用代理列表
        available = self._get_available_proxies()
        
        if not available:
            logger.warning("没有可用的代理")
            return None
        
        # 根据配置选择代理
        if self.config.PROXY_ROTATION == "random":
            proxy = random.choice(available)
        else:
            proxy = available[self.current_index % len(available)]
            self.current_index += 1
        
        return proxy
    
    def _get_available_proxies(self) -> List[Dict[str, str]]:
        """获取可用的代理列表（未失败的）"""
        available = []
        
        for proxy in self.proxies:
            proxy_hash = self._hash_proxy(proxy)
            
            # 检查是否在失败列表中
            if proxy_hash in self.failed_proxies:
                last_fail = self.failed_proxies[proxy_hash]
                # 5分钟后重试失败的代理
                if datetime.now() - last_fail > timedelta(minutes=5):
                    del self.failed_proxies[proxy_hash]
                else:
                    continue
            
            available.append(proxy)
        
        return available
    
    def mark_success(self, proxy: Dict[str, str]):
        """标记代理成功"""
        proxy_hash = self._hash_proxy(proxy)
        
        if proxy_hash not in self.proxy_stats:
            self.proxy_stats[proxy_hash] = {'success': 0, 'fail': 0}
        
        self.proxy_stats[proxy_hash]['success'] += 1
        
        # 如果之前标记为失败，清除
        if proxy_hash in self.failed_proxies:
            del self.failed_proxies[proxy_hash]
    
    def mark_failed(self, proxy: Dict[str, str]):
        """标记代理失败"""
        proxy_hash = self._hash_proxy(proxy)
        self.failed_proxies[proxy_hash] = datetime.now()
        
        if proxy_hash not in self.proxy_stats:
            self.proxy_stats[proxy_hash] = {'success': 0, 'fail': 0}
        
        self.proxy_stats[proxy_hash]['fail'] += 1
        
        logger.warning(f"代理失败: {proxy.get('http', 'unknown')}")
    
    def _hash_proxy(self, proxy: Dict[str, str]) -> str:
        """生成代理的唯一标识"""
        return proxy.get('http', '') + proxy.get('https', '')
    
    def get_stats(self) -> Dict:
        """获取代理统计信息"""
        return {
            'total': len(self.proxies),
            'available': len(self._get_available_proxies()),
            'failed': len(self.failed_proxies),
            'stats': self.proxy_stats
        }


# 简单代理测试函数
def test_proxy(proxy: Dict[str, str], test_url: str = "http://httpbin.org/ip") -> bool:
    """测试代理是否可用"""
    try:
        from curl_cffi import requests
        response = requests.get(test_url, proxies=proxy, timeout=10, impersonate="chrome120")
        return response.status_code == 200
    except:
        return False