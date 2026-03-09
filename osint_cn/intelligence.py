"""
情报分析引擎
信息提取、威胁评估、态势感知、情报研判
"""

import logging
import re
import hashlib
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Set
import threading
import time

import jieba
import jieba.analyse

logger = logging.getLogger(__name__)


class ThreatLevel(Enum):
    """威胁级别"""
    NONE = 0        # 无威胁
    LOW = 1         # 低威胁
    MEDIUM = 2      # 中等威胁
    HIGH = 3        # 高威胁
    CRITICAL = 4    # 严重威胁


class IntelligenceType(Enum):
    """情报类型"""
    OSINT = "osint"         # 开源情报
    SOCMINT = "socmint"     # 社交媒体情报
    TECHINT = "techint"     # 技术情报
    HUMINT = "humint"       # 人工情报
    FININT = "finint"       # 金融情报
    GEOINT = "geoint"       # 地理情报


class IntelligenceCategory(Enum):
    """情报分类"""
    POLITICAL = "political"         # 政治
    ECONOMIC = "economic"           # 经济
    MILITARY = "military"           # 军事
    TECHNOLOGY = "technology"       # 科技
    SOCIAL = "social"               # 社会
    SECURITY = "security"           # 安全
    CYBER = "cyber"                 # 网络
    INDUSTRY = "industry"           # 行业
    COMPETITOR = "competitor"       # 竞争对手
    REGULATORY = "regulatory"       # 监管


class CredibilityLevel(Enum):
    """可信度级别"""
    CONFIRMED = "A"         # 完全确认
    PROBABLY_TRUE = "B"     # 可能真实
    POSSIBLY_TRUE = "C"     # 或许真实
    DOUBTFUL = "D"          # 值得怀疑
    IMPROBABLE = "E"        # 不太可能
    UNVERIFIED = "F"        # 无法核实


class SourceReliability(Enum):
    """来源可靠性"""
    COMPLETELY_RELIABLE = "1"    # 完全可靠
    USUALLY_RELIABLE = "2"       # 通常可靠
    FAIRLY_RELIABLE = "3"        # 相当可靠
    NOT_USUALLY_RELIABLE = "4"   # 通常不可靠
    UNRELIABLE = "5"             # 不可靠
    UNKNOWN = "6"                # 可靠性未知


@dataclass
class IntelligenceItem:
    """情报项"""
    intel_id: str
    title: str
    content: str
    summary: str
    source: str
    source_url: str
    intel_type: IntelligenceType
    category: IntelligenceCategory
    threat_level: ThreatLevel
    credibility: CredibilityLevel
    source_reliability: SourceReliability
    
    # 提取的信息
    entities: List[Dict] = field(default_factory=list)      # 实体
    keywords: List[str] = field(default_factory=list)       # 关键词
    locations: List[str] = field(default_factory=list)      # 地点
    organizations: List[str] = field(default_factory=list)  # 组织
    persons: List[str] = field(default_factory=list)        # 人物
    events: List[str] = field(default_factory=list)         # 事件
    indicators: List[Dict] = field(default_factory=list)    # 指标（IOC等）
    
    # 元数据
    collected_at: datetime = field(default_factory=datetime.now)
    analyzed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    related_intel: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            'intel_id': self.intel_id,
            'title': self.title,
            'content': self.content[:1000],
            'summary': self.summary,
            'source': self.source,
            'source_url': self.source_url,
            'intel_type': self.intel_type.value,
            'category': self.category.value,
            'threat_level': self.threat_level.name,
            'threat_level_value': self.threat_level.value,
            'credibility': self.credibility.value,
            'source_reliability': self.source_reliability.value,
            'entities': self.entities,
            'keywords': self.keywords,
            'locations': self.locations,
            'organizations': self.organizations,
            'persons': self.persons,
            'events': self.events,
            'indicators': self.indicators,
            'collected_at': self.collected_at.isoformat(),
            'analyzed_at': self.analyzed_at.isoformat() if self.analyzed_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'tags': self.tags,
            'related_intel': self.related_intel,
            'metadata': self.metadata
        }


@dataclass
class ThreatIndicator:
    """威胁指标（IOC）"""
    indicator_id: str
    type: str               # ip, domain, url, hash, email, phone, etc.
    value: str
    threat_type: str        # malware, phishing, c2, etc.
    confidence: float       # 0-1
    first_seen: datetime
    last_seen: datetime
    sources: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            'indicator_id': self.indicator_id,
            'type': self.type,
            'value': self.value,
            'threat_type': self.threat_type,
            'confidence': round(self.confidence, 2),
            'first_seen': self.first_seen.isoformat(),
            'last_seen': self.last_seen.isoformat(),
            'sources': self.sources,
            'tags': self.tags
        }


