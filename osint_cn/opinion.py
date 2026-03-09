"""
自动化舆情分析引擎
情感趋势分析、热点追踪、传播分析、话题聚类
"""

import logging
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Set
import threading
import time

import jieba
import jieba.analyse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans, DBSCAN
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

logger = logging.getLogger(__name__)


class SentimentLevel(Enum):
    """情感级别"""
    VERY_NEGATIVE = -2
    NEGATIVE = -1
    NEUTRAL = 0
    POSITIVE = 1
    VERY_POSITIVE = 2


class HotLevel(Enum):
    """热度级别"""
    COLD = 1
    WARM = 2
    HOT = 3
    VERY_HOT = 4
    EXPLOSIVE = 5


class TrendDirection(Enum):
    """趋势方向"""
    FALLING = "falling"
    STABLE = "stable"
    RISING = "rising"
    SURGING = "surging"


@dataclass
class SentimentResult:
    """情感分析结果"""
    score: float  # -1 到 1
    level: SentimentLevel
    confidence: float
    positive_words: List[str]
    negative_words: List[str]
    
    def to_dict(self) -> Dict:
        return {
            'score': round(self.score, 4),
            'level': self.level.name,
            'level_value': self.level.value,
            'confidence': round(self.confidence, 4),
            'positive_words': self.positive_words[:10],
            'negative_words': self.negative_words[:10]
        }


@dataclass
class HotTopic:
    """热点话题"""
    topic_id: str
    keywords: List[str]
    title: str
    heat_score: float
    level: HotLevel
    trend: TrendDirection
    sample_texts: List[str]
    first_seen: datetime
    last_updated: datetime
    source_count: Dict[str, int]  # 各平台来源数量
    sentiment: Optional[SentimentResult] = None
    related_topics: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            'topic_id': self.topic_id,
            'keywords': self.keywords,
            'title': self.title,
            'heat_score': round(self.heat_score, 2),
            'level': self.level.name,
            'trend': self.trend.value,
            'sample_texts': self.sample_texts[:5],
            'first_seen': self.first_seen.isoformat(),
            'last_updated': self.last_updated.isoformat(),
            'source_count': self.source_count,
            'sentiment': self.sentiment.to_dict() if self.sentiment else None,
            'related_topics': self.related_topics
        }


@dataclass
class PropagationNode:
    """传播节点"""
    node_id: str
    content: str
    author: str
    platform: str
    timestamp: datetime
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    depth: int = 0
    influence_score: float = 0.0


@dataclass
class PropagationChain:
    """传播链"""
    chain_id: str
    root_node: PropagationNode
    total_nodes: int
    max_depth: int
    platforms: Set[str]
    time_span: timedelta
    key_spreaders: List[str]  # 关键传播者
    
    def to_dict(self) -> Dict:
        return {
            'chain_id': self.chain_id,
            'root_content': self.root_node.content[:100],
            'root_author': self.root_node.author,
            'total_nodes': self.total_nodes,
            'max_depth': self.max_depth,
            'platforms': list(self.platforms),
            'time_span_hours': self.time_span.total_seconds() / 3600,
            'key_spreaders': self.key_spreaders[:10]
        }


