#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复urllib3版本兼容性问题的工具
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def create_retry_strategy(total=3, backoff_factor=1, status_forcelist=None):
    """创建兼容不同urllib3版本的重试策略"""
    if status_forcelist is None:
        status_forcelist = [429, 500, 502, 503, 504]
    
    methods = ["HEAD", "GET", "OPTIONS", "POST"]
    
    # 检测urllib3版本并使用正确的参数名
    try:
        # 尝试使用新版本的参数名
        retry_strategy = Retry(
            total=total,
            status_forcelist=status_forcelist,
            allowed_methods=methods,
            backoff_factor=backoff_factor
        )
        print("✅ 使用新版urllib3参数: allowed_methods")
        return retry_strategy
    except TypeError as e:
        if "allowed_methods" in str(e):
            # 如果新参数不支持，使用旧参数
            try:
                retry_strategy = Retry(
                    total=total,
                    status_forcelist=status_forcelist,
                    method_whitelist=methods,
                    backoff_factor=backoff_factor
                )
                print("✅ 使用旧版urllib3参数: method_whitelist")
                return retry_strategy
            except TypeError:
                # 如果都不支持，创建最基本的重试策略
                retry_strategy = Retry(
                    total=total,
                    status_forcelist=status_forcelist,
                    backoff_factor=backoff_factor
                )
                print("⚠️ 使用基础重试策略（无方法限制）")
                return retry_strategy
        else:
            raise e

def test_retry_compatibility():
    """测试重试策略兼容性"""
    print("测试urllib3重试策略兼容性...")
    
    try:
        retry_strategy = create_retry_strategy()
        
        # 创建session并应用重试策略
        session = requests.Session()
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        print("✅ 重试策略创建成功")
        
        # 测试实际请求
        print("测试实际HTTP请求...")
        response = session.get("https://httpbin.org/status/200", timeout=10)
        print(f"✅ 请求成功，状态码: {response.status_code}")
        
        return True
        
    except Exception as e:
        print(f"❌ 重试策略测试失败: {e}")
        return False

def get_package_versions():
    """获取相关包的版本信息"""
    print("\n包版本信息:")
    
    try:
        import requests
        print(f"requests: {requests.__version__}")
    except:
        print("requests: 未安装")
    
    try:
        import urllib3
        print(f"urllib3: {urllib3.__version__}")
    except:
        print("urllib3: 未安装")
    
    try:
        from urllib3.util.retry import Retry
        print("urllib3.util.retry: 可用")
    except:
        print("urllib3.util.retry: 不可用")

if __name__ == "__main__":
    print("=" * 50)
    print("urllib3兼容性检查和修复工具")
    print("=" * 50)
    
    get_package_versions()
    print()
    
    success = test_retry_compatibility()
    
    if success:
        print("\n🎉 兼容性测试通过！")
        print("您的环境支持增强的重试机制。")
    else:
        print("\n⚠️ 兼容性测试失败")
        print("建议更新urllib3版本：pip install --upgrade urllib3")
