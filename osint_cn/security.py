"""
API 安全模块

提供认证、授权和限流功能
"""

import os
import time
import hashlib
import secrets
import functools
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Callable, Any
from flask import request, jsonify, g, current_app

logger = logging.getLogger(__name__)


# ============ API Key 认证 ============

class APIKeyManager:
    """API Key 管理器"""
    
    def __init__(self):
        self._keys: Dict[str, Dict[str, Any]] = {}
        self._load_from_env()
    
    def _load_from_env(self):
        """从环境变量加载 API Keys"""
        # 从环境变量加载主 API Key
        master_key = os.getenv('OSINT_API_KEY')
        if master_key:
            self._keys[master_key] = {
                'name': 'master',
                'role': 'admin',
                'rate_limit': 1000,  # 每分钟请求数
                'created_at': datetime.now(),
                'enabled': True,
            }
        
        # 加载额外的 API Keys（格式：OSINT_API_KEY_1, OSINT_API_KEY_2...）
        for i in range(1, 10):
            key = os.getenv(f'OSINT_API_KEY_{i}')
            if key:
                self._keys[key] = {
                    'name': f'key_{i}',
                    'role': 'user',
                    'rate_limit': 100,
                    'created_at': datetime.now(),
                    'enabled': True,
                }
    
    def generate_key(self, name: str = None, role: str = 'user', rate_limit: int = 100) -> str:
        """生成新的 API Key"""
        key = secrets.token_urlsafe(32)
        self._keys[key] = {
            'name': name or f'key_{len(self._keys) + 1}',
            'role': role,
            'rate_limit': rate_limit,
            'created_at': datetime.now(),
            'enabled': True,
        }
        return key
    
    def validate(self, key: str) -> Optional[Dict]:
        """验证 API Key"""
        key_info = self._keys.get(key)
        if key_info and key_info.get('enabled'):
            return key_info
        return None
    
    def revoke(self, key: str) -> bool:
        """撤销 API Key"""
        if key in self._keys:
            self._keys[key]['enabled'] = False
            return True
        return False
    
    def get_rate_limit(self, key: str) -> int:
        """获取 API Key 的速率限制"""
        key_info = self._keys.get(key)
        if key_info:
            return key_info.get('rate_limit', 60)
        return 60  # 默认限制


# 全局 API Key 管理器
api_key_manager = APIKeyManager()


# ============ 限流器 ============

