import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import json

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """分析结果基类"""
    analysis_type: str
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict = field(default_factory=dict)
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            'analysis_type': self.analysis_type,
            'timestamp': self.timestamp.isoformat(),
            'data': self.data,
            'metadata': self.metadata
        }


@dataclass
class SentimentStats:
    """情感统计"""
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0
    average_score: float = 0.0
    score_distribution: Dict[str, int] = field(default_factory=dict)


@dataclass
class TrendData:
    """趋势数据"""
    time_series: List[Dict] = field(default_factory=list)
    growth_rate: float = 0.0
    peak_time: Optional[datetime] = None
    keywords_evolution: Dict[str, List] = field(default_factory=dict)


@dataclass
class RiskIndicator:
    """风险指标"""
    level: str  # low, medium, high, critical
    score: float  # 0-100
    factors: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class OSINTAnalyzer:
    """OSINT 数据分析器"""
    
    def __init__(self, text_processor=None):
        """
        初始化分析器
        
        Args:
            text_processor: 文本处理器实例，用于情感分析等
        """
        self.text_processor = text_processor
        self._init_risk_keywords()
    
    def _init_risk_keywords(self):
        """初始化风险关键词"""
        self.risk_keywords = {
            'high': ['诈骗', '传销', '非法', '犯罪', '洗钱', '赌博', '毒品', '暴力', '恐怖'],
            'medium': ['投诉', '维权', '举报', '曝光', '黑幕', '骗局', '套路', '跑路', '暴雷'],
            'low': ['问题', '质疑', '争议', '纠纷', '负面', '差评', '退款', '投诉']
        }
        
        self.sensitive_topics = {
            '金融': ['理财', '投资', 'P2P', '借贷', '信用卡', '贷款', '股票', '基金'],
            '健康': ['药品', '保健品', '医疗', '治疗', '疾病', '偏方'],
            '政治': ['政府', '官员', '政策', '选举', '腐败'],
        }
    
    def sentiment_analysis(self, texts: List[str]) -> AnalysisResult:
        """
        批量情感分析
        
        Args:
            texts: 文本列表
            
        Returns:
            情感分析结果
        """
        if not self.text_processor:
            from processing import TextProcessor
            self.text_processor = TextProcessor()
        
        results = []
        positive_count = 0
        negative_count = 0
        neutral_count = 0
        total_score = 0.0
        
        for text in texts:
            result = self.text_processor.sentiment_analysis(text)
            results.append({
                'text': text[:100],
                'sentiment': result.sentiment,
                'score': result.score,
                'confidence': result.confidence
            })
            
            total_score += result.score
            if result.sentiment == 'positive':
                positive_count += 1
            elif result.sentiment == 'negative':
                negative_count += 1
            else:
                neutral_count += 1
        
        total = len(texts) or 1
        stats = SentimentStats(
            positive_count=positive_count,
            negative_count=negative_count,
            neutral_count=neutral_count,
            average_score=round(total_score / total, 3),
            score_distribution={
                'positive_ratio': round(positive_count / total, 3),
                'negative_ratio': round(negative_count / total, 3),
                'neutral_ratio': round(neutral_count / total, 3)
            }
        )
        
        return AnalysisResult(
            analysis_type='sentiment',
            data={
                'statistics': {
                    'positive_count': stats.positive_count,
                    'negative_count': stats.negative_count,
                    'neutral_count': stats.neutral_count,
                    'average_score': stats.average_score,
                    'distribution': stats.score_distribution
                },
                'samples': results[:20]  # 返回前20个样本
            },
            metadata={'total_analyzed': len(texts)}
        )
    
    def relationship_analysis(self, data: List[Dict]) -> AnalysisResult:
        """
        关系网络分析
        
        Args:
            data: 包含 author, mentions, retweets 等字段的数据列表
            
        Returns:
            关系分析结果
        """
        # 构建关系图
        nodes = set()
        edges = []
        edge_weights = defaultdict(int)
        
        for item in data:
            author = item.get('author', '')
            if author:
                nodes.add(author)
            
            # 提取 @ 提及
            mentions = item.get('mentions', [])
            if isinstance(mentions, str):
                import re
                mentions = re.findall(r'@(\w+)', mentions)
            
            for mention in mentions:
                nodes.add(mention)
                edge_key = (author, mention)
                edge_weights[edge_key] += 1
            
            # 转发关系
            retweet_from = item.get('retweet_from', '')
            if retweet_from:
                nodes.add(retweet_from)
                edge_key = (author, retweet_from)
                edge_weights[edge_key] += 1
        
        # 转换为边列表
        for (source, target), weight in edge_weights.items():
            edges.append({
                'source': source,
                'target': target,
                'weight': weight
            })
        
        # 计算节点度数
        in_degree = defaultdict(int)
        out_degree = defaultdict(int)
        
        for edge in edges:
            out_degree[edge['source']] += edge['weight']
            in_degree[edge['target']] += edge['weight']
        
        # 识别关键节点
        node_stats = []
        for node in nodes:
            node_stats.append({
                'id': node,
                'in_degree': in_degree[node],
                'out_degree': out_degree[node],
                'total_degree': in_degree[node] + out_degree[node]
            })
        
        # 按总度数排序
        node_stats.sort(key=lambda x: x['total_degree'], reverse=True)
        key_nodes = node_stats[:10]
        
        # 社区检测（简化版：基于连接度）
        communities = self._detect_communities(nodes, edges)
        
        return AnalysisResult(
            analysis_type='relationship',
            data={
                'nodes': list(nodes),
                'edges': edges,
                'key_nodes': key_nodes,
                'communities': communities,
                'statistics': {
                    'total_nodes': len(nodes),
                    'total_edges': len(edges),
                    'avg_degree': sum(in_degree.values()) / max(len(nodes), 1)
                }
            },
            metadata={'data_count': len(data)}
        )
    
    def _detect_communities(self, nodes: set, edges: List[Dict]) -> List[Dict]:
        """简化版社区检测"""
        # 构建邻接表
        adjacency = defaultdict(set)
        for edge in edges:
            adjacency[edge['source']].add(edge['target'])
            adjacency[edge['target']].add(edge['source'])
        
        # 使用连通分量作为社区
        visited = set()
        communities = []
        
        for node in nodes:
            if node not in visited:
                community = set()
                stack = [node]
                while stack:
                    current = stack.pop()
                    if current not in visited:
                        visited.add(current)
                        community.add(current)
                        stack.extend(adjacency[current] - visited)
                
                if len(community) > 1:
                    communities.append({
                        'id': len(communities),
                        'members': list(community),
                        'size': len(community)
                    })
        
        return communities
    
    def trend_analysis(self, data: List[Dict], time_field: str = 'publish_time', 
                       interval: str = 'day') -> AnalysisResult:
        """
        趋势分析
        
        Args:
            data: 带时间戳的数据列表
            time_field: 时间字段名
            interval: 时间间隔 (hour/day/week)
            
        Returns:
            趋势分析结果
        """
        # 按时间聚合
        time_buckets = defaultdict(list)
        
        for item in data:
            timestamp = item.get(time_field)
            if not timestamp:
                continue
            
            if isinstance(timestamp, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                except ValueError:
                    continue
            
            if interval == 'hour':
                bucket_key = timestamp.strftime('%Y-%m-%d %H:00')
            elif interval == 'day':
                bucket_key = timestamp.strftime('%Y-%m-%d')
            elif interval == 'week':
                bucket_key = timestamp.strftime('%Y-W%W')
            else:
                bucket_key = timestamp.strftime('%Y-%m-%d')
            
            time_buckets[bucket_key].append(item)
        
        # 生成时间序列
        time_series = []
        sorted_keys = sorted(time_buckets.keys())
        
        keywords_by_time = {}
        
        for key in sorted_keys:
            items = time_buckets[key]
            
            # 提取该时段的关键词
            all_text = ' '.join([item.get('content', '') for item in items])
            if self.text_processor:
                keywords = self.text_processor.extract_keywords(all_text, top_k=5)
                keywords_by_time[key] = [kw.keyword for kw in keywords]
            
            # 计算互动量
            total_likes = sum(item.get('likes', 0) for item in items)
            total_comments = sum(item.get('comments', 0) for item in items)
            total_shares = sum(item.get('shares', 0) for item in items)
            
            time_series.append({
                'time': key,
                'count': len(items),
                'likes': total_likes,
                'comments': total_comments,
                'shares': total_shares,
                'engagement': total_likes + total_comments * 2 + total_shares * 3
            })
        
        # 计算增长率
        growth_rate = 0.0
        if len(time_series) >= 2:
            first_half = sum(ts['count'] for ts in time_series[:len(time_series)//2])
            second_half = sum(ts['count'] for ts in time_series[len(time_series)//2:])
            if first_half > 0:
                growth_rate = (second_half - first_half) / first_half
        
        # 找出峰值
        peak = max(time_series, key=lambda x: x['count']) if time_series else None
        
        return AnalysisResult(
            analysis_type='trend',
            data={
                'time_series': time_series,
                'growth_rate': round(growth_rate, 3),
                'peak_time': peak['time'] if peak else None,
                'peak_count': peak['count'] if peak else 0,
                'keywords_evolution': keywords_by_time,
                'statistics': {
                    'total_periods': len(time_series),
                    'total_items': len(data),
                    'avg_per_period': len(data) / max(len(time_series), 1)
                }
            },
            metadata={'interval': interval, 'time_field': time_field}
        )
    
    def risk_assessment(self, data: List[Dict], context: Dict = None) -> AnalysisResult:
        """
        风险评估
        
        Args:
            data: 数据列表
            context: 上下文信息（如行业、主体等）
            
        Returns:
            风险评估结果
        """
        context = context or {}
        risk_factors = []
        risk_score = 0
        
        # 合并所有文本
        all_texts = [item.get('content', '') for item in data]
        combined_text = ' '.join(all_texts)
        
        # 1. 关键词风险检测
        keyword_risks = self._check_keyword_risks(combined_text)
        risk_factors.extend(keyword_risks['factors'])
        risk_score += keyword_risks['score']
        
        # 2. 情感风险（负面情绪过多）
        if self.text_processor and all_texts:
            sentiment_result = self.sentiment_analysis(all_texts[:100])  # 采样分析
            negative_ratio = sentiment_result.data['statistics']['distribution']['negative_ratio']
            
            if negative_ratio > 0.5:
                risk_factors.append(f"负面情绪占比过高: {negative_ratio:.1%}")
                risk_score += 20
            elif negative_ratio > 0.3:
                risk_factors.append(f"存在较多负面情绪: {negative_ratio:.1%}")
                risk_score += 10
        
        # 3. 传播风险（高互动但负面）
        high_engagement_negative = 0
        for item in data:
            engagement = item.get('likes', 0) + item.get('comments', 0) * 2 + item.get('shares', 0) * 3
            if engagement > 1000:
                content = item.get('content', '')
                for keyword in self.risk_keywords['medium'] + self.risk_keywords['high']:
                    if keyword in content:
                        high_engagement_negative += 1
                        break
        
        if high_engagement_negative > 0:
            risk_factors.append(f"发现 {high_engagement_negative} 条高传播风险内容")
            risk_score += high_engagement_negative * 5
        
        # 4. 敏感话题检测
        for topic, keywords in self.sensitive_topics.items():
            if any(kw in combined_text for kw in keywords):
                risk_factors.append(f"涉及敏感话题: {topic}")
                risk_score += 5
        
        # 确定风险等级
        risk_score = min(risk_score, 100)
        if risk_score >= 70:
            risk_level = 'critical'
        elif risk_score >= 50:
            risk_level = 'high'
        elif risk_score >= 30:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        # 生成建议
        recommendations = self._generate_recommendations(risk_level, risk_factors)
        
        return AnalysisResult(
            analysis_type='risk_assessment',
            data={
                'risk_level': risk_level,
                'risk_score': risk_score,
                'risk_factors': risk_factors,
                'recommendations': recommendations,
                'details': {
                    'keyword_risks': keyword_risks,
                    'high_engagement_negative': high_engagement_negative
                }
            },
            metadata={'data_count': len(data), 'context': context}
        )
    
    def _check_keyword_risks(self, text: str) -> Dict:
        """检查关键词风险"""
        factors = []
        score = 0
        found_keywords = {'high': [], 'medium': [], 'low': []}
        
        for level, keywords in self.risk_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    found_keywords[level].append(keyword)
        
        if found_keywords['high']:
            factors.append(f"发现高风险关键词: {', '.join(found_keywords['high'][:5])}")
            score += len(found_keywords['high']) * 15
        
        if found_keywords['medium']:
            factors.append(f"发现中等风险关键词: {', '.join(found_keywords['medium'][:5])}")
            score += len(found_keywords['medium']) * 8
        
        if found_keywords['low']:
            factors.append(f"发现低风险关键词: {', '.join(found_keywords['low'][:5])}")
            score += len(found_keywords['low']) * 3
        
        return {'factors': factors, 'score': min(score, 50), 'found_keywords': found_keywords}
    
    def _generate_recommendations(self, risk_level: str, factors: List[str]) -> List[str]:
        """生成风险建议"""
        recommendations = []
        
        if risk_level in ['critical', 'high']:
            recommendations.extend([
                "建议立即进行深入调查",
                "启动舆情监控和预警机制",
                "准备应对方案和公关预案"
            ])
        elif risk_level == 'medium':
            recommendations.extend([
                "建议持续关注舆情发展",
                "定期进行风险评估",
                "准备基础应对话术"
            ])
        else:
            recommendations.extend([
                "保持常规监控即可",
                "定期进行例行检查"
            ])
        
        return recommendations
    
    def comprehensive_analysis(self, data: List[Dict]) -> Dict:
        """
        综合分析
        
        Args:
            data: 数据列表
            
        Returns:
            包含多维度分析结果的字典
        """
        texts = [item.get('content', '') for item in data if item.get('content')]
        
        results = {
            'sentiment': self.sentiment_analysis(texts).to_dict(),
            'trend': self.trend_analysis(data).to_dict(),
            'risk': self.risk_assessment(data).to_dict(),
            'relationship': self.relationship_analysis(data).to_dict(),
            'summary': {
                'total_items': len(data),
                'analysis_time': datetime.now().isoformat(),
            }
        }
        
        return results