class SentimentAnalyzer:
    """情感分析器"""
    
    # 正面词典
    POSITIVE_WORDS = {
        '好', '棒', '赞', '优秀', '喜欢', '爱', '支持', '推荐', '感谢', '厉害',
        '完美', '精彩', '出色', '满意', '开心', '高兴', '美', '帅', '酷', '强',
        '牛', '绝', '妙', '佳', '善', '良', '优', '益', '利', '胜',
        '成功', '进步', '发展', '创新', '突破', '领先', '卓越', '杰出', '非凡', '辉煌',
        '希望', '信心', '积极', '乐观', '向上', '正能量', '温暖', '感动', '振奋', '鼓舞'
    }
    
    # 负面词典
    NEGATIVE_WORDS = {
        '差', '烂', '坏', '垃圾', '讨厌', '恨', '反对', '失望', '愤怒', '难过',
        '糟糕', '无语', '崩溃', '恶心', '可怕', '危险', '严重', '问题', '错误', '失败',
        '骗', '假', '黑', '毒', '害', '损', '亏', '败', '惨', '悲',
        '质疑', '批评', '谴责', '抗议', '投诉', '曝光', '丑闻', '黑幕', '造假', '欺骗',
        '担忧', '焦虑', '恐惧', '绝望', '悲观', '消极', '负面', '低迷', '萧条', '危机'
    }
    
    # 程度副词
    DEGREE_WORDS = {
        '非常': 2.0, '特别': 2.0, '极其': 2.5, '超级': 2.0, '太': 1.8,
        '很': 1.5, '十分': 1.8, '相当': 1.5, '比较': 1.2, '有点': 0.8,
        '稍微': 0.6, '略微': 0.5, '不太': 0.4, '不怎么': 0.3
    }
    
    # 否定词
    NEGATION_WORDS = {'不', '没', '无', '非', '别', '勿', '未', '莫', '否', '难以'}
    
    def __init__(self):
        self.positive_set = self.POSITIVE_WORDS.copy()
        self.negative_set = self.NEGATIVE_WORDS.copy()
    
    def add_positive_words(self, words: List[str]):
        """添加正面词"""
        self.positive_set.update(words)
    
    def add_negative_words(self, words: List[str]):
        """添加负面词"""
        self.negative_set.update(words)
    
    def analyze(self, text: str) -> SentimentResult:
        """分析文本情感"""
        if not text:
            return SentimentResult(0.0, SentimentLevel.NEUTRAL, 0.0, [], [])
        
        # 分词
        words = list(jieba.cut(text))
        
        positive_found = []
        negative_found = []
        score = 0.0
        total_weight = 0.0
        
        i = 0
        while i < len(words):
            word = words[i]
            weight = 1.0
            negated = False
            
            # 检查前面的程度词和否定词
            if i > 0:
                prev_word = words[i - 1]
                if prev_word in self.DEGREE_WORDS:
                    weight = self.DEGREE_WORDS[prev_word]
                if prev_word in self.NEGATION_WORDS:
                    negated = True
                
                # 检查前两个词
                if i > 1:
                    prev2 = words[i - 2]
                    if prev2 in self.NEGATION_WORDS:
                        negated = not negated
                    if prev2 in self.DEGREE_WORDS:
                        weight *= self.DEGREE_WORDS[prev2]
            
            # 判断情感
            if word in self.positive_set:
                if negated:
                    score -= weight
                    negative_found.append(word)
                else:
                    score += weight
                    positive_found.append(word)
                total_weight += weight
            elif word in self.negative_set:
                if negated:
                    score += weight * 0.5  # 否定负面词不完全变正面
                    positive_found.append(word)
                else:
                    score -= weight
                    negative_found.append(word)
                total_weight += weight
            
            i += 1
        
        # 归一化
        if total_weight > 0:
            normalized_score = score / total_weight
            normalized_score = max(-1, min(1, normalized_score))  # 限制在[-1, 1]
        else:
            normalized_score = 0.0
        
        # 确定情感级别
        if normalized_score >= 0.6:
            level = SentimentLevel.VERY_POSITIVE
        elif normalized_score >= 0.2:
            level = SentimentLevel.POSITIVE
        elif normalized_score <= -0.6:
            level = SentimentLevel.VERY_NEGATIVE
        elif normalized_score <= -0.2:
            level = SentimentLevel.NEGATIVE
        else:
            level = SentimentLevel.NEUTRAL
        
        # 置信度
        confidence = min(1.0, total_weight / max(len(words), 1) * 5)
        
        return SentimentResult(
            score=normalized_score,
            level=level,
            confidence=confidence,
            positive_words=positive_found,
            negative_words=negative_found
        )
    
    def analyze_batch(self, texts: List[str]) -> List[SentimentResult]:
        """批量分析"""
        return [self.analyze(text) for text in texts]
    
    def get_trend(
        self,
        results: List[Tuple[datetime, SentimentResult]]
    ) -> Dict[str, Any]:
        """分析情感趋势"""
        if not results:
            return {'trend': 'unknown', 'data': []}
        
        # 按时间排序
        sorted_results = sorted(results, key=lambda x: x[0])
        
        # 计算滑动平均
        window_size = min(5, len(sorted_results))
        scores = [r[1].score for r in sorted_results]
        
        trend_data = []
        for i in range(len(scores)):
            start = max(0, i - window_size + 1)
            window = scores[start:i + 1]
            avg = sum(window) / len(window)
            trend_data.append({
                'timestamp': sorted_results[i][0].isoformat(),
                'score': sorted_results[i][1].score,
                'moving_avg': round(avg, 4)
            })
        
        # 判断趋势
        if len(scores) >= 3:
            recent = scores[-3:]
            older = scores[:3]
            recent_avg = sum(recent) / len(recent)
            older_avg = sum(older) / len(older)
            diff = recent_avg - older_avg
            
            if diff > 0.3:
                trend = 'improving'
            elif diff < -0.3:
                trend = 'declining'
            else:
                trend = 'stable'
        else:
            trend = 'insufficient_data'
        
        return {
            'trend': trend,
            'current_avg': round(sum(scores[-min(5, len(scores)):]) / min(5, len(scores)), 4),
            'overall_avg': round(sum(scores) / len(scores), 4),
            'data': trend_data
        }