class RateLimiter:
    """
    滑动窗口限流器
    
    支持基于 IP 或 API Key 的限流
    """
    
    def __init__(self, default_limit: int = 60, window_seconds: int = 60):
        """
        初始化限流器
        
        Args:
            default_limit: 默认每窗口请求限制
            window_seconds: 窗口大小（秒）
        """
        self.default_limit = default_limit
        self.window_seconds = window_seconds
        self._requests: Dict[str, list] = {}
        self._redis_client = None
        self._init_redis()
    
    def _init_redis(self):
        """初始化 Redis 连接（用于分布式限流）"""
        try:
            import redis
            redis_host = os.getenv('REDIS_HOST', 'localhost')
            redis_port = int(os.getenv('REDIS_PORT', 6379))
            redis_password = os.getenv('REDIS_PASSWORD')
            
            self._redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                decode_responses=True
            )
            self._redis_client.ping()
            logger.info("Redis connected for rate limiting")
        except Exception as e:
            logger.warning(f"Redis not available for rate limiting, using in-memory storage: {e}")
            self._redis_client = None
    
    def _get_identifier(self) -> str:
        """获取请求标识符（API Key 或 IP）"""
        # 优先使用 API Key
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        if api_key:
            return f"key:{api_key}"
        
        # 使用 IP 地址
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            ip = forwarded_for.split(',')[0].strip()
        else:
            ip = request.remote_addr
        
        return f"ip:{ip}"
    
    def _check_redis(self, identifier: str, limit: int) -> tuple:
        """使用 Redis 检查限流（分布式环境）"""
        key = f"rate_limit:{identifier}"
        current_time = int(time.time())
        window_start = current_time - self.window_seconds
        
        pipe = self._redis_client.pipeline()
        
        # 移除窗口外的请求
        pipe.zremrangebyscore(key, 0, window_start)
        # 添加当前请求
        pipe.zadd(key, {str(current_time): current_time})
        # 获取窗口内请求数
        pipe.zcard(key)
        # 设置过期时间
        pipe.expire(key, self.window_seconds * 2)
        
        results = pipe.execute()
        request_count = results[2]
        
        remaining = max(0, limit - request_count)
        reset_time = current_time + self.window_seconds
        
        return request_count <= limit, remaining, reset_time
    
    def _check_memory(self, identifier: str, limit: int) -> tuple:
        """使用内存检查限流（单机环境）"""
        current_time = time.time()
        window_start = current_time - self.window_seconds
        
        # 获取或创建请求列表
        if identifier not in self._requests:
            self._requests[identifier] = []
        
        # 清理窗口外的请求
        self._requests[identifier] = [
            t for t in self._requests[identifier] 
            if t > window_start
        ]
        
        request_count = len(self._requests[identifier])
        
        if request_count < limit:
            self._requests[identifier].append(current_time)
            allowed = True
        else:
            allowed = False
        
        remaining = max(0, limit - request_count - (1 if allowed else 0))
        reset_time = int(current_time) + self.window_seconds
        
        return allowed, remaining, reset_time
    
    def check(self, limit: int = None) -> tuple:
        """
        检查是否允许请求
        
        Returns:
            (allowed, remaining, reset_time) 元组
        """
        identifier = self._get_identifier()
        limit = limit or self.default_limit
        
        # 从 API Key 获取限制
        if identifier.startswith('key:'):
            api_key = identifier[4:]
            key_limit = api_key_manager.get_rate_limit(api_key)
            if key_limit:
                limit = key_limit
        
        if self._redis_client:
            return self._check_redis(identifier, limit)
        else:
            return self._check_memory(identifier, limit)
    
    def cleanup(self):
        """清理过期的内存数据"""
        current_time = time.time()
        window_start = current_time - self.window_seconds
        
        for identifier in list(self._requests.keys()):
            self._requests[identifier] = [
                t for t in self._requests[identifier]
                if t > window_start
            ]
            if not self._requests[identifier]:
                del self._requests[identifier]


# 全局限流器
rate_limiter = RateLimiter()


# ============ 装饰器 ============

def require_api_key(f: Callable) -> Callable:
    """
    要求 API Key 认证的装饰器
    
    从请求头 X-API-Key 或查询参数 api_key 获取 API Key
    """
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        
        if not api_key:
            return jsonify({
                'success': False,
                'error': 'unauthorized',
                'message': '缺少 API Key，请在请求头 X-API-Key 或查询参数 api_key 中提供'
            }), 401
        
        key_info = api_key_manager.validate(api_key)
        if not key_info:
            return jsonify({
                'success': False,
                'error': 'forbidden',
                'message': 'API Key 无效或已被禁用'
            }), 403
        
        # 将 key 信息存储到 g 对象供后续使用
        g.api_key = api_key
        g.api_key_info = key_info
        
        return f(*args, **kwargs)
    
    return decorated


