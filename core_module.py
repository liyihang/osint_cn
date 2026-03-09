"""
OSINT CN - 核心模块

该模块负责协调系统的核心功能，包括数据采集、处理和分析的统一调度。
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field

from osint_cn.config import get_config, Config
from osint_cn.collection import CollectorFactory, CollectedItem
from osint_cn.analysis import OSINTAnalyzer
from processing import TextProcessor

logger = logging.getLogger(__name__)


@dataclass
class TaskResult:
    """任务执行结果"""
    task_id: str
    task_type: str
    status: str  # success, failed, partial
    start_time: datetime
    end_time: Optional[datetime] = None
    data: Dict = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    
    @property
    def duration(self) -> float:
        """执行时长（秒）"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0


class OSINTCore:
    """OSINT 核心引擎"""
    
    def __init__(self, config: Config = None):
        """
        初始化核心引擎
        
        Args:
            config: 配置对象，如果不提供则使用默认配置
        """
        self.config = config or get_config()
        self.text_processor = TextProcessor()
        self.analyzer = OSINTAnalyzer(self.text_processor)
        self._task_counter = 0
        
        logger.info("OSINT Core initialized")
    
    def _generate_task_id(self) -> str:
        """生成任务 ID"""
        self._task_counter += 1
        return f"task_{datetime.now().strftime('%Y%m%d%H%M%S')}_{self._task_counter}"
    
    def collect(self, platform: str, keyword: str, limit: int = 100, 
                config: Dict = None) -> TaskResult:
        """
        执行数据采集任务
        
        Args:
            platform: 目标平台
            keyword: 搜索关键词
            limit: 采集数量限制
            config: 采集器配置
            
        Returns:
            TaskResult: 任务执行结果
        """
        task_id = self._generate_task_id()
        start_time = datetime.now()
        errors = []
        
        logger.info(f"Starting collection task {task_id}: {platform} - {keyword}")
        
        try:
            collector = CollectorFactory.create(platform, config)
            items = collector.collect(keyword, limit=limit)
            
            # 转换为可序列化格式
            data = {
                'items': [self._item_to_dict(item) for item in items],
                'count': len(items),
                'platform': platform,
                'keyword': keyword
            }
            
            status = 'success' if items else 'partial'
            
        except Exception as e:
            logger.error(f"Collection task {task_id} failed: {e}")
            errors.append(str(e))
            data = {'items': [], 'count': 0}
            status = 'failed'
        
        return TaskResult(
            task_id=task_id,
            task_type='collection',
            status=status,
            start_time=start_time,
            end_time=datetime.now(),
            data=data,
            errors=errors
        )
    
    def _item_to_dict(self, item: CollectedItem) -> Dict:
        """将采集项转换为字典"""
        return {
            'platform': item.platform,
            'content': item.content,
            'author': item.author,
            'author_id': item.author_id,
            'url': item.url,
            'publish_time': item.publish_time.isoformat() if item.publish_time else None,
            'likes': item.likes,
            'comments': item.comments,
            'shares': item.shares,
            'metadata': item.metadata
        }
    
    def process_text(self, text: str) -> Dict:
        """
        处理单条文本
        
        Args:
            text: 待处理文本
            
        Returns:
            处理结果字典
        """
        cleaned = self.text_processor.clean_text(text)
        segments = self.text_processor.segment(cleaned)
        keywords = self.text_processor.extract_keywords(cleaned, top_k=10)
        sentiment = self.text_processor.sentiment_analysis(cleaned)
        entities = self.text_processor.extract_entities(cleaned)
        
        return {
            'original': text,
            'cleaned': cleaned,
            'segments': segments,
            'keywords': [{'keyword': kw.keyword, 'weight': kw.weight} for kw in keywords],
            'sentiment': {
                'sentiment': sentiment.sentiment,
                'score': sentiment.score,
                'confidence': sentiment.confidence
            },
            'entities': entities
        }
    
    def analyze(self, data: List[Dict], analysis_types: List[str] = None) -> TaskResult:
        """
        执行数据分析任务
        
        Args:
            data: 待分析数据
            analysis_types: 分析类型列表 ['sentiment', 'trend', 'risk', 'relationship']
            
        Returns:
            TaskResult: 任务执行结果
        """
        task_id = self._generate_task_id()
        start_time = datetime.now()
        errors = []
        
        analysis_types = analysis_types or ['sentiment', 'trend', 'risk']
        
        logger.info(f"Starting analysis task {task_id}: {analysis_types}")
        
        results = {}
        
        try:
            texts = [item.get('content', '') for item in data if item.get('content')]
            
            if 'sentiment' in analysis_types:
                try:
                    results['sentiment'] = self.analyzer.sentiment_analysis(texts).to_dict()
                except Exception as e:
                    errors.append(f"Sentiment analysis failed: {e}")
            
            if 'trend' in analysis_types:
                try:
                    results['trend'] = self.analyzer.trend_analysis(data).to_dict()
                except Exception as e:
                    errors.append(f"Trend analysis failed: {e}")
            
            if 'risk' in analysis_types:
                try:
                    results['risk'] = self.analyzer.risk_assessment(data).to_dict()
                except Exception as e:
                    errors.append(f"Risk assessment failed: {e}")
            
            if 'relationship' in analysis_types:
                try:
                    results['relationship'] = self.analyzer.relationship_analysis(data).to_dict()
                except Exception as e:
                    errors.append(f"Relationship analysis failed: {e}")
            
            status = 'success' if not errors else 'partial'
            
        except Exception as e:
            logger.error(f"Analysis task {task_id} failed: {e}")
            errors.append(str(e))
            status = 'failed'
        
        return TaskResult(
            task_id=task_id,
            task_type='analysis',
            status=status,
            start_time=start_time,
            end_time=datetime.now(),
            data=results,
            errors=errors
        )
    
    def run_pipeline(self, platform: str, keyword: str, limit: int = 100,
                     analysis_types: List[str] = None) -> Dict:
        """
        运行完整的采集-分析流水线
        
        Args:
            platform: 目标平台
            keyword: 搜索关键词
            limit: 采集数量限制
            analysis_types: 分析类型
            
        Returns:
            包含采集和分析结果的字典
        """
        pipeline_id = self._generate_task_id()
        
        logger.info(f"Starting pipeline {pipeline_id}: {platform} - {keyword}")
        
        # 步骤 1: 采集数据
        collection_result = self.collect(platform, keyword, limit)
        
        if collection_result.status == 'failed':
            return {
                'pipeline_id': pipeline_id,
                'status': 'failed',
                'collection': collection_result.data,
                'errors': collection_result.errors
            }
        
        # 步骤 2: 分析数据
        items = collection_result.data.get('items', [])
        analysis_result = self.analyze(items, analysis_types)
        
        return {
            'pipeline_id': pipeline_id,
            'status': 'success' if analysis_result.status == 'success' else 'partial',
            'collection': {
                'count': collection_result.data.get('count', 0),
                'duration': collection_result.duration
            },
            'analysis': analysis_result.data,
            'errors': collection_result.errors + analysis_result.errors
        }
    
    def batch_collect(self, tasks: List[Dict]) -> List[TaskResult]:
        """
        批量采集
        
        Args:
            tasks: 任务列表，每个任务包含 platform, keyword, limit
            
        Returns:
            任务结果列表
        """
        results = []
        
        for task in tasks:
            result = self.collect(
                platform=task.get('platform'),
                keyword=task.get('keyword'),
                limit=task.get('limit', 100),
                config=task.get('config')
            )
            results.append(result)
        
        return results
    
    def compare_platforms(self, keyword: str, platforms: List[str] = None,
                          limit: int = 50) -> Dict:
        """
        跨平台比较分析
        
        Args:
            keyword: 搜索关键词
            platforms: 平台列表
            limit: 每个平台的采集数量
            
        Returns:
            比较分析结果
        """
        platforms = platforms or ['weibo', 'zhihu', 'baidu']
        
        platform_results = {}
        all_items = []
        
        for platform in platforms:
            result = self.collect(platform, keyword, limit)
            items = result.data.get('items', [])
            
            # 为每个项目添加平台标记
            for item in items:
                item['source_platform'] = platform
            
            all_items.extend(items)
            
            # 分析该平台的数据
            if items:
                texts = [item.get('content', '') for item in items]
                sentiment = self.analyzer.sentiment_analysis(texts)
                
                platform_results[platform] = {
                    'count': len(items),
                    'sentiment': sentiment.data['statistics'],
                    'top_keywords': self._extract_platform_keywords(items)
                }
            else:
                platform_results[platform] = {
                    'count': 0,
                    'sentiment': None,
                    'top_keywords': []
                }
        
        # 综合分析
        overall_analysis = None
        if all_items:
            overall_analysis = self.analyzer.comprehensive_analysis(all_items)
        
        return {
            'keyword': keyword,
            'platforms': platform_results,
            'overall': overall_analysis,
            'total_items': len(all_items)
        }
    
    def _extract_platform_keywords(self, items: List[Dict], top_k: int = 10) -> List[Dict]:
        """提取平台关键词"""
        all_text = ' '.join([item.get('content', '') for item in items])
        keywords = self.text_processor.extract_keywords(all_text, top_k=top_k)
        return [{'keyword': kw.keyword, 'weight': kw.weight} for kw in keywords]


# 便捷函数
def create_core(config: Config = None) -> OSINTCore:
    """创建核心实例"""
    return OSINTCore(config)


def quick_collect(platform: str, keyword: str, limit: int = 100) -> List[Dict]:
    """快速采集"""
    core = OSINTCore()
    result = core.collect(platform, keyword, limit)
    return result.data.get('items', [])


def quick_analyze(texts: List[str]) -> Dict:
    """快速分析"""
    core = OSINTCore()
    data = [{'content': text} for text in texts]
    result = core.analyze(data)
    return result.data