class HotTopicTracker:
    """热点话题追踪器"""
    
    def __init__(
        self,
        min_cluster_size: int = 5,
        similarity_threshold: float = 0.3,
        decay_hours: int = 24
    ):
        self.min_cluster_size = min_cluster_size
        self.similarity_threshold = similarity_threshold
        self.decay_hours = decay_hours
        
        self.topics: Dict[str, HotTopic] = {}
        self.text_buffer: List[Dict] = []
        self.vectorizer = TfidfVectorizer(
            tokenizer=lambda x: list(jieba.cut(x)),
            max_features=5000,
            stop_words=self._load_stopwords()
        )
        self.sentiment_analyzer = SentimentAnalyzer()
        
        self._lock = threading.Lock()
    
    def _load_stopwords(self) -> List[str]:
        """加载停用词"""
        return [
            '的', '了', '是', '在', '我', '有', '和', '就', '不', '人',
            '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去',
            '你', '会', '着', '没有', '看', '好', '自己', '这', '那', '他',
            '她', '它', '我们', '你们', '他们', '什么', '怎么', '为什么', '哪里', '谁'
        ]
    
    def add_text(
        self,
        text: str,
        platform: str,
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict] = None
    ):
        """添加文本到缓冲区"""
        with self._lock:
            self.text_buffer.append({
                'text': text,
                'platform': platform,
                'timestamp': timestamp or datetime.now(),
                'metadata': metadata or {}
            })
    
    def detect_topics(self, min_texts: int = 20) -> List[HotTopic]:
        """检测热点话题"""
        with self._lock:
            if len(self.text_buffer) < min_texts:
                return []
            
            texts = [item['text'] for item in self.text_buffer]
            
            try:
                # TF-IDF向量化
                tfidf_matrix = self.vectorizer.fit_transform(texts)
                
                # 聚类
                n_clusters = max(2, len(texts) // 10)
                kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
                clusters = kmeans.fit_predict(tfidf_matrix)
                
                # 分析每个聚类
                new_topics = []
                for cluster_id in range(n_clusters):
                    cluster_indices = [i for i, c in enumerate(clusters) if c == cluster_id]
                    
                    if len(cluster_indices) < self.min_cluster_size:
                        continue
                    
                    # 获取聚类内容
                    cluster_texts = [texts[i] for i in cluster_indices]
                    cluster_items = [self.text_buffer[i] for i in cluster_indices]
                    
                    # 提取关键词
                    combined_text = ' '.join(cluster_texts)
                    keywords = jieba.analyse.extract_tags(combined_text, topK=10)
                    
                    if not keywords:
                        continue
                    
                    # 生成话题ID
                    topic_id = f"topic_{hash('_'.join(keywords[:3])) % 10000:04d}"
                    
                    # 计算热度
                    heat_score = self._calculate_heat(cluster_items)
                    
                    # 分析情感
                    sentiments = self.sentiment_analyzer.analyze_batch(cluster_texts[:50])
                    avg_sentiment = sum(s.score for s in sentiments) / len(sentiments)
                    
                    # 来源统计
                    source_count = Counter(item['platform'] for item in cluster_items)
                    
                    # 确定热度级别
                    if heat_score >= 1000:
                        level = HotLevel.EXPLOSIVE
                    elif heat_score >= 500:
                        level = HotLevel.VERY_HOT
                    elif heat_score >= 200:
                        level = HotLevel.HOT
                    elif heat_score >= 50:
                        level = HotLevel.WARM
                    else:
                        level = HotLevel.COLD
                    
                    topic = HotTopic(
                        topic_id=topic_id,
                        keywords=keywords,
                        title=keywords[0] if keywords else "未知话题",
                        heat_score=heat_score,
                        level=level,
                        trend=TrendDirection.STABLE,
                        sample_texts=cluster_texts[:10],
                        first_seen=min(item['timestamp'] for item in cluster_items),
                        last_updated=datetime.now(),
                        source_count=dict(source_count),
                        sentiment=SentimentResult(
                            avg_sentiment,
                            SentimentLevel.NEUTRAL,
                            0.8,
                            [], []
                        )
                    )
                    
                    new_topics.append(topic)
                    self.topics[topic_id] = topic
                
                # 清理缓冲区
                self.text_buffer = []
                
                return sorted(new_topics, key=lambda x: x.heat_score, reverse=True)
                
            except Exception as e:
                logger.error(f"话题检测失败: {e}")
                return []
    
    def _calculate_heat(self, items: List[Dict]) -> float:
        """计算热度分数"""
        now = datetime.now()
        base_score = len(items)
        
        # 时间衰减因子
        time_scores = []
        for item in items:
            hours_ago = (now - item['timestamp']).total_seconds() / 3600
            decay = math.exp(-hours_ago / self.decay_hours)
            time_scores.append(decay)
        
        time_factor = sum(time_scores) / len(time_scores) if time_scores else 0
        
        # 平台多样性加成
        platforms = set(item['platform'] for item in items)
        diversity_bonus = 1 + len(platforms) * 0.1
        
        return base_score * time_factor * diversity_bonus
    
    def update_trends(self):
        """更新话题趋势"""
        now = datetime.now()
        
        for topic_id, topic in list(self.topics.items()):
            # 检查是否过期
            hours_since_update = (now - topic.last_updated).total_seconds() / 3600
            
            if hours_since_update > self.decay_hours * 2:
                # 话题已冷却，降低热度
                topic.heat_score *= 0.5
                if topic.heat_score < 10:
                    del self.topics[topic_id]
                    continue
            
            # 更新趋势
            if hours_since_update < 1:
                topic.trend = TrendDirection.SURGING
            elif hours_since_update < 6:
                topic.trend = TrendDirection.RISING
            elif hours_since_update < 12:
                topic.trend = TrendDirection.STABLE
            else:
                topic.trend = TrendDirection.FALLING
    
    def get_hot_topics(self, limit: int = 20) -> List[Dict]:
        """获取热点话题列表"""
        self.update_trends()
        
        sorted_topics = sorted(
            self.topics.values(),
            key=lambda x: x.heat_score,
            reverse=True
        )
        
        return [t.to_dict() for t in sorted_topics[:limit]]
    
    def get_topic_detail(self, topic_id: str) -> Optional[Dict]:
        """获取话题详情"""
        if topic_id in self.topics:
            return self.topics[topic_id].to_dict()
        return None


class PropagationAnalyzer:
    """传播分析器"""
    
    def __init__(self):
        self.chains: Dict[str, PropagationChain] = {}
        self.nodes: Dict[str, PropagationNode] = {}
    
    def add_content(
        self,
        content_id: str,
        content: str,
        author: str,
        platform: str,
        timestamp: datetime,
        parent_id: Optional[str] = None
    ) -> PropagationNode:
        """添加内容节点"""
        node = PropagationNode(
            node_id=content_id,
            content=content,
            author=author,
            platform=platform,
            timestamp=timestamp,
            parent_id=parent_id
        )
        
        self.nodes[content_id] = node
        
        # 建立关系
        if parent_id and parent_id in self.nodes:
            parent = self.nodes[parent_id]
            parent.children.append(content_id)
            node.depth = parent.depth + 1
        
        return node
    
    def build_chain(self, root_id: str) -> Optional[PropagationChain]:
        """构建传播链"""
        if root_id not in self.nodes:
            return None
        
        root = self.nodes[root_id]
        
        # BFS遍历
        visited = set()
        queue = [root_id]
        all_nodes = []
        max_depth = 0
        platforms = set()
        timestamps = []
        spreader_counts = Counter()
        
        while queue:
            node_id = queue.pop(0)
            if node_id in visited:
                continue
            
            visited.add(node_id)
            node = self.nodes.get(node_id)
            
            if node:
                all_nodes.append(node)
                max_depth = max(max_depth, node.depth)
                platforms.add(node.platform)
                timestamps.append(node.timestamp)
                spreader_counts[node.author] += 1
                
                queue.extend(node.children)
        
        if not all_nodes:
            return None
        
        # 计算时间跨度
        if timestamps:
            time_span = max(timestamps) - min(timestamps)
        else:
            time_span = timedelta()
        
        # 关键传播者
        key_spreaders = [author for author, count in spreader_counts.most_common(10)]
        
        chain = PropagationChain(
            chain_id=f"chain_{root_id}",
            root_node=root,
            total_nodes=len(all_nodes),
            max_depth=max_depth,
            platforms=platforms,
            time_span=time_span,
            key_spreaders=key_spreaders
        )
        
        self.chains[chain.chain_id] = chain
        return chain
    
    def analyze_influence(self, node_id: str) -> float:
        """分析节点影响力"""
        if node_id not in self.nodes:
            return 0.0
        
        node = self.nodes[node_id]
        
        # 基础分数：子节点数量
        direct_influence = len(node.children)
        
        # 递归计算间接影响
        indirect_influence = 0.0
        for child_id in node.children:
            indirect_influence += self.analyze_influence(child_id) * 0.5
        
        node.influence_score = direct_influence + indirect_influence
        return node.influence_score
    
    def find_key_nodes(self, top_n: int = 10) -> List[Dict]:
        """找出关键传播节点"""
        # 计算所有节点影响力
        for node_id in self.nodes:
            self.analyze_influence(node_id)
        
        # 排序
        sorted_nodes = sorted(
            self.nodes.values(),
            key=lambda x: x.influence_score,
            reverse=True
        )[:top_n]
        
        return [{
            'node_id': n.node_id,
            'author': n.author,
            'platform': n.platform,
            'influence_score': round(n.influence_score, 2),
            'direct_spread': len(n.children),
            'content_preview': n.content[:100]
        } for n in sorted_nodes]
    
    def get_propagation_stats(self) -> Dict:
        """获取传播统计"""
        if not self.nodes:
            return {'total_nodes': 0}
        
        platforms = Counter(n.platform for n in self.nodes.values())
        depths = [n.depth for n in self.nodes.values()]
        
        return {
            'total_nodes': len(self.nodes),
            'total_chains': len(self.chains),
            'platforms': dict(platforms),
            'max_depth': max(depths) if depths else 0,
            'avg_depth': round(sum(depths) / len(depths), 2) if depths else 0
        }


class PublicOpinionEngine:
    """舆情分析引擎 - 整合所有分析能力"""
    
    def __init__(self):
        self.sentiment_analyzer = SentimentAnalyzer()
        self.topic_tracker = HotTopicTracker()
        self.propagation_analyzer = PropagationAnalyzer()
        
        self.running = False
        self._analysis_thread: Optional[threading.Thread] = None
    
    def start(self):
        """启动引擎"""
        if self.running:
            return
        
        self.running = True
        self._analysis_thread = threading.Thread(
            target=self._analysis_loop,
            daemon=True
        )
        self._analysis_thread.start()
        logger.info("舆情分析引擎已启动")
    
    def stop(self):
        """停止引擎"""
        self.running = False
        if self._analysis_thread:
            self._analysis_thread.join(timeout=5)
        logger.info("舆情分析引擎已停止")
    
    def _analysis_loop(self):
        """分析循环"""
        while self.running:
            try:
                # 定期检测话题
                self.topic_tracker.detect_topics()
                # 更新趋势
                self.topic_tracker.update_trends()
            except Exception as e:
                logger.error(f"分析循环错误: {e}")
            
            time.sleep(60)  # 每分钟分析一次
    
    def process_content(
        self,
        content: str,
        platform: str,
        author: str = "Unknown",
        content_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ) -> Dict:
        """处理内容 - 综合分析"""
        timestamp = timestamp or datetime.now()
        content_id = content_id or f"{platform}_{hash(content) % 100000:05d}"
        
        # 情感分析
        sentiment = self.sentiment_analyzer.analyze(content)
        
        # 添加到话题追踪
        self.topic_tracker.add_text(
            text=content,
            platform=platform,
            timestamp=timestamp,
            metadata={'author': author, 'id': content_id}
        )
        
        # 添加到传播分析
        self.propagation_analyzer.add_content(
            content_id=content_id,
            content=content,
            author=author,
            platform=platform,
            timestamp=timestamp,
            parent_id=parent_id
        )
        
        return {
            'content_id': content_id,
            'sentiment': sentiment.to_dict(),
            'processed_at': datetime.now().isoformat()
        }
    
    def get_dashboard_data(self) -> Dict:
        """获取仪表板数据"""
        return {
            'hot_topics': self.topic_tracker.get_hot_topics(10),
            'propagation_stats': self.propagation_analyzer.get_propagation_stats(),
            'key_spreaders': self.propagation_analyzer.find_key_nodes(5),
            'updated_at': datetime.now().isoformat()
        }
    
    def analyze_text(self, text: str) -> Dict:
        """单独分析文本"""
        sentiment = self.sentiment_analyzer.analyze(text)
        keywords = jieba.analyse.extract_tags(text, topK=10, withWeight=True)
        
        return {
            'sentiment': sentiment.to_dict(),
            'keywords': [{'word': w, 'weight': round(s, 4)} for w, s in keywords],
            'word_count': len(list(jieba.cut(text)))
        }


# 全局实例
_opinion_engine: Optional[PublicOpinionEngine] = None


def get_opinion_engine() -> PublicOpinionEngine:
    """获取舆情分析引擎实例"""
    global _opinion_engine
    if _opinion_engine is None:
        _opinion_engine = PublicOpinionEngine()
    return _opinion_engine