def require_role(*roles):
    """
    要求特定角色的装饰器
    
    必须与 require_api_key 一起使用
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            if not hasattr(g, 'api_key_info'):
                return jsonify({
                    'success': False,
                    'error': 'unauthorized',
                    'message': '需要先进行 API Key 认证'
                }), 401
            
            user_role = g.api_key_info.get('role', 'user')
            if user_role not in roles:
                return jsonify({
                    'success': False,
                    'error': 'forbidden',
                    'message': f'需要 {", ".join(roles)} 角色权限'
                }), 403
            
            return f(*args, **kwargs)
        
        return decorated
    return decorator


def rate_limit(limit: int = None, per_seconds: int = 60):
    """
    限流装饰器
    
    Args:
        limit: 请求限制数量
        per_seconds: 时间窗口（秒）
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            if current_app and current_app.config.get('RATELIMIT_ENABLED', True) is False:
                return f(*args, **kwargs)

            allowed, remaining, reset_time = rate_limiter.check(limit)
            
            # 添加限流相关响应头
            response_headers = {
                'X-RateLimit-Limit': str(limit or rate_limiter.default_limit),
                'X-RateLimit-Remaining': str(remaining),
                'X-RateLimit-Reset': str(reset_time),
            }
            
            if not allowed:
                response = jsonify({
                    'success': False,
                    'error': 'rate_limit_exceeded',
                    'message': '请求过于频繁，请稍后再试',
                    'retry_after': reset_time - int(time.time())
                })
                response.headers.extend(response_headers)
                response.status_code = 429
                return response
            
            # 执行原函数
            result = f(*args, **kwargs)
            
            # 如果返回的是 Response 对象，添加头信息
            if hasattr(result, 'headers'):
                result.headers.extend(response_headers)
            
            return result
        
        return decorated
    return decorator


def optional_api_key(f: Callable) -> Callable:
    """
    可选 API Key 认证装饰器
    
    如果提供了 API Key 则验证，否则使用匿名访问（有更低的限流限制）
    """
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        
        if api_key:
            key_info = api_key_manager.validate(api_key)
            if key_info:
                g.api_key = api_key
                g.api_key_info = key_info
            else:
                return jsonify({
                    'success': False,
                    'error': 'forbidden',
                    'message': 'API Key 无效或已被禁用'
                }), 403
        else:
            g.api_key = None
            g.api_key_info = {'role': 'anonymous', 'rate_limit': 30}
        
        return f(*args, **kwargs)
    
    return decorated


# ============ 安全工具函数 ============

def hash_api_key(key: str) -> str:
    """对 API Key 进行哈希处理（用于存储）"""
    return hashlib.sha256(key.encode()).hexdigest()


def generate_request_id() -> str:
    """生成请求 ID"""
    return secrets.token_hex(16)


def mask_sensitive_data(data: str, visible_chars: int = 4) -> str:
    """
    遮蔽敏感数据
    
    例如：sk_live_1234567890 -> sk_l****7890
    """
    if len(data) <= visible_chars * 2:
        return '*' * len(data)
    
    return f"{data[:visible_chars]}****{data[-visible_chars:]}"


def validate_ip_whitelist(ip: str, whitelist: list) -> bool:
    """验证 IP 是否在白名单中"""
    import ipaddress
    
    try:
        ip_obj = ipaddress.ip_address(ip)
        
        for allowed in whitelist:
            if '/' in allowed:
                # 网段
                if ip_obj in ipaddress.ip_network(allowed, strict=False):
                    return True
            else:
                # 单个 IP
                if ip_obj == ipaddress.ip_address(allowed):
                    return True
        
        return False
    except ValueError:
        return False


# ============ 中间件 ============

def setup_security_middleware(app):
    """
    设置安全中间件
    
    Args:
        app: Flask 应用实例
    """
    @app.before_request
    def before_request():
        # 生成请求 ID
        g.request_id = generate_request_id()
        g.request_start_time = time.time()
        
        # 记录请求日志
        logger.info(f"[{g.request_id}] {request.method} {request.path} - IP: {request.remote_addr}")
    
    @app.after_request
    def after_request(response):
        # 添加安全相关响应头
        response.headers['X-Request-ID'] = g.get('request_id', '')
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # 记录响应日志
        duration = time.time() - g.get('request_start_time', time.time())
        logger.info(f"[{g.get('request_id', '')}] Response: {response.status_code} - {duration:.3f}s")
        
        return response
    
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({
            'success': False,
            'error': 'rate_limit_exceeded',
            'message': '请求过于频繁，请稍后再试'
        }), 429
    
    @app.errorhandler(401)
    def unauthorized_handler(e):
        return jsonify({
            'success': False,
            'error': 'unauthorized',
            'message': '未授权访问'
        }), 401
    
    @app.errorhandler(403)
    def forbidden_handler(e):
        return jsonify({
            'success': False,
            'error': 'forbidden',
            'message': '禁止访问'
        }), 403
