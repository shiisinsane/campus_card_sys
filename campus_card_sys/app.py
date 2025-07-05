# app.py
from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from models import db, User, CampusCard, ForumPost, Reward
from datetime import datetime, timedelta
import re
import os
import uuid
import json
import requests
import threading
import time
import hashlib
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///campus_card.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 添加Flask配置以提高稳定性
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
    'connect_args': {'timeout': 20}
}
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # 1年
app.config['PERMANENT_SESSION_LIFETIME'] = 3600     # 1小时



# 图片上传配置
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# 确保上传目录存在
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# DeepSeek API配置
DEEPSEEK_API_KEY = "sk-2c5b003626704440a7721b08a849e382"  # 您的DeepSeek API密钥
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# 网络配置
NETWORK_CONFIG = {
    'connect_timeout': 30,  # 连接超时
    'read_timeout': 90,     # 读取超时
    'max_retries': 3,       # 最大重试次数
    'backoff_factor': 1,    # 退避因子
    'verify_ssl': True      # SSL验证
}

# 加载地点数据库
def load_location_database():
    """加载地点数据库"""
    try:
        with open('location_database.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载地点数据库失败: {e}")
        return {}

LOCATION_DB = load_location_database()

# ==================== 缓存系统 ====================

# 查询结果缓存
QUERY_CACHE = {}
CACHE_EXPIRY_TIME = 7200  # 缓存2小时，增加稳定性

def get_cache_key(user_input, return_best_match=False):
    """生成缓存键"""
    cache_data = f"{user_input.lower().strip()}_{return_best_match}"
    return hashlib.md5(cache_data.encode('utf-8')).hexdigest()

def get_from_cache(cache_key):
    """从缓存获取结果"""
    if cache_key in QUERY_CACHE:
        cached_data = QUERY_CACHE[cache_key]
        # 检查是否过期
        if time.time() - cached_data['timestamp'] < CACHE_EXPIRY_TIME:
            return cached_data['result']
        else:
            # 删除过期缓存
            del QUERY_CACHE[cache_key]
    return None

def save_to_cache(cache_key, result):
    """保存结果到缓存"""
    QUERY_CACHE[cache_key] = {
        'result': result,
        'timestamp': time.time()
    }

def clear_expired_cache():
    """清理过期缓存"""
    current_time = time.time()
    expired_keys = []
    for key, data in QUERY_CACHE.items():
        if current_time - data['timestamp'] >= CACHE_EXPIRY_TIME:
            expired_keys.append(key)

    for key in expired_keys:
        del QUERY_CACHE[key]

db.init_app(app)

# 添加CORS支持
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

def create_compatible_retry_strategy(total=3, backoff_factor=1, status_forcelist=None):
    """创建兼容不同urllib3版本的重试策略"""
    from urllib3.util.retry import Retry

    if status_forcelist is None:
        status_forcelist = [429, 500, 502, 503, 504]

    methods = ["HEAD", "GET", "OPTIONS", "POST"]

    try:
        # 尝试使用新版本的参数名
        return Retry(
            total=total,
            status_forcelist=status_forcelist,
            allowed_methods=methods,
            backoff_factor=backoff_factor
        )
    except TypeError:
        # 使用旧版本的参数名
        try:
            return Retry(
                total=total,
                status_forcelist=status_forcelist,
                method_whitelist=methods,
                backoff_factor=backoff_factor
            )
        except TypeError:
            # 最基本的重试策略
            return Retry(
                total=total,
                status_forcelist=status_forcelist,
                backoff_factor=backoff_factor
            )

def call_deepseek_api(prompt, system_message=None, max_retries=3):
    """调用DeepSeek API - 增强版本，包含重试机制和更好的错误处理"""
    headers = {
        'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
        'Content-Type': 'application/json',
        'User-Agent': 'CampusCardSystem/1.0',
        'Accept': 'application/json',
        'Connection': 'keep-alive'
    }

    # 默认系统消息用于地点识别
    if system_message is None:
        system_message = "你是一个校园地点识别专家。请从用户输入的文本中识别出地点名称，并返回JSON格式的结果。"

    data = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": system_message
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.1,
        "max_tokens": 500,
        "stream": False
    }

    # 创建session以复用连接
    session = requests.Session()
    session.headers.update(headers)

    # 配置适配器以提高连接稳定性
    from requests.adapters import HTTPAdapter

    # 使用兼容的重试策略
    retry_strategy = create_compatible_retry_strategy(
        total=max_retries,
        backoff_factor=NETWORK_CONFIG['backoff_factor'],
        status_forcelist=[429, 500, 502, 503, 504]
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # 设置代理（如果环境变量中有配置）
    import os
    proxies = {}
    http_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
    https_proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    if http_proxy:
        proxies['http'] = http_proxy
    if https_proxy:
        proxies['https'] = https_proxy
    if proxies:
        session.proxies.update(proxies)
        print(f"使用代理设置: {proxies}")

    for attempt in range(1, max_retries + 1):
        try:
            print(f"DeepSeek API调用尝试 {attempt}/{max_retries}")

            # 使用配置的超时时间：(连接超时, 读取超时)
            timeout = (NETWORK_CONFIG['connect_timeout'], NETWORK_CONFIG['read_timeout'])
            response = session.post(
                DEEPSEEK_API_URL,
                json=data,
                timeout=timeout,
                verify=NETWORK_CONFIG['verify_ssl']
            )

            print(f"API响应状态码: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                print(f"API调用成功，返回内容长度: {len(content)}")
                return content
            elif response.status_code == 401:
                print(f"DeepSeek API认证失败: API密钥可能无效或已过期")
                return None
            elif response.status_code == 429:
                print(f"DeepSeek API请求频率限制: {response.text}")
                if attempt < max_retries:
                    wait_time = 2 ** attempt  # 指数退避
                    print(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                    continue
                return None
            elif response.status_code >= 500:
                print(f"DeepSeek API服务器错误: {response.status_code}, {response.text}")
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    print(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                    continue
                return None
            else:
                print(f"DeepSeek API未知错误: {response.status_code}, {response.text}")
                return None

        except requests.exceptions.Timeout as e:
            print(f"DeepSeek API超时错误 (尝试 {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                wait_time = 2 ** attempt
                print(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
                continue
            print("所有重试都超时，API调用失败")
            return None

        except requests.exceptions.ConnectionError as e:
            print(f"DeepSeek API连接错误 (尝试 {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                wait_time = 2 ** attempt
                print(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
                continue
            print("所有重试都连接失败，API调用失败")
            return None

        except requests.exceptions.RequestException as e:
            print(f"DeepSeek API请求异常 (尝试 {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                wait_time = 2 ** attempt
                print(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
                continue
            return None

        except Exception as e:
            print(f"DeepSeek API未知异常 (尝试 {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                wait_time = 2 ** attempt
                print(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
                continue
            return None

    print("所有重试都失败，API调用最终失败")
    return None

# ==================== 模块A: 地点提取功能模块 ====================

def extract_location_from_text(user_input, return_best_match=False):
    """
    模块A: 从用户输入文本中提取校园地点

    Args:
        user_input (str): 用户输入的文本
        return_best_match (bool): 是否只返回最佳匹配的单个地点

    Returns:
        dict: 包含提取结果的字典
        - 如果 return_best_match=False: 返回所有找到的地点列表
        - 如果 return_best_match=True: 返回最佳匹配的单个地点
    """
    # 清理过期缓存
    clear_expired_cache()

    # 检查缓存
    cache_key = get_cache_key(user_input, return_best_match)
    cached_result = get_from_cache(cache_key)
    if cached_result:
        print(f"缓存命中: {user_input} -> {cached_result}")
        return cached_result

    # 首先尝试快速关键词匹配
    fallback_result = fallback_location_parsing(user_input, return_best_match)

    # 如果关键词匹配有高置信度结果，直接返回，避免AI调用
    if return_best_match:
        if fallback_result.get('confidence', 0) >= 0.9:
            save_to_cache(cache_key, fallback_result)
            print(f"快速匹配: {user_input} -> {fallback_result}")
            return fallback_result
    else:
        if fallback_result.get('confidence', 0) >= 0.8 and fallback_result.get('found_locations'):
            save_to_cache(cache_key, fallback_result)
            print(f"快速匹配: {user_input} -> {fallback_result}")
            return fallback_result

    # 构建提示词，包含所有可能的地点名称
    location_names = [loc_data['name'] for loc_data in LOCATION_DB.values()]
    location_list = "、".join(location_names)

    if return_best_match:
        prompt = f"""
请从以下用户输入中识别出最可能的校园地点名称：
用户输入："{user_input}"

校园中的地点包括：{location_list}

请返回JSON格式的结果，只返回最可能的一个地点：
{{
    "best_match": "地点名称",
    "confidence": 0.9,
    "reasoning": "识别理由"
}}

如果没有找到匹配的地点，请返回：
{{
    "best_match": null,
    "confidence": 0.0,
    "reasoning": "未找到匹配的校园地点"
}}
"""
    else:
        prompt = f"""
请从以下用户输入中识别出校园地点名称，并根据用户原文的语义相关性对地点进行排序：
用户输入："{user_input}"

校园中的地点包括：{location_list}

请仔细分析用户输入的语义，如果识别出多个地点，请按照与用户原文语义最相关的顺序排列。
例如：如果用户说"东南门"，而你识别出了"南门"和"东南门"，那么"东南门"应该排在前面，因为它与用户原文完全匹配。

请返回JSON格式的结果，格式如下：
{{
    "found_locations": ["最相关地点", "次相关地点"],
    "confidence": 0.9,
    "reasoning": "识别理由和排序依据"
}}

如果没有找到匹配的地点，请返回：
{{
    "found_locations": [],
    "confidence": 0.0,
    "reasoning": "未找到匹配的校园地点"
}}
"""

    response = call_deepseek_api(prompt)
    if response:
        try:
            # 尝试解析JSON响应
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                # 保存到缓存
                save_to_cache(cache_key, result)
                print(f"AI分析完成: {user_input} -> {result}")
                return result
        except Exception as e:
            print(f"解析DeepSeek响应失败: {e}")

    # 如果API调用失败，使用简单的关键词匹配作为备选方案
    final_result = fallback_location_parsing(user_input, return_best_match)
    save_to_cache(cache_key, final_result)
    return final_result

def parse_location_from_text(user_input):
    """
    兼容性函数：保持原有智能地点查询的接口不变
    """
    return extract_location_from_text(user_input, return_best_match=False)

# ==================== 异步处理模块 ====================

def async_location_analysis_worker(card_id, found_location):
    """
    异步工作函数：分析地点并更新数据库
    """
    try:
        print(f"开始异步分析地点: 卡片ID={card_id}, 地点='{found_location}'")

        # 使用模块A分析地点
        location_analysis = extract_location_from_text(found_location, return_best_match=True)

        if location_analysis.get('best_match') and location_analysis.get('confidence', 0) > 0.5:
            select_loc = location_analysis['best_match']
            confidence = location_analysis.get('confidence', 0)

            print(f"AI分析完成: '{found_location}' -> '{select_loc}' (置信度: {confidence:.2f})")

            # 更新数据库
            with app.app_context():
                card = CampusCard.query.get(card_id)
                if card:
                    card.select_loc = select_loc
                    db.session.commit()
                    print(f"数据库更新成功: 卡片ID={card_id}, select_loc='{select_loc}'")
                else:
                    print(f"未找到卡片: ID={card_id}")
        else:
            print(f"AI分析置信度过低或未找到匹配: {location_analysis}")

    except Exception as e:
        print(f"异步地点分析失败: 卡片ID={card_id}, 错误={e}")

def start_async_location_analysis(card_id, found_location):
    """
    启动异步地点分析任务
    """
    try:
        # 创建并启动后台线程，增加错误处理
        thread = threading.Thread(
            target=safe_async_location_analysis_worker,
            args=(card_id, found_location),
            daemon=True  # 设置为守护线程，主程序退出时自动结束
        )
        thread.start()
        print(f"异步分析任务已启动: 卡片ID={card_id}")
    except Exception as e:
        print(f"启动异步任务失败: {e}")

def safe_async_location_analysis_worker(card_id, found_location):
    """
    安全的异步工作函数：带有完整错误处理
    """
    try:
        async_location_analysis_worker(card_id, found_location)
    except Exception as e:
        print(f"异步任务执行失败: 卡片ID={card_id}, 错误={e}")
        # 记录错误但不影响主服务

def calculate_semantic_relevance(user_input, location_name):
    """
    计算用户输入与地点名称的语义相关性得分
    返回值范围：0.0 - 1.0，值越高表示相关性越强
    """
    user_input_clean = user_input.strip().lower()
    location_clean = location_name.strip().lower()

    # 1. 完全匹配 - 最高分
    if location_clean == user_input_clean:
        return 1.0

    # 2. 地点名称完全包含在用户输入中
    if location_clean in user_input_clean:
        # 计算匹配长度占用户输入的比例
        match_ratio = len(location_clean) / len(user_input_clean)
        return 0.9 + (match_ratio * 0.1)  # 0.9-1.0之间

    # 3. 用户输入完全包含在地点名称中（如用户说"南门"，地点是"东南门"）
    if user_input_clean in location_clean:
        # 计算匹配长度占地点名称的比例
        match_ratio = len(user_input_clean) / len(location_clean)
        return 0.7 + (match_ratio * 0.2)  # 0.7-0.9之间

    # 4. 部分字符匹配
    common_chars = set(user_input_clean) & set(location_clean)
    if common_chars:
        # 计算共同字符的比例
        common_ratio = len(common_chars) / max(len(set(user_input_clean)), len(set(location_clean)))
        return 0.3 + (common_ratio * 0.4)  # 0.3-0.7之间

    # 5. 无匹配
    return 0.0

def fallback_location_parsing(user_input, return_best_match=False):
    """备选的地点解析方法（关键词匹配）"""
    found_locations = []
    user_input_lower = user_input.lower()

    # 记录匹配的地点和匹配度
    matches = []

    for loc_key, loc_data in LOCATION_DB.items():
        location_name = loc_data['name']
        # 检查地点名称是否在用户输入中
        if location_name in user_input:
            # 计算语义相关性得分
            semantic_score = calculate_semantic_relevance(user_input, location_name)
            matches.append((location_name, semantic_score))
            found_locations.append(location_name)
        elif loc_key in user_input_lower:
            # 关键词匹配，中等优先级
            semantic_score = calculate_semantic_relevance(user_input, location_name) * 0.8
            matches.append((location_name, semantic_score))
            found_locations.append(location_name)

    if return_best_match:
        if matches:
            # 按语义相关性得分排序，返回最佳匹配
            matches.sort(key=lambda x: x[1], reverse=True)
            best_location = matches[0][0]
            confidence = matches[0][1]
            return {
                "best_match": best_location,
                "confidence": confidence,
                "reasoning": "使用语义相关性匹配识别"
            }
        else:
            return {
                "best_match": None,
                "confidence": 0.0,
                "reasoning": "未找到匹配的校园地点"
            }
    else:
        # 按语义相关性得分排序
        matches.sort(key=lambda x: x[1], reverse=True)
        # 重新构建按相关性排序的地点列表
        sorted_locations = [match[0] for match in matches]

        return {
            "found_locations": sorted_locations,
            "confidence": 0.8 if sorted_locations else 0.0,
            "reasoning": "使用语义相关性匹配识别，按相关性排序" if sorted_locations else "未找到匹配的校园地点"
        }

def calculate_distance(x1, y1, x2, y2):
    """计算两点之间的曼哈顿距离（街区距离）"""
    return abs(x2 - x1) + abs(y2 - y1)

def find_nearest_lost_and_found(location_name):
    """找到距离指定地点最近的招领点"""
    # 首先找到指定地点的坐标
    target_location = None
    for loc_key, loc_data in LOCATION_DB.items():
        if loc_data['name'] == location_name and loc_data['type'] == 'building':
            target_location = loc_data
            break

    if not target_location:
        return None

    # 找到所有招领点
    lost_and_found_points = []
    for loc_key, loc_data in LOCATION_DB.items():
        if loc_data['type'] == 'lost_and_found':
            distance = calculate_distance(
                target_location['x'], target_location['y'],
                loc_data['x'], loc_data['y']
            )
            lost_and_found_points.append({
                'name': loc_data['name'],
                'x': loc_data['x'],
                'y': loc_data['y'],
                'distance': distance
            })

    # 按距离排序，返回最近的
    if lost_and_found_points:
        lost_and_found_points.sort(key=lambda x: x['distance'])
        return lost_and_found_points[0]

    return None

def analyze_nearest_lost_and_found_with_ai(location_name, nearest_point):
    """使用AI分析最近的招领点信息"""
    if not nearest_point:
        return "未找到附近的招领点"

    prompt = f"""
请为用户提供关于校园招领点的友好建议：

用户询问的地点：{location_name}
最近的招领点：{nearest_point['name']}
距离：{nearest_point['distance']:.1f}个单位

请用友好、实用的语言为用户提供建议，包括：
1. 确认最近的招领点位置
2. 简单的路线建议
3. 其他实用提示

请用中文回复，语言要亲切友好，但不要加过多语气词。特别注意，要以向捡卡者提供信息的角度给出建议，不要以向丢卡者提供信息的角度给建议。另外，不要说“建议带上学生证，方便登记认领”，因为查询者是因为丢卡而来的;
也不要说类似“沿着学府路往东直行约500米就能到达”这种带有其他地点的话，最好能说一下步行时间，比如“从管院到梧桐苑，步行5-7分钟就能到。”
"""

    # 使用专门的系统消息来生成友好建议
    system_message = "你是一个友好的校园助手，专门为学生提供实用的校园服务建议。请用亲切、友好的语言回复，提供具体实用的建议。"

    response = call_deepseek_api(prompt, system_message)
    if response:
        # 清理可能的JSON格式或其他格式化字符
        cleaned_response = response.strip()
        # 如果响应包含JSON格式，尝试提取实际内容
        if cleaned_response.startswith('{') and cleaned_response.endswith('}'):
            try:
                import json
                parsed = json.loads(cleaned_response)
                # 如果是JSON格式，尝试提取建议内容
                if isinstance(parsed, dict):
                    if 'advice' in parsed:
                        return parsed['advice']
                    elif 'suggestion' in parsed:
                        return parsed['suggestion']
                    elif 'message' in parsed:
                        return parsed['message']
                    else:
                        # 如果没有找到预期的字段，返回备用建议
                        return f"最近的招领点是{nearest_point['name']}，距离约{nearest_point['distance']:.1f}个单位。建议您前往该地点查看是否有您丢失的物品。"
            except:
                # JSON解析失败，返回备用建议
                return f"最近的招领点是{nearest_point['name']}，距离约{nearest_point['distance']:.1f}个单位。建议您前往该地点查看是否有您丢失的物品。"

        return cleaned_response
    else:
        return f"最近的招领点是{nearest_point['name']}，距离约{nearest_point['distance']:.1f}个单位。建议您前往该地点查看是否有您丢失的物品。"

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 添加健康检查端点
@app.route('/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    try:
        # 检查数据库连接
        db.session.execute('SELECT 1')
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'database': 'connected'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }), 500

# 添加API测试端点
@app.route('/test_deepseek_api', methods=['GET'])
def test_deepseek_api():
    """测试DeepSeek API连接"""
    try:
        print("开始测试DeepSeek API连接...")

        # 简单的测试调用
        test_prompt = "请回复'测试成功'"
        test_system = "你是一个测试助手，请简短回复。"

        result = call_deepseek_api(test_prompt, test_system)

        if result:
            return jsonify({
                'status': 'success',
                'message': 'DeepSeek API连接正常',
                'api_response': result,
                'timestamp': datetime.now().isoformat()
            }), 200
        else:
            return jsonify({
                'status': 'failed',
                'message': 'DeepSeek API调用失败',
                'timestamp': datetime.now().isoformat()
            }), 500

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'测试过程中发生错误: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

# 添加连接保持端点
@app.route('/ping', methods=['GET'])
def ping():
    """简单的ping端点，用于保持连接"""
    return jsonify({'pong': True, 'timestamp': time.time()}), 200

@app.route('/upload_image', methods=['POST'])
def upload_image():
    """上传图片"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        # 生成唯一文件名
        filename = secure_filename(file.filename)
        file_extension = filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{file_extension}"

        # 保存文件
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)

        # 返回文件URL
        file_url = f"/uploads/{unique_filename}"
        return jsonify({
            'message': 'File uploaded successfully',
            'file_url': file_url
        }), 200

    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """提供上传的图片文件"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/register', methods=['POST'])
def register():
    """用户注册"""
    data = request.json
    student_id = data.get('student_id')
    full_name = data.get('full_name')
    password = data.get('password')
    
    if not all([student_id, full_name, password]):
        return jsonify({'error': 'Missing parameters'}), 400
    
    if User.query.filter_by(student_id=student_id).first():
        return jsonify({'error': 'User already exists'}), 409
        
    new_user = User(student_id=student_id, full_name=full_name, password=password)
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({'message': 'User registered successfully', 'user_id': new_user.id}), 201

@app.route('/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.json
    student_id = data.get('student_id')
    full_name = data.get('full_name')
    password = data.get('password')

    if not all([student_id, full_name, password]):
        return jsonify({'error': 'Missing parameters'}), 400

    user = User.query.filter_by(
        student_id=student_id,
        full_name=full_name,
        password=password
    ).first()

    if user:
        return jsonify({
            'message': 'Login successful',
            'user_id': user.id,
            'student_id': user.student_id,
            'full_name': user.full_name,
            'points': user.points
        }), 200
    else:
        return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/report_card', methods=['POST'])
def report_found_card():
    """报告捡到校园卡"""
    # 支持JSON和form-data两种格式
    if request.is_json:
        data = request.json
        card_number = data.get('card_number')
        found_location = data.get('found_location', '')
        handler_option = data.get('handler_option')
        contact = data.get('contact', '')
        photo_url = data.get('photo_url', '')
        current_user_id = data.get('current_user_id')
        current_user_name = data.get('current_user_name')
    else:
        # form-data格式（支持文件上传）
        card_number = request.form.get('card_number')
        found_location = request.form.get('found_location', '')
        handler_option = request.form.get('handler_option')
        contact = request.form.get('contact', '')
        photo_url = ''
        current_user_id = request.form.get('current_user_id')
        current_user_name = request.form.get('current_user_name')

        # 处理图片上传
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename != '' and allowed_file(file.filename):
                # 生成唯一文件名
                filename = secure_filename(file.filename)
                file_extension = filename.rsplit('.', 1)[1].lower()
                unique_filename = f"{uuid.uuid4().hex}.{file_extension}"

                # 保存文件
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(file_path)

                # 设置photo_url
                photo_url = f"/uploads/{unique_filename}"

    # 转换handler_option为整数
    try:
        handler_option = int(handler_option) if handler_option else None
    except (ValueError, TypeError):
        handler_option = None

    if not card_number or handler_option not in [1, 2]:
        return jsonify({'error': 'Invalid parameters'}), 400

    # 验证必填字段
    if handler_option == 1:
        # 选择自行联系，必须提供联系方式
        if not contact or not contact.strip():
            return jsonify({'error': 'Contact information is required for self-contact option'}), 400
    elif handler_option == 2:
        # 选择放置指定地点，必须提供拾取点信息
        if not contact or not contact.strip():
            return jsonify({'error': 'Pickup location is required for location placement option'}), 400
        # 验证拾取点是否在允许的选项中
        allowed_locations = ['图书馆', '梧桐苑', '康桥苑', '中一楼']
        if contact.strip() not in allowed_locations:
            return jsonify({'error': 'Invalid pickup location'}), 400
    
    student_id = card_number  # 假设卡号就是学号

    # 检查卡是否已在系统中
    card = CampusCard.query.filter_by(card_number=card_number).first()

    if card:
        # 更新现有卡片状态
        card.status = 'found'
        card.found_location = found_location
        card.handler_option = handler_option
        # 无论选择哪种处理方式，都将信息存储到contact字段
        card.contact = contact.strip() if contact else None
        card.found_time = datetime.now()
        card.student_id = student_id  # 更新学生ID
        card.photo_url = photo_url
        # select_loc暂时为空，稍后异步更新
        card.select_loc = None
    else:
        # 创建新记录
        card = CampusCard(
            card_number=card_number,
            student_id=student_id,
            status='found',
            found_location=found_location,
            handler_option=handler_option,
            # 无论选择哪种处理方式，都将信息存储到contact字段
            contact=contact.strip() if contact else None,
            photo_url=photo_url,
            found_time=datetime.now(),
            select_loc=None  # 暂时为空，稍后异步更新
        )
    
    db.session.add(card)
    db.session.commit()

    # 获取卡片ID用于异步处理
    card_id = card.id

    # 自动匹配失主
    if student_id:
        owner = User.query.filter_by(student_id=student_id).first()
        if owner:
            card.student_id = student_id
            card.is_matched = True
            db.session.commit()

            # 启动异步AI分析任务
            if found_location and found_location.strip():
                start_async_location_analysis(card_id, found_location.strip())

            # 为当前登录用户增加积分奖励
            points_awarded = 0
            if current_user_id and current_user_name:
                try:
                    current_user_id = int(current_user_id)
                    points_awarded = award_points_for_current_user(current_user_id, current_user_name)
                except (ValueError, TypeError):
                    print(f"无效的用户ID: {current_user_id}")

            if points_awarded > 0:
                return jsonify({
                    'message': f'Card reported and matched to owner! 感谢您的善举，已为您增加{points_awarded}个积分！',
                    'owner_masked': mask_info(owner.full_name, owner.student_id),
                    'points_awarded': points_awarded
                }), 200
            else:
                return jsonify({
                    'message': 'Card reported and matched to owner',
                    'owner_masked': mask_info(owner.full_name, owner.student_id)
                }), 200

    # 启动异步AI分析任务
    if found_location and found_location.strip():
        start_async_location_analysis(card_id, found_location.strip())

    # 为当前登录用户增加积分奖励
    points_awarded = 0
    if current_user_id and current_user_name:
        try:
            current_user_id = int(current_user_id)
            points_awarded = award_points_for_current_user(current_user_id, current_user_name)
        except (ValueError, TypeError):
            print(f"无效的用户ID: {current_user_id}")

    if points_awarded > 0:
        return jsonify({
            'message': f'Card reported successfully! 感谢您的善举，已为您增加{points_awarded}个积分！',
            'points_awarded': points_awarded
        }), 200
    else:
        return jsonify({'message': 'Card reported successfully'}), 200

# def extract_student_id(card_number):
#     """从卡号中提取学号（示例逻辑）"""
#     # 实际实现根据学校卡号规则
#     if re.match(r'^\d{10}$', card_number):
#         return card_number[:6]  # 取前6位作为学号
#     return None

def mask_info(full_name, student_id):
    """信息脱敏处理"""
    masked_name = full_name[0] + '*' * (len(full_name) - 1) if len(full_name) > 1 else '*'
    masked_id = student_id[:2] + '****' + student_id[-2:] if len(student_id) > 4 else '****'
    return {'name': masked_name, 'student_id': masked_id}

def get_half_month_ago():
    """获取半个月前的时间"""
    return datetime.now() - timedelta(days=15)

def is_within_half_month(found_time):
    """检查时间是否在最近半个月内"""
    if not found_time:
        return False
    half_month_ago = get_half_month_ago()
    return found_time >= half_month_ago

def get_real_name_by_student_id(student_id):
    """根据学号获取真实姓名，如果找不到用户则返回None"""
    try:
        # 在user表中查找对应的用户
        user = User.query.filter_by(student_id=student_id).first()
        if user and user.full_name:
            # 找到用户，返回完整的真实姓名
            return user.full_name
        else:
            # 未找到用户，返回None
            return None
    except Exception as e:
        print(f"查询用户姓名失败: {e}")
        return None

def award_points_for_current_user(user_id, user_name):
    """为当前登录用户增加积分奖励"""
    try:
        # 根据用户ID查找用户（更准确）
        user = User.query.get(user_id)
        if user:
            # 验证用户名是否匹配（额外安全检查）
            if user.full_name == user_name:
                # 增加10个积分
                user.points += 10
                db.session.commit()
                print(f"积分奖励成功: 用户 {user_name} (ID: {user_id}, 学号: {user.student_id}) 获得10个积分，当前积分: {user.points}")
                return 10
            else:
                print(f"用户名不匹配: 数据库中的姓名为 {user.full_name}，传入的姓名为 {user_name}")
                return 0
        else:
            print(f"未找到用户ID: {user_id}")
            return 0
    except Exception as e:
        print(f"积分奖励失败: {e}")
        return 0

@app.route('/query_lost_card', methods=['GET'])
def query_lost_card():
    """查询丢失的校园卡"""
    student_id = request.args.get('student_id')
    if not student_id:
        return jsonify({'error': 'Missing student ID'}), 400

    # 计算半个月前的时间
    half_month_ago = get_half_month_ago()

    # 查找匹配的校园卡（只查询最近半个月的记录）
    card = CampusCard.query.filter(
        CampusCard.student_id == student_id,
        CampusCard.status == 'found',
        CampusCard.found_time >= half_month_ago
    ).first()
    
    if card:
        # 尝试获取真实姓名
        real_name = get_real_name_by_student_id(student_id)

        # 返回领卡方式
        if card.handler_option == 1:
            # 自行联系：返回联系方式
            if real_name:
                message = f'您好{real_name}，您的校园卡已被拾到，请自行联系拾卡者'
            else:
                message = '您的校园卡已被拾到，请自行联系拾卡者'

            return jsonify({
                'status': 'found',
                'message': message,
                'contact_info': card.contact,
                'handler_type': 'contact',
                'owner_name': real_name,  # 添加真实姓名字段
                'card_id': card.id,  # 添加卡片ID用于删除操作
                'student_id': card.student_id  # 添加学号用于权限检查
            }), 200
        else:
            # 放置指定地点：返回拾取点信息
            if real_name:
                message = f'您好{real_name}，您的校园卡已放置在{card.contact}，请前往领取'
            else:
                message = f'您的校园卡已放置在{card.contact}，请前往领取'

            return jsonify({
                'status': 'found',
                'message': message,
                'location_info': card.contact,  # 拾取点信息存储在contact字段中
                'handler_type': 'location',
                'owner_name': real_name,  # 添加真实姓名字段
                'card_id': card.id,  # 添加卡片ID用于删除操作
                'student_id': card.student_id  # 添加学号用于权限检查
            }), 200
    
    # 未找到匹配卡片的处理
    return jsonify({
        'status': 'not_found',
        'message': '尚未找到您的校园卡，请多关注公示信息',
        'unmatched_cards': get_unmatched_cards()
    }), 200

def get_unmatched_cards():
    """获取未匹配的校园卡列表（脱敏）- 只显示最近半个月的记录"""
    # 计算半个月前的时间
    half_month_ago = get_half_month_ago()

    # 只查询最近半个月的未匹配校园卡
    cards = CampusCard.query.filter(
        CampusCard.is_matched == False,
        CampusCard.status == 'found',
        CampusCard.found_time >= half_month_ago
    ).all()

    result = []
    for card in cards:
        # 确定处理方式的显示文本
        if card.handler_option == 1:
            handler_text = "自行联系失主"
            contact_info = card.contact if card.contact else "未提供联系方式"
        elif card.handler_option == 2:
            handler_text = "放置到指定地点"
            contact_info = f"拾取点：{card.contact}" if card.contact else "未指定拾取点"
        else:
            handler_text = "未知处理方式"
            contact_info = "无信息"

        # 尝试获取真实姓名
        real_name = get_real_name_by_student_id(card.student_id)

        if real_name:
            # 找到了用户姓名，使用真实姓名
            display_name = real_name
            name_source = "real"  # 标记为真实姓名
        else:
            # 未找到用户姓名，使用默认的"持卡人"
            display_name = "持卡人"
            name_source = "default"  # 标记为默认名称

        result.append({
            'card_id': card.id,
            'masked_info': mask_info(display_name, card.student_id),
            'found_time': card.found_time.strftime('%Y-%m-%d %H:%M'),
            'found_location': card.found_location,
            'handler_option': card.handler_option,
            'handler_text': handler_text,
            'contact_info': contact_info,
            'owner_name': real_name,  # 真实姓名（如果有）
            'name_source': name_source,  # 姓名来源标记
            'student_id': card.student_id  # 添加学号用于权限检查
        })
    return result

@app.route('/forum/post', methods=['POST'])
def create_forum_post():
    """创建论坛帖子"""
    data = request.json
    title = data.get('title')
    content = data.get('content')
    author_id = data.get('author_id')
    is_ad = data.get('is_ad', False)
    is_advice = data.get('is_advice', False)

    if not all([title, content, author_id]):
        return jsonify({'error': 'Missing parameters'}), 400

    # 确保广告和建议/反馈互斥
    if is_ad and is_advice:
        return jsonify({'error': 'Post cannot be both advertisement and advice'}), 400

    post = ForumPost(
        title=title,
        content=content,
        author_id=author_id,
        is_ad=is_ad,
        is_advice=is_advice
    )
    db.session.add(post)
    db.session.commit()

    return jsonify({'message': 'Post created successfully', 'post_id': post.id}), 201

@app.route('/forum/posts', methods=['GET'])
def get_forum_posts():
    """获取论坛帖子列表"""
    posts = ForumPost.query.order_by(ForumPost.created_at.desc()).all()
    result = []
    for post in posts:
        author = User.query.get(post.author_id)
        result.append({
            'id': post.id,
            'title': post.title,
            'content': post.content,
            'author_name': author.full_name if author else 'Unknown',
            'created_at': post.created_at.strftime('%Y-%m-%d %H:%M'),
            'is_ad': post.is_ad,
            'is_advice': post.is_advice
        })
    return jsonify(result), 200

@app.route('/hot_locations', methods=['GET'])
def get_hot_locations():
    """获取热门丢失地点（从校园卡select_loc字段统计AI分析后的标准地点）- 只统计最近半个月的记录"""
    try:
        # 计算半个月前的时间
        half_month_ago = get_half_month_ago()

        # 获取最近半个月的所有校园卡记录（不限制status，统计所有地点）
        cards = CampusCard.query.filter(
            CampusCard.found_time >= half_month_ago
        ).all()

        if not cards:
            return jsonify([]), 200

        # 统计地点出现频次
        location_count = {}
        cards_with_select_loc = 0  # 统计有select_loc的卡片数量

        for card in cards:
            # 优先使用AI分析后的标准地点名称
            if card.select_loc and card.select_loc.strip():
                location = card.select_loc.strip()
                cards_with_select_loc += 1
                if location in location_count:
                    location_count[location] += 1
                else:
                    location_count[location] = 1
            # 如果没有select_loc，回退到原始found_location（用于兼容性）
            elif card.found_location and card.found_location.strip():
                location = f"[原始] {card.found_location.strip()}"
                if location in location_count:
                    location_count[location] += 1
                else:
                    location_count[location] = 1

        # 按频次排序，取前10个
        sorted_locations = sorted(location_count.items(), key=lambda x: x[1], reverse=True)[:10]

        # 格式化结果
        result = []
        total_cards = len(cards)

        for location, count in sorted_locations:
            result.append({
                'location': location,
                'count': count,
                'percentage': round((count / total_cards) * 100, 1) if total_cards > 0 else 0
            })

        # 添加统计信息到响应中
        response_data = {
            'locations': result,
            'statistics': {
                'total_cards': total_cards,
                'cards_with_ai_analysis': cards_with_select_loc,
                'ai_analysis_coverage': round((cards_with_select_loc / total_cards) * 100, 1) if total_cards > 0 else 0
            }
        }

        return jsonify(response_data), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/rewards', methods=['GET'])
def get_rewards():
    """获取奖励列表"""
    rewards = Reward.query.all()
    result = []
    for reward in rewards:
        result.append({
            'id': reward.id,
            'name': reward.name,
            'description': reward.description,
            'points_required': reward.points_required
        })
    return jsonify(result), 200

@app.route('/reward/redeem', methods=['POST'])
def redeem_reward():
    """兑换奖励"""
    data = request.json
    user_id = data.get('user_id')
    reward_id = data.get('reward_id')
    
    user = User.query.get(user_id)
    reward = Reward.query.get(reward_id)
    
    if not user or not reward:
        return jsonify({'error': 'Invalid user or reward'}), 404
    
    if user.points < reward.points_required:
        return jsonify({'error': 'Insufficient points'}), 400
    
    # 扣除积分
    user.points -= reward.points_required
    db.session.commit()
    
    return jsonify({
        'message': f'Successfully redeemed {reward.name}',
        'remaining_points': user.points
    }), 200

@app.route('/smart_location_query', methods=['POST'])
def smart_location_query():
    """智能地点查询接口"""
    try:
        data = request.json
        user_input = data.get('user_input', '').strip()

        if not user_input:
            return jsonify({'error': '请输入查询内容'}), 400

        # 使用AI解析地点
        parsing_result = parse_location_from_text(user_input)

        if not parsing_result['found_locations']:
            return jsonify({
                'success': False,
                'message': '抱歉，无法识别您输入中的校园地点。请尝试输入更具体的地点名称。',
                'parsing_result': parsing_result
            }), 200

        # 处理找到的地点
        results = []
        map_markers = []

        for location_name in parsing_result['found_locations']:
            # 获取查询地点的坐标
            query_location_coords = None
            for loc_key, loc_data in LOCATION_DB.items():
                if loc_data['name'] == location_name:
                    query_location_coords = {
                        'x': loc_data['x'],
                        'y': loc_data['y']
                    }
                    # 添加查询地点标记
                    map_markers.append({
                        'type': 'query_location',
                        'name': location_name,
                        'x': loc_data['x'],
                        'y': loc_data['y'],
                        'color': '#000000',  # 黑色
                        'shape': 'square'
                    })
                    break

            # 找到最近的招领点
            nearest_point = find_nearest_lost_and_found(location_name)

            if nearest_point:
                # 添加最近招领点标记
                map_markers.append({
                    'type': 'nearest_point',
                    'name': nearest_point['name'],
                    'x': nearest_point['x'],
                    'y': nearest_point['y'],
                    'distance': round(nearest_point['distance'], 1),
                    'color': '#dc3545',  # 红色
                    'shape': 'circle'
                })

                # 生成快速建议作为占位符，AI建议将通过单独接口获取
                quick_advice = f"最近的招领点是{nearest_point['name']}，距离约{nearest_point['distance']:.1f}个单位。"

                results.append({
                    'location': location_name,
                    'coordinates': query_location_coords,
                    'nearest_lost_and_found': {
                        'name': nearest_point['name'],
                        'distance': round(nearest_point['distance'], 1),
                        'coordinates': {
                            'x': nearest_point['x'],
                            'y': nearest_point['y']
                        }
                    },
                    'ai_advice': quick_advice,
                    'ai_advice_loading': True  # 标记AI建议正在加载
                })
            else:
                results.append({
                    'location': location_name,
                    'coordinates': query_location_coords,
                    'nearest_lost_and_found': None,
                    'ai_advice': f'抱歉，暂未找到距离{location_name}最近的招领点信息。'
                })

        return jsonify({
            'success': True,
            'message': f'成功识别到{len(results)}个地点',
            'parsing_result': parsing_result,
            'results': results,
            'map_data': {
                'markers': map_markers,
                'map_image': 'campus_map.jpg'
            }
        }), 200

    except Exception as e:
        print(f"智能地点查询错误: {e}")
        return jsonify({
            'success': False,
            'error': '查询过程中发生错误，请稍后重试'
        }), 500

@app.route('/get_ai_advice', methods=['POST'])
def get_ai_advice():
    """获取AI智能建议（流式接口）"""
    try:
        data = request.json
        location_name = data.get('location_name', '').strip()
        nearest_point_data = data.get('nearest_point')

        if not location_name or not nearest_point_data:
            return jsonify({'error': '缺少必要参数'}), 400

        # 重构nearest_point数据
        nearest_point = {
            'name': nearest_point_data.get('name'),
            'distance': nearest_point_data.get('distance'),
            'x': nearest_point_data.get('coordinates', {}).get('x'),
            'y': nearest_point_data.get('coordinates', {}).get('y')
        }

        # 调用AI分析函数
        ai_advice = analyze_nearest_lost_and_found_with_ai(location_name, nearest_point)

        return jsonify({
            'success': True,
            'location': location_name,
            'ai_advice': ai_advice
        }), 200

    except Exception as e:
        print(f"AI建议生成错误: {e}")
        return jsonify({
            'success': False,
            'error': '生成AI建议时发生错误'
        }), 500

@app.route('/delete_card_record', methods=['POST'])
def delete_card_record():
    """删除校园卡记录（将status改为'get'）"""
    try:
        data = request.json
        card_id = data.get('card_id')
        current_user_student_id = data.get('current_user_student_id')

        if not card_id or not current_user_student_id:
            return jsonify({'error': '缺少必要参数'}), 400

        # 查找校园卡记录
        card = CampusCard.query.get(card_id)
        if not card:
            return jsonify({'error': '未找到校园卡记录'}), 404

        # 检查权限：只有记录的拥有者才能删除
        if card.student_id != current_user_student_id:
            return jsonify({'error': '无权限删除此记录'}), 403

        # 检查记录状态：只能删除status为'found'的记录
        if card.status != 'found':
            return jsonify({'error': '该记录无法删除'}), 400

        # 执行删除操作：将status改为'get'
        card.status = 'get'
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '记录删除成功'
        }), 200

    except Exception as e:
        print(f"删除记录错误: {e}")
        return jsonify({
            'success': False,
            'error': '删除记录时发生错误'
        }), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    # 检查是否有waitress可用，如果有则使用生产级服务器
    try:
        from waitress import serve
        print("使用 Waitress 生产服务器启动...")
        print("服务地址: http://localhost:5000")
        print("按 Ctrl+C 停止服务")

        serve(
            app,
            host='0.0.0.0',
            port=5000,
            threads=10,
            connection_limit=1000,
            cleanup_interval=30,
            channel_timeout=120
        )
    except ImportError:
        print("Waitress 未安装，使用 Flask 开发服务器...")
        print("注意：开发服务器不适合长时间运行，建议安装 waitress")
        print("安装命令: pip install waitress")
        # 关闭调试模式以提高稳定性
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)