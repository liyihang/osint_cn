"""
OSINT CN - 开源情报系统

一个专注于中文互联网的开源情报采集与分析系统。

功能：
- 多平台数据采集（微博、知乎、抖音、百度等）
- 中文文本处理（分词、情感分析、关键词提取）
- 数据分析（情感统计、趋势分析、风险评估、关系网络）
- RESTful API 服务

使用示例：
    from osint_cn import OSINTCore
    
    # 创建核心实例
    core = OSINTCore()
    
    # 采集数据
    result = core.collect('weibo', '人工智能', limit=50)
    
    # 分析数据
    analysis = core.analyze(result.data['items'])
"""

__version__ = '1.0.0'
__author__ = 'OSINT CN Team'

from osint_cn.config import Config, get_config
from osint_cn.collection import (
    BaseCollector,
    WeiboCollector,
    ZhihuCollector,
    DouyinCollector,
    BaiduCollector,
    CollectorFactory,
    CollectedItem
)
from osint_cn.analysis import OSINTAnalyzer, AnalysisResult

__all__ = [
    'Config',
    'get_config',
    'BaseCollector',
    'WeiboCollector',
    'ZhihuCollector',
    'DouyinCollector',
    'BaiduCollector',
    'CollectorFactory',
    'CollectedItem',
    'OSINTAnalyzer',
    'AnalysisResult',
]
