#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网络配置模块
用于配置API调用的网络参数
"""

import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class NetworkConfig:
    """网络配置类"""
    
    def __init__(self):
        # 基本配置
        self.connect_timeout = 30
        self.read_timeout = 90
        self.max_retries = 3
        self.backoff_factor = 1
        self.verify_ssl = True
        
        # 代理配置（如果需要）
        self.proxies = self._get_proxy_config()
        
        # 重试策略
        self.retry_status_codes = [429, 500, 502, 503, 504]
        self.retry_methods = ["HEAD", "GET", "OPTIONS", "POST"]
    
    def _get_proxy_config(self):
        """获取代理配置"""
        proxies = {}
        
        # 从环境变量读取代理设置
        http_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
        https_proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
        
        if http_proxy:
            proxies['http'] = http_proxy
        if https_proxy:
            proxies['https'] = https_proxy
            
        return proxies if proxies else None
    
    def create_session(self):
        """创建配置好的requests session"""
        session = requests.Session()
        
        # 配置重试策略（兼容不同版本的urllib3）
        try:
            # 新版本urllib3使用allowed_methods
            retry_strategy = Retry(
                total=self.max_retries,
                status_forcelist=self.retry_status_codes,
                allowed_methods=self.retry_methods,
                backoff_factor=self.backoff_factor
            )
        except TypeError:
            # 旧版本urllib3使用method_whitelist
            retry_strategy = Retry(
                total=self.max_retries,
                status_forcelist=self.retry_status_codes,
                method_whitelist=self.retry_methods,
                backoff_factor=self.backoff_factor
            )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # 设置代理
        if self.proxies:
            session.proxies.update(self.proxies)
            print(f"使用代理: {self.proxies}")
        
        return session
    
    def get_timeout(self):
        """获取超时配置"""
        return (self.connect_timeout, self.read_timeout)
    
    def print_config(self):
        """打印当前配置"""
        print("网络配置:")
        print(f"  连接超时: {self.connect_timeout}秒")
        print(f"  读取超时: {self.read_timeout}秒")
        print(f"  最大重试: {self.max_retries}次")
        print(f"  退避因子: {self.backoff_factor}")
        print(f"  SSL验证: {self.verify_ssl}")
        print(f"  代理设置: {self.proxies or '无'}")

# 全局网络配置实例
network_config = NetworkConfig()

def test_network_connectivity():
    """测试网络连接"""
    print("测试网络连接...")
    
    test_urls = [
        "https://www.baidu.com",
        "https://api.deepseek.com",
        "https://www.google.com"
    ]
    
    session = network_config.create_session()
    
    for url in test_urls:
        try:
            response = session.get(url, timeout=network_config.get_timeout())
            print(f"✅ {url} - 状态码: {response.status_code}")
        except Exception as e:
            print(f"❌ {url} - 错误: {e}")

if __name__ == "__main__":
    network_config.print_config()
    test_network_connectivity()
