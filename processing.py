import re
import logging
from typing import List, Dict, Tuple, Optional
from collections import Counter
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SentimentResult:
    """情感分析结果"""
    text: str
    sentiment: str  # positive, negative, neutral
    score: float  # -1.0 到 1.0
    confidence: float  # 0.0 到 1.0


@dataclass
class KeywordResult:
    """关键词提取结果"""
    keyword: str
    weight: float
    frequency: int


class TextProcessor:
    """中文文本处理器"""
    
    def __init__(self):
        self._jieba = None
        self._stopwords = None
        self._sentiment_dict = None
    
    @property
    def jieba(self):
        """延迟加载 jieba"""
        if self._jieba is None:
            import jieba
            import jieba.analyse
            self._jieba = jieba
        return self._jieba
    
    @property
    def stopwords(self) -> set:
        """获取停用词"""
        if self._stopwords is None:
            # 常用中文停用词
            self._stopwords = {
                '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
                '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
                '自己', '这', '那', '但', '他', '她', '它', '们', '为', '什么', '这个', '那个',
                '如果', '因为', '所以', '但是', '可以', '可能', '应该', '已经', '正在', '还是',
                '或者', '而且', '以及', '等等', '之后', '之前', '其中', '关于', '对于', '通过'
            }
        return self._stopwords
    
    @property
    def sentiment_dict(self) -> Dict[str, float]:
        """情感词典"""
        if self._sentiment_dict is None:
            # 简化版情感词典
            self._sentiment_dict = {
                # 正面词汇
                '好': 0.8, '棒': 0.9, '优秀': 0.9, '喜欢': 0.7, '爱': 0.8,
                '开心': 0.8, '高兴': 0.8, '快乐': 0.9, '满意': 0.7, '感谢': 0.6,
                '支持': 0.6, '赞': 0.7, '厉害': 0.8, '漂亮': 0.7, '美丽': 0.7,
                '成功': 0.8, '精彩': 0.8, '完美': 0.9, '优质': 0.7, '推荐': 0.6,
                '点赞': 0.7, '牛': 0.7, '帅': 0.6, '酷': 0.6, '给力': 0.8,
                # 负面词汇
                '差': -0.7, '烂': -0.8, '垃圾': -0.9, '讨厌': -0.7, '恨': -0.8,
                '难过': -0.7, '伤心': -0.8, '失望': -0.7, '愤怒': -0.8, '生气': -0.7,
                '糟糕': -0.7, '恶心': -0.8, '无聊': -0.5, '累': -0.4, '烦': -0.6,
                '骗': -0.8, '假': -0.7, '坏': -0.7, '丑': -0.6, '弱': -0.5,
                '失败': -0.7, '可怕': -0.7, '害怕': -0.6, '担心': -0.5, '后悔': -0.6,
            }
        return self._sentiment_dict
    
    def segment(self, text: str, use_paddle: bool = False) -> List[str]:
        """中文分词"""
        if not text:
            return []
        
        # 清理文本
        text = self.clean_text(text)
        
        if use_paddle:
            try:
                import jieba
                jieba.enable_paddle()
                return list(jieba.cut(text, use_paddle=True))
            except Exception:
                pass
        
        return list(self.jieba.cut(text))
    
    def segment_search(self, text: str) -> List[str]:
        """搜索引擎模式分词"""
        text = self.clean_text(text)
        return list(self.jieba.cut_for_search(text))
    
    def clean_text(self, text: str) -> str:
        """清理文本"""
        if not text:
            return ""
        
        # 移除 HTML 标签
        text = re.sub(r'<[^>]+>', '', text)
        # 移除 URL
        text = re.sub(r'https?://\S+', '', text)
        # 移除 @用户
        text = re.sub(r'@\S+', '', text)
        # 移除多余空白
        text = re.sub(r'\s+', ' ', text)
        # 移除表情符号代码
        text = re.sub(r'\[[\u4e00-\u9fa5]+\]', '', text)
        
        return text.strip()
    
    def remove_stopwords(self, words: List[str]) -> List[str]:
        """移除停用词"""
        return [w for w in words if w not in self.stopwords and len(w.strip()) > 0]
    
    def sentiment_analysis(self, text: str) -> SentimentResult:
        """情感分析"""
        if not text:
            return SentimentResult(text="", sentiment="neutral", score=0.0, confidence=0.0)
        
        words = self.segment(text)
        words = self.remove_stopwords(words)
        
        if not words:
            return SentimentResult(text=text, sentiment="neutral", score=0.0, confidence=0.5)
        
        # 计算情感得分
        scores = []
        for word in words:
            if word in self.sentiment_dict:
                scores.append(self.sentiment_dict[word])
        
        if not scores:
            return SentimentResult(text=text, sentiment="neutral", score=0.0, confidence=0.3)
        
        avg_score = sum(scores) / len(scores)
        confidence = min(len(scores) / len(words), 1.0)
        
        # 判断情感倾向
        if avg_score > 0.2:
            sentiment = "positive"
        elif avg_score < -0.2:
            sentiment = "negative"
        else:
            sentiment = "neutral"
        
        return SentimentResult(
            text=text,
            sentiment=sentiment,
            score=round(avg_score, 3),
            confidence=round(confidence, 3)
        )
    
    def extract_keywords(self, text: str, top_k: int = 10, method: str = 'tfidf') -> List[KeywordResult]:
        """提取关键词"""
        if not text:
            return []
        
        text = self.clean_text(text)
        
        if method == 'tfidf':
            keywords = self.jieba.analyse.extract_tags(text, topK=top_k, withWeight=True)
        elif method == 'textrank':
            keywords = self.jieba.analyse.textrank(text, topK=top_k, withWeight=True)
        else:
            keywords = self.jieba.analyse.extract_tags(text, topK=top_k, withWeight=True)
        
        # 统计词频
        words = self.segment(text)
        word_freq = Counter(words)
        
        return [
            KeywordResult(keyword=kw, weight=round(weight, 4), frequency=word_freq.get(kw, 0))
            for kw, weight in keywords
        ]
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """命名实体识别（简化版）"""
        entities = {
            'person': [],
            'location': [],
            'organization': [],
            'time': [],
            'number': [],
        }
        
        if not text:
            return entities
        
        import jieba.posseg as pseg
        
        words = pseg.cut(text)
        for word, flag in words:
            if flag == 'nr':  # 人名
                entities['person'].append(word)
            elif flag == 'ns':  # 地名
                entities['location'].append(word)
            elif flag == 'nt':  # 机构名
                entities['organization'].append(word)
            elif flag == 't':  # 时间
                entities['time'].append(word)
            elif flag == 'm':  # 数词
                entities['number'].append(word)
        
        # 去重
        for key in entities:
            entities[key] = list(set(entities[key]))
        
        return entities
    
    def similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度（基于词汇重叠）"""
        if not text1 or not text2:
            return 0.0
        
        words1 = set(self.segment(text1))
        words2 = set(self.segment(text2))
        
        # Jaccard 相似度
        intersection = words1 & words2
        union = words1 | words2
        
        if not union:
            return 0.0
        
        return len(intersection) / len(union)
    
    def summarize(self, text: str, sentences: int = 3) -> str:
        """文本摘要（提取式）"""
        if not text:
            return ""
        
        # 按句子分割
        sentence_pattern = r'[。！？；\n]+'
        sentence_list = [s.strip() for s in re.split(sentence_pattern, text) if s.strip()]
        
        if len(sentence_list) <= sentences:
            return text
        
        # 计算每个句子的重要性（基于关键词）
        keywords = {kw.keyword for kw in self.extract_keywords(text, top_k=20)}
        
        sentence_scores = []
        for sent in sentence_list:
            words = set(self.segment(sent))
            score = len(words & keywords) / max(len(words), 1)
            sentence_scores.append((sent, score))
        
        # 选择得分最高的句子
        sentence_scores.sort(key=lambda x: x[1], reverse=True)
        top_sentences = [s[0] for s in sentence_scores[:sentences]]
        
        # 按原文顺序排列
        result = [s for s in sentence_list if s in top_sentences]
        
        return '。'.join(result) + '。'
    
    def word_frequency(self, text: str, top_k: int = 50) -> List[Tuple[str, int]]:
        """词频统计"""
        words = self.segment(text)
        words = self.remove_stopwords(words)
        
        # 过滤单字符和纯数字
        words = [w for w in words if len(w) > 1 and not w.isdigit()]
        
        return Counter(words).most_common(top_k)
