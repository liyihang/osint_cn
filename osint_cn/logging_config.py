"""
OSINT CN 日志系统

提供统一的日志配置、格式化和错误追踪
"""

import os
import sys
import json
import logging
import traceback
from datetime import datetime
from typing import Optional, Dict, Any
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from functools import wraps
import time


# ==========================================
# 日志格式化器
# ==========================================

class JSONFormatter(logging.Formatter):
    """JSON 格式日志"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # 添加异常信息
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # 添加额外字段
        if hasattr(record, 'extra_data'):
            log_data['extra'] = record.extra_data
        
        return json.dumps(log_data, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """彩色控制台日志格式"""
    
    COLORS = {
        'DEBUG': '\033[36m',     # 青色
        'INFO': '\033[32m',      # 绿色
        'WARNING': '\033[33m',   # 黄色
        'ERROR': '\033[31m',     # 红色
        'CRITICAL': '\033[35m',  # 紫色
    }
    RESET = '\033[0m'
    
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        
        # 格式化时间
        time_str = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        # 构建日志消息
        message = f"{color}[{time_str}] [{record.levelname:8}]{self.RESET} "
        message += f"\033[90m{record.name}\033[0m - {record.getMessage()}"
        
        # 添加异常信息
        if record.exc_info:
            message += f"\n{color}{self._format_exception(record.exc_info)}{self.RESET}"
        
        return message
    
    def _format_exception(self, exc_info) -> str:
        return ''.join(traceback.format_exception(*exc_info))


# ==========================================
# 日志配置
# ==========================================

def setup_logging(
    log_level: str = None,
    log_file: str = None,
    log_format: str = 'text',  # text, json, colored
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    配置日志系统
    
    Args:
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件路径
        log_format: 日志格式 (text, json, colored)
        max_bytes: 日志文件最大大小
        backup_count: 保留的备份文件数量
    
    Returns:
        根日志记录器
    """
    # 从环境变量获取配置
    log_level = log_level or os.getenv('LOG_LEVEL', 'INFO')
    log_file = log_file or os.getenv('LOG_FILE', 'logs/app.log')
    log_format = os.getenv('LOG_FORMAT', log_format)
    
    # 转换日志级别
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # 获取根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # 清除现有处理器
    root_logger.handlers.clear()
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    if log_format == 'colored' and sys.stdout.isatty():
        console_handler.setFormatter(ColoredFormatter())
    elif log_format == 'json':
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
    
    root_logger.addHandler(console_handler)
    
    # 文件处理器
    if log_file:
        # 确保日志目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(JSONFormatter())  # 文件始终使用 JSON 格式
        
        root_logger.addHandler(file_handler)
        
        # 错误日志单独文件
        error_file = log_file.replace('.log', '.error.log')
        error_handler = RotatingFileHandler(
            error_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(JSONFormatter())
        
        root_logger.addHandler(error_handler)
    
    return root_logger


def get_logger(name: str = None) -> logging.Logger:
    """获取日志记录器"""
    return logging.getLogger(name)


# ==========================================
# 日志装饰器
# ==========================================

def log_function_call(logger: logging.Logger = None):
    """
    函数调用日志装饰器
    
    记录函数的调用参数、返回值和执行时间
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            log = logger or logging.getLogger(func.__module__)
            
            # 记录调用
            log.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                
                log.debug(f"{func.__name__} completed in {elapsed:.3f}s")
                return result
                
            except Exception as e:
                elapsed = time.time() - start_time
                log.error(
                    f"{func.__name__} failed after {elapsed:.3f}s: {e}",
                    exc_info=True
                )
                raise
        
        return wrapper
    return decorator


def log_api_request(logger: logging.Logger = None):
    """
    API 请求日志装饰器
    
    记录 Flask API 请求的详细信息
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from flask import request
            
            log = logger or logging.getLogger('api')
            
            # 记录请求
            log.info(f"API Request: {request.method} {request.path}")
            
            if request.is_json and request.data:
                log.debug(f"Request body: {request.get_json()}")
            
            start_time = time.time()
            try:
                response = func(*args, **kwargs)
                elapsed = time.time() - start_time
                
                status_code = response[1] if isinstance(response, tuple) else 200
                log.info(f"API Response: {status_code} in {elapsed:.3f}s")
                
                return response
                
            except Exception as e:
                elapsed = time.time() - start_time
                log.error(
                    f"API Error: {request.method} {request.path} failed after {elapsed:.3f}s",
                    exc_info=True
                )
                raise
        
        return wrapper
    return decorator


# ==========================================
# 错误追踪
# ==========================================

class ErrorTracker:
    """错误追踪器"""
    
    def __init__(self, max_errors: int = 100):
        self.errors: list = []
        self.max_errors = max_errors
        self.logger = logging.getLogger('error_tracker')
    
    def capture(self, error: Exception, context: Dict = None) -> str:
        """
        捕获错误
        
        Args:
            error: 异常对象
            context: 上下文信息
            
        Returns:
            错误 ID
        """
        import uuid
        
        error_id = str(uuid.uuid4())[:8]
        
        error_data = {
            'id': error_id,
            'type': type(error).__name__,
            'message': str(error),
            'traceback': traceback.format_exc(),
            'context': context or {},
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # 添加到错误列表
        self.errors.append(error_data)
        
        # 限制错误数量
        if len(self.errors) > self.max_errors:
            self.errors = self.errors[-self.max_errors:]
        
        # 记录日志
        self.logger.error(
            f"Error captured [{error_id}]: {type(error).__name__}: {error}",
            extra={'extra_data': error_data}
        )
        
        return error_id
    
    def get_error(self, error_id: str) -> Optional[Dict]:
        """获取错误详情"""
        for error in self.errors:
            if error['id'] == error_id:
                return error
        return None
    
    def get_recent_errors(self, limit: int = 10) -> list:
        """获取最近的错误"""
        return self.errors[-limit:]
    
    def get_error_stats(self) -> Dict:
        """获取错误统计"""
        if not self.errors:
            return {'total': 0, 'by_type': {}}
        
        by_type = {}
        for error in self.errors:
            error_type = error['type']
            by_type[error_type] = by_type.get(error_type, 0) + 1
        
        return {
            'total': len(self.errors),
            'by_type': by_type,
            'oldest': self.errors[0]['timestamp'],
            'newest': self.errors[-1]['timestamp']
        }
    
    def clear(self):
        """清空错误记录"""
        self.errors.clear()


# 全局错误追踪器
_error_tracker: Optional[ErrorTracker] = None


def get_error_tracker() -> ErrorTracker:
    """获取全局错误追踪器"""
    global _error_tracker
    if _error_tracker is None:
        _error_tracker = ErrorTracker()
    return _error_tracker


def capture_error(error: Exception, context: Dict = None) -> str:
    """便捷函数：捕获错误"""
    return get_error_tracker().capture(error, context)


# ==========================================
# 审计日志
# ==========================================

class AuditLogger:
    """审计日志记录器"""
    
    def __init__(self, log_file: str = 'logs/audit.log'):
        self.logger = logging.getLogger('audit')
        self.logger.setLevel(logging.INFO)
        
        # 确保目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        
        # 每日滚动日志
        handler = TimedRotatingFileHandler(
            log_file,
            when='midnight',
            interval=1,
            backupCount=30,
            encoding='utf-8'
        )
        handler.setFormatter(JSONFormatter())
        
        self.logger.addHandler(handler)
    
    def log(self, action: str, user: str = None, details: Dict = None):
        """
        记录审计日志
        
        Args:
            action: 操作类型
            user: 用户标识
            details: 详细信息
        """
        record = logging.LogRecord(
            name='audit',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg=action,
            args=(),
            exc_info=None
        )
        
        record.extra_data = {
            'action': action,
            'user': user,
            'details': details or {}
        }
        
        self.logger.handle(record)
    
    def log_api_access(self, endpoint: str, method: str, user: str = None, 
                       status_code: int = None, duration: float = None):
        """记录 API 访问"""
        self.log(
            action='api_access',
            user=user,
            details={
                'endpoint': endpoint,
                'method': method,
                'status_code': status_code,
                'duration_ms': round(duration * 1000, 2) if duration else None
            }
        )
    
    def log_data_collection(self, platform: str, keyword: str, count: int, 
                            user: str = None):
        """记录数据采集"""
        self.log(
            action='data_collection',
            user=user,
            details={
                'platform': platform,
                'keyword': keyword,
                'collected_count': count
            }
        )
    
    def log_analysis(self, analysis_type: str, data_count: int, 
                     user: str = None, duration: float = None):
        """记录数据分析"""
        self.log(
            action='data_analysis',
            user=user,
            details={
                'analysis_type': analysis_type,
                'data_count': data_count,
                'duration_ms': round(duration * 1000, 2) if duration else None
            }
        )


# 全局审计日志记录器
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """获取审计日志记录器"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


# ==========================================
# 初始化
# ==========================================

def init_logging():
    """初始化日志系统"""
    setup_logging(
        log_level=os.getenv('LOG_LEVEL', 'INFO'),
        log_file=os.getenv('LOG_FILE', 'logs/app.log'),
        log_format=os.getenv('LOG_FORMAT', 'colored')
    )
    
    logger = get_logger(__name__)
    logger.info("Logging system initialized")
    
    return logger
