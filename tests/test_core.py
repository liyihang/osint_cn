"""
OSINT CN 单元测试

测试覆盖：
- 文本处理模块
- 分析模块
- 采集模块
- API 接口
"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock


# ==========================================
# 文本处理模块测试
# ==========================================

class TestTextProcessor:
    """文本处理器测试"""
    
    @pytest.fixture
    def processor(self):
        from processing import TextProcessor
        return TextProcessor()
    
    def test_clean_text_removes_html(self, processor):
        """测试移除 HTML 标签"""
        text = "<p>这是一段<b>测试</b>文本</p>"
        result = processor.clean_text(text)
        assert "<p>" not in result
        assert "<b>" not in result
        assert "测试" in result
    
    def test_clean_text_removes_urls(self, processor):
        """测试移除 URL"""
        text = "访问 https://example.com 获取更多信息"
        result = processor.clean_text(text)
        assert "https://" not in result
        assert "访问" in result
    
    def test_clean_text_removes_mentions(self, processor):
        """测试移除 @ 提及"""
        text = "感谢 @张三 的帮助"
        result = processor.clean_text(text)
        assert "@张三" not in result
    
    def test_segment_chinese_text(self, processor):
        """测试中文分词"""
        text = "我爱北京天安门"
        segments = processor.segment(text)
        assert isinstance(segments, list)
        assert len(segments) > 0
        assert "北京" in segments or "天安门" in segments
    
    def test_segment_empty_text(self, processor):
        """测试空文本分词"""
        result = processor.segment("")
        assert result == []
    
    def test_sentiment_analysis_positive(self, processor):
        """测试正面情感分析"""
        text = "这个产品真的很棒，非常满意"
        result = processor.sentiment_analysis(text)
        assert result.sentiment == "positive"
        assert result.score > 0
    
    def test_sentiment_analysis_negative(self, processor):
        """测试负面情感分析"""
        text = "太差了，非常失望"
        result = processor.sentiment_analysis(text)
        assert result.sentiment == "negative"
        assert result.score < 0
    
    def test_sentiment_analysis_neutral(self, processor):
        """测试中性情感分析"""
        text = "今天是星期一"
        result = processor.sentiment_analysis(text)
        assert result.sentiment == "neutral"
    
    def test_extract_keywords(self, processor):
        """测试关键词提取"""
        text = "人工智能和机器学习正在改变世界，深度学习技术得到广泛应用"
        keywords = processor.extract_keywords(text, top_k=5)
        assert len(keywords) > 0
        assert all(hasattr(kw, 'keyword') for kw in keywords)
        assert all(hasattr(kw, 'weight') for kw in keywords)
    
    def test_extract_keywords_empty(self, processor):
        """测试空文本关键词提取"""
        result = processor.extract_keywords("")
        assert result == []
    
    def test_extract_entities(self, processor):
        """测试命名实体识别"""
        text = "张三在北京工作，他在阿里巴巴公司上班"
        entities = processor.extract_entities(text)
        assert isinstance(entities, dict)
        assert 'person' in entities
        assert 'location' in entities
        assert 'organization' in entities
    
    def test_remove_stopwords(self, processor):
        """测试停用词移除"""
        words = ["我", "爱", "北京", "的", "天安门"]
        result = processor.remove_stopwords(words)
        assert "的" not in result
        assert "北京" in result
    
    def test_word_frequency(self, processor):
        """测试词频统计"""
        text = "人工智能 人工智能 机器学习 深度学习 人工智能"
        freq = processor.word_frequency(text, top_k=3)
        assert len(freq) > 0
        assert freq[0][1] >= freq[-1][1]  # 确保按频率排序
    
    def test_similarity(self, processor):
        """测试文本相似度"""
        text1 = "人工智能改变世界"
        text2 = "人工智能正在改变世界"
        text3 = "今天天气真好"
        
        sim1 = processor.similarity(text1, text2)
        sim2 = processor.similarity(text1, text3)
        
        assert sim1 > sim2  # 相似文本得分应更高
        assert 0 <= sim1 <= 1
        assert 0 <= sim2 <= 1


# ==========================================
# 分析模块测试
# ==========================================

class TestOSINTAnalyzer:
    """OSINT 分析器测试"""
    
    @pytest.fixture
    def analyzer(self):
        from osint_cn.analysis import OSINTAnalyzer
        from processing import TextProcessor
        return OSINTAnalyzer(TextProcessor())
    
    @pytest.fixture
    def sample_data(self):
        return [
            {"content": "这个产品真的很棒", "author": "用户A", "likes": 100, "publish_time": "2024-01-01"},
            {"content": "太差了，非常失望", "author": "用户B", "likes": 50, "publish_time": "2024-01-02"},
            {"content": "一般般吧，没什么特别", "author": "用户C", "likes": 30, "publish_time": "2024-01-03"},
        ]
    
    def test_sentiment_analysis(self, analyzer, sample_data):
        """测试批量情感分析"""
        texts = [item['content'] for item in sample_data]
        result = analyzer.sentiment_analysis(texts)
        
        assert result.analysis_type == 'sentiment'
        assert 'statistics' in result.data
        assert 'positive_count' in result.data['statistics']
        assert 'negative_count' in result.data['statistics']
    
    def test_trend_analysis(self, analyzer, sample_data):
        """测试趋势分析"""
        result = analyzer.trend_analysis(sample_data)
        
        assert result.analysis_type == 'trend'
        assert 'time_series' in result.data
        assert 'growth_rate' in result.data
    
    def test_risk_assessment(self, analyzer, sample_data):
        """测试风险评估"""
        result = analyzer.risk_assessment(sample_data)
        
        assert result.analysis_type == 'risk_assessment'
        assert 'risk_level' in result.data
        assert 'risk_score' in result.data
        assert result.data['risk_level'] in ['low', 'medium', 'high', 'critical']
    
    def test_risk_assessment_with_keywords(self, analyzer):
        """测试包含风险关键词的风险评估"""
        data = [
            {"content": "这是一个诈骗项目"},
            {"content": "非法集资需要警惕"},
        ]
        result = analyzer.risk_assessment(data)
        
        assert result.data['risk_score'] > 0
        assert len(result.data['risk_factors']) > 0
    
    def test_relationship_analysis(self, analyzer):
        """测试关系网络分析"""
        data = [
            {"author": "用户A", "mentions": ["用户B", "用户C"]},
            {"author": "用户B", "mentions": ["用户A"]},
            {"author": "用户C", "retweet_from": "用户A"},
        ]
        result = analyzer.relationship_analysis(data)
        
        assert result.analysis_type == 'relationship'
        assert 'nodes' in result.data
        assert 'edges' in result.data
        assert len(result.data['nodes']) > 0
    
    def test_comprehensive_analysis(self, analyzer, sample_data):
        """测试综合分析"""
        result = analyzer.comprehensive_analysis(sample_data)
        
        assert 'sentiment' in result
        assert 'trend' in result
        assert 'risk' in result
        assert 'summary' in result


# ==========================================
# 采集模块测试
# ==========================================

class TestCollectors:
    """采集器测试"""
    
    def test_collector_factory_create(self):
        """测试采集器工厂创建"""
        from osint_cn.collection import CollectorFactory
        
        collector = CollectorFactory.create('weibo')
        assert collector.platform_name == 'weibo'
    
    def test_collector_factory_unknown_platform(self):
        """测试未知平台抛出异常"""
        from osint_cn.collection import CollectorFactory
        
        with pytest.raises(ValueError):
            CollectorFactory.create('unknown_platform')
    
    def test_collector_factory_available_platforms(self):
        """测试获取可用平台列表"""
        from osint_cn.collection import CollectorFactory
        
        platforms = CollectorFactory.available_platforms()
        assert 'weibo' in platforms
        assert 'zhihu' in platforms
        assert 'baidu' in platforms
    
    def test_collected_item_dataclass(self):
        """测试采集数据项"""
        from osint_cn.collection import CollectedItem
        
        item = CollectedItem(
            platform='weibo',
            content='测试内容',
            author='测试用户',
            likes=100
        )
        
        assert item.platform == 'weibo'
        assert item.content == '测试内容'
        assert item.likes == 100
    
    @patch('requests.Session.request')
    def test_weibo_collector_with_mock(self, mock_request):
        """测试微博采集器（使用 Mock）"""
        from osint_cn.collection import WeiboCollector
        
        # Mock 响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {
                'cards': [
                    {
                        'card_type': 9,
                        'mblog': {
                            'text': '测试微博内容',
                            'user': {'screen_name': '测试用户', 'id': '12345'},
                            'attitudes_count': 10,
                            'comments_count': 5,
                            'reposts_count': 3
                        }
                    }
                ]
            }
        }
        mock_request.return_value = mock_response
        
        collector = WeiboCollector()
        items = collector.collect('测试', limit=1)
        
        # 验证返回结果
        assert isinstance(items, list)


# ==========================================
# API 接口测试
# ==========================================

class TestAPI:
    """API 接口测试"""
    
    @pytest.fixture
    def client(self):
        from osint_cn.api import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_index(self, client):
        """测试首页"""
        response = client.get('/')
        assert response.status_code == 200
        assert b'OSINT CN' in response.data
    
    def test_health(self, client):
        """测试健康检查"""
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
    
    def test_platforms(self, client):
        """测试平台列表"""
        response = client.get('/api/platforms')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'platforms' in data
        assert 'weibo' in data['platforms']
    
    def test_sentiment_api(self, client):
        """测试情感分析 API"""
        response = client.post(
            '/api/sentiment',
            data=json.dumps({'text': '这个产品真的很棒'}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'result' in data
        assert 'sentiment' in data['result']
    
    def test_sentiment_api_missing_text(self, client):
        """测试情感分析 API 缺少参数"""
        response = client.post(
            '/api/sentiment',
            data=json.dumps({}),
            content_type='application/json'
        )
        assert response.status_code == 400
    
    def test_keywords_api(self, client):
        """测试关键词提取 API"""
        response = client.post(
            '/api/keywords',
            data=json.dumps({'text': '人工智能正在改变各行各业'}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'keywords' in data
    
    def test_process_text_api(self, client):
        """测试文本处理 API"""
        response = client.post(
            '/api/process-text',
            data=json.dumps({
                'text': '我爱北京天安门',
                'operations': ['segment', 'clean']
            }),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'result' in data
        assert 'segments' in data['result']
    
    def test_404_handler(self, client):
        """测试 404 错误处理"""
        response = client.get('/nonexistent')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_json_required(self, client):
        """测试非 JSON 请求被拒绝"""
        response = client.post(
            '/api/sentiment',
            data='not json',
            content_type='text/plain'
        )
        assert response.status_code == 400


# ==========================================
# 配置模块测试
# ==========================================

class TestConfig:
    """配置模块测试"""
    
    def test_database_config_from_env(self):
        """测试从环境变量加载数据库配置"""
        import os
        from osint_cn.config import DatabaseConfig
        
        # 设置环境变量
        os.environ['TEST_HOST'] = 'test_host'
        os.environ['TEST_PORT'] = '5433'
        
        config = DatabaseConfig(
            host=os.getenv('TEST_HOST', 'localhost'),
            port=int(os.getenv('TEST_PORT', 5432))
        )
        
        assert config.host == 'test_host'
        assert config.port == 5433
        
        # 清理
        del os.environ['TEST_HOST']
        del os.environ['TEST_PORT']
    
    def test_database_config_to_url(self):
        """测试数据库配置转 URL"""
        from osint_cn.config import DatabaseConfig
        
        config = DatabaseConfig(
            host='localhost',
            port=5432,
            user='user',
            password='pass',
            database='db'
        )
        
        url = config.to_url()
        assert 'postgresql://' in url
        assert 'user:pass' in url
        assert 'localhost:5432' in url
    
    def test_config_to_dict(self):
        """测试配置转字典"""
        from osint_cn.config import Config
        
        config = Config()
        data = config.to_dict()
        
        assert 'debug' in data
        assert 'postgres' in data
        assert 'mongo' in data


# ==========================================
# 运行测试
# ==========================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