@dataclass
class SituationReport:
    """态势报告"""
    report_id: str
    title: str
    period_start: datetime
    period_end: datetime
    summary: str
    key_findings: List[str]
    threat_assessment: Dict[str, Any]
    trend_analysis: Dict[str, Any]
    recommendations: List[str]
    intel_items: List[str]      # 关联的情报ID
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            'report_id': self.report_id,
            'title': self.title,
            'period_start': self.period_start.isoformat(),
            'period_end': self.period_end.isoformat(),
            'summary': self.summary,
            'key_findings': self.key_findings,
            'threat_assessment': self.threat_assessment,
            'trend_analysis': self.trend_analysis,
            'recommendations': self.recommendations,
            'intel_items_count': len(self.intel_items),
            'created_at': self.created_at.isoformat()
        }


class InformationExtractor:
    """信息提取器"""
    
    # 指标正则模式
    PATTERNS = {
        'ip': re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
        'ipv6': re.compile(r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b'),
        'domain': re.compile(r'\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b'),
        'url': re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+'),
        'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        'phone': re.compile(r'(?:\+86)?1[3-9]\d{9}|\d{3,4}-\d{7,8}'),
        'md5': re.compile(r'\b[a-fA-F0-9]{32}\b'),
        'sha1': re.compile(r'\b[a-fA-F0-9]{40}\b'),
        'sha256': re.compile(r'\b[a-fA-F0-9]{64}\b'),
        'btc_address': re.compile(r'\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b'),
        'cve': re.compile(r'CVE-\d{4}-\d{4,}', re.IGNORECASE),
    }
    
    # 威胁关键词
    THREAT_KEYWORDS = {
        'high': ['攻击', '入侵', '泄露', '漏洞', '恶意', '病毒', '木马', '勒索', '钓鱼', 
                 '黑客', 'APT', '0day', '后门', '数据泄露', '安全事件', '网络攻击'],
        'medium': ['可疑', '异常', '风险', '威胁', '警告', '监控', '追踪', '情报',
                   '调查', '审计', '违规', '漏洞扫描', '渗透'],
        'low': ['更新', '补丁', '修复', '安全', '防护', '监测', '预防', '合规']
    }
    
    # 分类关键词
    CATEGORY_KEYWORDS = {
        IntelligenceCategory.CYBER: ['网络', '黑客', '漏洞', 'APT', '恶意软件', '钓鱼', '勒索'],
        IntelligenceCategory.SECURITY: ['安全', '威胁', '风险', '防护', '攻击', '入侵'],
        IntelligenceCategory.ECONOMIC: ['经济', '金融', '市场', '股票', '投资', '贸易'],
        IntelligenceCategory.POLITICAL: ['政治', '政策', '政府', '选举', '外交', '法规'],
        IntelligenceCategory.TECHNOLOGY: ['技术', '科技', 'AI', '人工智能', '芯片', '5G'],
        IntelligenceCategory.MILITARY: ['军事', '国防', '武器', '军队', '战争'],
        IntelligenceCategory.INDUSTRY: ['行业', '产业', '企业', '公司', '市场份额'],
        IntelligenceCategory.COMPETITOR: ['竞争', '对手', '竞品', '市场分析'],
        IntelligenceCategory.REGULATORY: ['监管', '合规', '法规', '政策', '罚款'],
        IntelligenceCategory.SOCIAL: ['社会', '舆论', '民众', '公众', '媒体']
    }
    
    def __init__(self):
        self.custom_keywords: Dict[str, List[str]] = {}
    
    def add_custom_keywords(self, category: str, keywords: List[str]):
        """添加自定义关键词"""
        if category not in self.custom_keywords:
            self.custom_keywords[category] = []
        self.custom_keywords[category].extend(keywords)
    
    def extract_indicators(self, text: str) -> List[Dict]:
        """提取威胁指标（IOC）"""
        indicators = []
        
        for indicator_type, pattern in self.PATTERNS.items():
            matches = pattern.findall(text)
            for match in set(matches):
                indicators.append({
                    'type': indicator_type,
                    'value': match,
                    'context': self._get_context(text, match)
                })
        
        return indicators
    
    def _get_context(self, text: str, match: str, window: int = 50) -> str:
        """获取匹配项的上下文"""
        pos = text.find(match)
        if pos == -1:
            return ""
        
        start = max(0, pos - window)
        end = min(len(text), pos + len(match) + window)
        return text[start:end]
    
    def extract_keywords(self, text: str, top_k: int = 20) -> List[Tuple[str, float]]:
        """提取关键词"""
        keywords = jieba.analyse.extract_tags(text, topK=top_k, withWeight=True)
        return keywords
    
    def assess_threat_level(self, text: str) -> ThreatLevel:
        """评估威胁级别"""
        text_lower = text.lower()
        
        high_count = sum(1 for kw in self.THREAT_KEYWORDS['high'] if kw in text_lower)
        medium_count = sum(1 for kw in self.THREAT_KEYWORDS['medium'] if kw in text_lower)
        low_count = sum(1 for kw in self.THREAT_KEYWORDS['low'] if kw in text_lower)
        
        # 检查IOC数量
        indicators = self.extract_indicators(text)
        ioc_count = len(indicators)
        
        # 综合评分
        score = high_count * 3 + medium_count * 2 + low_count * 1 + ioc_count * 2
        
        if score >= 10 or high_count >= 3:
            return ThreatLevel.CRITICAL
        elif score >= 6 or high_count >= 2:
            return ThreatLevel.HIGH
        elif score >= 3 or medium_count >= 2:
            return ThreatLevel.MEDIUM
        elif score >= 1:
            return ThreatLevel.LOW
        else:
            return ThreatLevel.NONE
    
    def classify_category(self, text: str) -> IntelligenceCategory:
        """分类情报类别"""
        scores = {}
        
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text)
            scores[category] = score
        
        if not scores or max(scores.values()) == 0:
            return IntelligenceCategory.SECURITY
        
        return max(scores, key=scores.get)
    
    def generate_summary(self, text: str, max_length: int = 200) -> str:
        """生成摘要"""
        # 简单的提取式摘要：选择包含关键词最多的句子
        sentences = re.split(r'[。！？\n]', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        
        if not sentences:
            return text[:max_length]
        
        keywords = [kw for kw, _ in self.extract_keywords(text, top_k=10)]
        
        # 计算每个句子的得分
        sentence_scores = []
        for sent in sentences:
            score = sum(1 for kw in keywords if kw in sent)
            sentence_scores.append((sent, score))
        
        # 选择得分最高的句子
        sorted_sentences = sorted(sentence_scores, key=lambda x: x[1], reverse=True)
        
        summary = ""
        for sent, _ in sorted_sentences:
            if len(summary) + len(sent) <= max_length:
                summary += sent + "。"
            else:
                break
        
        return summary if summary else text[:max_length]


class ThreatIntelligenceManager:
    """威胁情报管理器"""
    
    def __init__(self):
        self.indicators: Dict[str, ThreatIndicator] = {}
        self.indicator_index: Dict[str, Set[str]] = defaultdict(set)  # type -> indicator_ids
        self._lock = threading.Lock()
    
    def add_indicator(
        self,
        indicator_type: str,
        value: str,
        threat_type: str = "unknown",
        confidence: float = 0.5,
        source: str = "unknown",
        tags: List[str] = None
    ) -> str:
        """添加威胁指标"""
        indicator_id = f"ioc_{hashlib.md5(f'{indicator_type}:{value}'.encode()).hexdigest()[:12]}"
        
        with self._lock:
            if indicator_id in self.indicators:
                # 更新现有指标
                existing = self.indicators[indicator_id]
                existing.last_seen = datetime.now()
                existing.confidence = max(existing.confidence, confidence)
                if source not in existing.sources:
                    existing.sources.append(source)
                if tags:
                    existing.tags.extend([t for t in tags if t not in existing.tags])
            else:
                # 创建新指标
                indicator = ThreatIndicator(
                    indicator_id=indicator_id,
                    type=indicator_type,
                    value=value,
                    threat_type=threat_type,
                    confidence=confidence,
                    first_seen=datetime.now(),
                    last_seen=datetime.now(),
                    sources=[source],
                    tags=tags or []
                )
                self.indicators[indicator_id] = indicator
                self.indicator_index[indicator_type].add(indicator_id)
        
        return indicator_id
    
    def check_indicator(self, indicator_type: str, value: str) -> Optional[ThreatIndicator]:
        """检查指标是否存在"""
        indicator_id = f"ioc_{hashlib.md5(f'{indicator_type}:{value}'.encode()).hexdigest()[:12]}"
        return self.indicators.get(indicator_id)
    
    def search_indicators(
        self,
        indicator_type: Optional[str] = None,
        value_pattern: Optional[str] = None,
        min_confidence: float = 0.0
    ) -> List[Dict]:
        """搜索指标"""
        results = []
        
        for indicator in self.indicators.values():
            if indicator_type and indicator.type != indicator_type:
                continue
            if value_pattern and value_pattern not in indicator.value:
                continue
            if indicator.confidence < min_confidence:
                continue
            
            results.append(indicator.to_dict())
        
        return sorted(results, key=lambda x: x['confidence'], reverse=True)
    
    def get_stats(self) -> Dict:
        """获取统计"""
        type_counts = Counter(i.type for i in self.indicators.values())
        threat_counts = Counter(i.threat_type for i in self.indicators.values())
        
        return {
            'total_indicators': len(self.indicators),
            'by_type': dict(type_counts),
            'by_threat': dict(threat_counts),
            'avg_confidence': round(
                sum(i.confidence for i in self.indicators.values()) / max(len(self.indicators), 1),
                2
            )
        }


class IntelligenceAnalyzer:
    """情报分析器"""
    
    def __init__(self):
        self.extractor = InformationExtractor()
        self.threat_intel = ThreatIntelligenceManager()
        self.intel_store: Dict[str, IntelligenceItem] = {}
        self.reports: Dict[str, SituationReport] = {}
        
        # 来源可靠性映射
        self.source_reliability_map: Dict[str, SourceReliability] = {
            'official': SourceReliability.COMPLETELY_RELIABLE,
            'mainstream_media': SourceReliability.USUALLY_RELIABLE,
            'industry_report': SourceReliability.FAIRLY_RELIABLE,
            'social_media': SourceReliability.NOT_USUALLY_RELIABLE,
            'anonymous': SourceReliability.UNRELIABLE,
            'unknown': SourceReliability.UNKNOWN
        }
        
        self.running = False
        self._lock = threading.Lock()
    
    def analyze(
        self,
        content: str,
        source: str = "unknown",
        source_url: str = "",
        intel_type: IntelligenceType = IntelligenceType.OSINT,
        source_category: str = "unknown",
        metadata: Optional[Dict] = None
    ) -> IntelligenceItem:
        """分析情报"""
        intel_id = f"intel_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hashlib.md5(content[:100].encode()).hexdigest()[:8]}"
        
        # 提取关键词
        keywords = [kw for kw, _ in self.extractor.extract_keywords(content, top_k=15)]
        
        # 提取IOC指标
        indicators = self.extractor.extract_indicators(content)
        
        # 评估威胁级别
        threat_level = self.extractor.assess_threat_level(content)
        
        # 分类
        category = self.extractor.classify_category(content)
        
        # 生成摘要
        summary = self.extractor.generate_summary(content)
        
        # 确定来源可靠性
        source_reliability = self.source_reliability_map.get(
            source_category, 
            SourceReliability.UNKNOWN
        )
        
        # 确定可信度（基于来源和内容）
        credibility = self._assess_credibility(content, source_reliability, indicators)
        
        # 提取实体
        entities = self._extract_entities(content)
        
        # 生成标题
        title = self._generate_title(content, keywords)
        
        intel_item = IntelligenceItem(
            intel_id=intel_id,
            title=title,
            content=content,
            summary=summary,
            source=source,
            source_url=source_url,
            intel_type=intel_type,
            category=category,
            threat_level=threat_level,
            credibility=credibility,
            source_reliability=source_reliability,
            entities=entities,
            keywords=keywords,
            locations=entities.get('locations', []),
            organizations=entities.get('organizations', []),
            persons=entities.get('persons', []),
            indicators=indicators,
            analyzed_at=datetime.now(),
            metadata=metadata or {}
        )
        
        # 存储
        with self._lock:
            self.intel_store[intel_id] = intel_item
        
        # 更新威胁情报库
        for indicator in indicators:
            self.threat_intel.add_indicator(
                indicator_type=indicator['type'],
                value=indicator['value'],
                source=source,
                confidence=0.6 if threat_level.value >= 2 else 0.3
            )
        
        return intel_item
    
    def _assess_credibility(
        self,
        content: str,
        source_reliability: SourceReliability,
        indicators: List[Dict]
    ) -> CredibilityLevel:
        """评估可信度"""
        # 基于来源可靠性的基础分数
        reliability_scores = {
            SourceReliability.COMPLETELY_RELIABLE: 5,
            SourceReliability.USUALLY_RELIABLE: 4,
            SourceReliability.FAIRLY_RELIABLE: 3,
            SourceReliability.NOT_USUALLY_RELIABLE: 2,
            SourceReliability.UNRELIABLE: 1,
            SourceReliability.UNKNOWN: 2
        }
        
        score = reliability_scores.get(source_reliability, 2)
        
        # IOC增加可信度
        if len(indicators) >= 3:
            score += 1
        
        # 内容长度和详细程度
        if len(content) >= 500:
            score += 0.5
        
        # 映射到可信度级别
        if score >= 5:
            return CredibilityLevel.CONFIRMED
        elif score >= 4:
            return CredibilityLevel.PROBABLY_TRUE
        elif score >= 3:
            return CredibilityLevel.POSSIBLY_TRUE
        elif score >= 2:
            return CredibilityLevel.DOUBTFUL
        else:
            return CredibilityLevel.IMPROBABLE
    
    def _extract_entities(self, content: str) -> Dict[str, List[str]]:
        """提取实体"""
        import jieba.posseg as pseg
        
        entities = {
            'persons': [],
            'organizations': [],
            'locations': []
        }
        
        words = pseg.cut(content)
        for word, flag in words:
            word = word.strip()
            if len(word) < 2:
                continue
            
            if flag in ('nr', 'nrt', 'nrfg'):
                if word not in entities['persons']:
                    entities['persons'].append(word)
            elif flag in ('nt', 'nto', 'nts', 'nth'):
                if word not in entities['organizations']:
                    entities['organizations'].append(word)
            elif flag in ('ns', 'nsf'):
                if word not in entities['locations']:
                    entities['locations'].append(word)
        
        return entities
    
    def _generate_title(self, content: str, keywords: List[str]) -> str:
        """生成标题"""
        # 取第一句话或前50个字符作为标题基础
        first_sentence = re.split(r'[。！？\n]', content)[0]
        
        if len(first_sentence) <= 50:
            return first_sentence
        
        # 使用关键词组合
        if keywords:
            return f"关于{keywords[0]}的情报 - {keywords[1] if len(keywords) > 1 else ''}"
        
        return content[:50] + "..."
    
    def search_intel(
        self,
        keyword: Optional[str] = None,
        category: Optional[IntelligenceCategory] = None,
        threat_level: Optional[ThreatLevel] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50
    ) -> List[Dict]:
        """搜索情报"""
        results = []
        
        for intel in self.intel_store.values():
            # 关键词过滤
            if keyword and keyword not in intel.content and keyword not in ' '.join(intel.keywords):
                continue
            
            # 类别过滤
            if category and intel.category != category:
                continue
            
            # 威胁级别过滤
            if threat_level and intel.threat_level.value < threat_level.value:
                continue
            
            # 时间过滤
            if start_date and intel.collected_at < start_date:
                continue
            if end_date and intel.collected_at > end_date:
                continue
            
            results.append(intel.to_dict())
        
        # 按时间排序
        results.sort(key=lambda x: x['collected_at'], reverse=True)
        
        return results[:limit]
    
    def generate_situation_report(
        self,
        period_hours: int = 24,
        title: Optional[str] = None
    ) -> SituationReport:
        """生成态势报告"""
        report_id = f"report_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        period_end = datetime.now()
        period_start = period_end - timedelta(hours=period_hours)
        
        # 获取时间段内的情报
        intel_items = [
            intel for intel in self.intel_store.values()
            if intel.collected_at >= period_start
        ]
        
        # 威胁统计
        threat_counts = Counter(intel.threat_level.name for intel in intel_items)
        category_counts = Counter(intel.category.value for intel in intel_items)
        
        # 主要发现
        key_findings = []
        high_threat_intel = [i for i in intel_items if i.threat_level.value >= ThreatLevel.HIGH.value]
        
        for intel in high_threat_intel[:5]:
            key_findings.append(f"[{intel.threat_level.name}] {intel.title}")
        
        if not key_findings:
            key_findings = ["本时段未发现高威胁情报"]
        
        # 威胁评估
        threat_assessment = {
            'total_items': len(intel_items),
            'threat_distribution': dict(threat_counts),
            'category_distribution': dict(category_counts),
            'high_threat_count': len(high_threat_intel),
            'overall_threat_level': self._calculate_overall_threat(intel_items)
        }
        
        # 趋势分析
        trend_analysis = {
            'volume_trend': 'stable',  # TODO: 与历史对比
            'threat_trend': 'stable',
            'top_keywords': self._get_top_keywords(intel_items),
            'active_sources': list(set(i.source for i in intel_items))[:10]
        }
        
        # 建议
        recommendations = self._generate_recommendations(threat_assessment)
        
        report = SituationReport(
            report_id=report_id,
            title=title or f"态势报告 ({period_start.strftime('%Y-%m-%d %H:%M')} - {period_end.strftime('%Y-%m-%d %H:%M')})",
            period_start=period_start,
            period_end=period_end,
            summary=f"本时段共收集{len(intel_items)}条情报，其中高威胁{len(high_threat_intel)}条。",
            key_findings=key_findings,
            threat_assessment=threat_assessment,
            trend_analysis=trend_analysis,
            recommendations=recommendations,
            intel_items=[i.intel_id for i in intel_items]
        )
        
        self.reports[report_id] = report
        return report
    
    def _calculate_overall_threat(self, intel_items: List[IntelligenceItem]) -> str:
        """计算整体威胁级别"""
        if not intel_items:
            return "LOW"
        
        avg_threat = sum(i.threat_level.value for i in intel_items) / len(intel_items)
        
        if avg_threat >= 3:
            return "CRITICAL"
        elif avg_threat >= 2:
            return "HIGH"
        elif avg_threat >= 1:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _get_top_keywords(self, intel_items: List[IntelligenceItem], top_n: int = 10) -> List[str]:
        """获取热门关键词"""
        all_keywords = []
        for intel in intel_items:
            all_keywords.extend(intel.keywords)
        
        keyword_counts = Counter(all_keywords)
        return [kw for kw, _ in keyword_counts.most_common(top_n)]
    
    def _generate_recommendations(self, threat_assessment: Dict) -> List[str]:
        """生成建议"""
        recommendations = []
        
        high_count = threat_assessment.get('high_threat_count', 0)
        overall_level = threat_assessment.get('overall_threat_level', 'LOW')
        
        if overall_level == "CRITICAL":
            recommendations.append("建议立即启动应急响应程序")
            recommendations.append("加强关键系统监控")
        elif overall_level == "HIGH":
            recommendations.append("建议提升安全警戒级别")
            recommendations.append("增加安全巡检频率")
        elif overall_level == "MEDIUM":
            recommendations.append("建议持续关注威胁动态")
        else:
            recommendations.append("当前态势稳定，建议保持常规监控")
        
        if high_count > 5:
            recommendations.append(f"发现{high_count}条高威胁情报，建议重点分析")
        
        return recommendations
    
    def get_dashboard_data(self) -> Dict:
        """获取仪表板数据"""
        now = datetime.now()
        last_24h = now - timedelta(hours=24)
        
        recent_intel = [
            i for i in self.intel_store.values()
            if i.collected_at >= last_24h
        ]
        
        threat_counts = Counter(i.threat_level.name for i in recent_intel)
        category_counts = Counter(i.category.value for i in recent_intel)
        
        return {
            'total_intel': len(self.intel_store),
            'last_24h_count': len(recent_intel),
            'threat_distribution': dict(threat_counts),
            'category_distribution': dict(category_counts),
            'threat_intel_stats': self.threat_intel.get_stats(),
            'recent_high_threats': [
                i.to_dict() for i in recent_intel
                if i.threat_level.value >= ThreatLevel.HIGH.value
            ][:10],
            'top_keywords': self._get_top_keywords(recent_intel),
            'updated_at': now.isoformat()
        }
    
    def get_intel(self, intel_id: str) -> Optional[Dict]:
        """获取情报详情"""
        if intel_id in self.intel_store:
            return self.intel_store[intel_id].to_dict()
        return None
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            'total_intel': len(self.intel_store),
            'total_reports': len(self.reports),
            'threat_intel': self.threat_intel.get_stats()
        }


# 全局实例
_intelligence_analyzer: Optional[IntelligenceAnalyzer] = None


def get_intelligence_analyzer() -> IntelligenceAnalyzer:
    """获取情报分析器实例"""
    global _intelligence_analyzer
    if _intelligence_analyzer is None:
        _intelligence_analyzer = IntelligenceAnalyzer()
    return _intelligence_analyzer
