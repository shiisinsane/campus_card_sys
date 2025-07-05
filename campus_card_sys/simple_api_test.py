#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的DeepSeek API测试脚本
"""

import requests
import json
import time

# DeepSeek API配置
DEEPSEEK_API_KEY = "sk-2c5b003626704440a7721b08a849e382"
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

def test_simple_request():
    """测试简单的API请求"""
    print("=" * 50)
    print("测试DeepSeek API连接")
    print("=" * 50)
    
    headers = {
        'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
        'Content-Type': 'application/json',
        'User-Agent': 'CampusCardSystem/1.0'
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "user",
                "content": "请回复'测试成功'"
            }
        ],
        "max_tokens": 50,
        "temperature": 0.1
    }
    
    print(f"API URL: {DEEPSEEK_API_URL}")
    print(f"API Key: {DEEPSEEK_API_KEY[:20]}...")
    print("发送请求...")
    
    try:
        start_time = time.time()
        
        response = requests.post(
            DEEPSEEK_API_URL,
            headers=headers,
            json=data,
            timeout=(30, 90)  # 连接超时30秒，读取超时90秒
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"请求完成，耗时: {duration:.2f}秒")
        print(f"状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ API调用成功!")
            print(f"响应内容: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                print(f"AI回复: {content}")
            
            return True
        else:
            print(f"❌ API调用失败")
            print(f"错误响应: {response.text}")
            return False
            
    except requests.exceptions.Timeout as e:
        print(f"❌ 请求超时: {e}")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"❌ 连接错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return False

def test_network_basic():
    """测试基本网络连接"""
    print("\n" + "=" * 50)
    print("测试基本网络连接")
    print("=" * 50)
    
    try:
        # 测试能否访问DeepSeek主页
        response = requests.get("https://api.deepseek.com", timeout=30)
        print(f"✅ 可以访问DeepSeek API域名，状态码: {response.status_code}")
        return True
    except Exception as e:
        print(f"❌ 无法访问DeepSeek API域名: {e}")
        return False

def main():
    """主函数"""
    print("DeepSeek API 简化测试工具")
    
    # 测试网络连接
    network_ok = test_network_basic()
    
    if network_ok:
        # 测试API调用
        api_ok = test_simple_request()
        
        if api_ok:
            print("\n🎉 所有测试通过！DeepSeek API工作正常。")
        else:
            print("\n⚠️ API调用失败，请检查:")
            print("1. API密钥是否正确")
            print("2. 账户是否有余额")
            print("3. 是否超出了请求频率限制")
    else:
        print("\n⚠️ 网络连接失败，请检查:")
        print("1. 网络连接是否正常")
        print("2. 防火墙设置")
        print("3. 是否需要代理")

if __name__ == "__main__":
    main()
