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
        from osint_cn.api import (
            app,
            alert_manager,
            collected_data_store,
            analysis_results_store,
            dashboard_pipeline_store,
            monitor_profiles_store,
            monitor_groups_store,
        )
        from osint_cn.security import rate_limiter
        app.config['TESTING'] = True
        app.config['RATELIMIT_ENABLED'] = False
        collected_data_store.clear()
        analysis_results_store.clear()
        dashboard_pipeline_store.clear()
        monitor_profiles_store.clear()
        monitor_groups_store.clear()
        alert_manager.alerts.clear()
        alert_manager.alert_history.clear()
        alert_manager.rule_engine.frequency_tracker.clear()
        rate_limiter._requests.clear()
        with app.test_client() as client:
            yield client
    
    def test_index(self, client):
        """测试首页"""
        response = client.get('/')
        assert response.status_code == 200
        assert b'OSINT CN' in response.data

    def test_dashboard_page_contains_presets_and_large_volume_options(self, client):
        """测试 Dashboard 页面包含场景快捷方案和高采样档位"""
        response = client.get('/dashboard')
        assert response.status_code == 200
        assert '全国主流平台舆情检测中心'.encode('utf-8') in response.data
        assert '品牌舆情'.encode('utf-8') in response.data
        assert '客诉投诉'.encode('utf-8') in response.data
        assert '竞品对比'.encode('utf-8') in response.data
        assert '深度报告'.encode('utf-8') in response.data
        assert '500条/平台'.encode('utf-8') in response.data
    
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
        assert any(item.get('id') == 'weibo' for item in data['platforms'])
    
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

    @patch('osint_cn.api.CollectorFactory.create')
    @patch('osint_cn.api.analyzer.comprehensive_analysis')
    def test_dashboard_pipeline_api(self, mock_analysis, mock_create, client):
        """测试一体化大屏流水线接口"""
        from osint_cn.collection import CollectedItem

        mock_collector = Mock()
        mock_collector.collect.return_value = [
            CollectedItem(
                platform='weibo',
                content='教育集团服务体验不错',
                author='用户A',
                publish_time=datetime.now(),
                likes=12,
                comments=3,
                shares=1
            )
        ]
        mock_create.return_value = mock_collector
        mock_analysis.return_value = {
            'sentiment': {
                'data': {
                    'statistics': {
                        'positive_count': 1,
                        'neutral_count': 0,
                        'negative_count': 0
                    }
                }
            },
            'trend': {'data': {'time_series': [], 'peak_time': None, 'peak_count': 0}},
            'risk': {'data': {'risk_level': 'low', 'risk_score': 8, 'recommendations': ['保持观察']}},
            'summary': {'total_items': 1}
        }

        response = client.post(
            '/api/dashboard/pipeline',
            data=json.dumps({
                'keyword': '教育集团',
                'platforms': ['weibo'],
                'max_items': 10
            }),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['keyword'] == '教育集团'
        assert data['total_items'] >= 1
        assert 'collection_duration_seconds' in data
        assert 'report' in data
        assert 'wordcloud' in data
        assert 'ai_insight' in data['report']
        assert 'action_recommendations' in data['report']['ai_insight']
        assert 'pr_talking_points' in data['report']['ai_insight']

    def test_dashboard_pipeline_missing_keyword(self, client):
        """测试流水线接口缺少关键词"""
        response = client.post(
            '/api/dashboard/pipeline',
            data=json.dumps({'platforms': ['weibo']}),
            content_type='application/json'
        )
        assert response.status_code == 400

    @patch('osint_cn.api.CollectorFactory.create')
    @patch('osint_cn.api.analyzer.comprehensive_analysis')
    def test_dashboard_full_smoke_workflow(self, mock_analysis, mock_create, client):
        """测试 Dashboard 主链路冒烟流程"""
        from osint_cn.collection import CollectedItem

        def fake_collect(keyword, max_items=20, **kwargs):
            if '竞品' in str(keyword):
                return [
                    CollectedItem(platform='weibo', content='竞品服务体验稳定，退款讨论较少', author='用户B', publish_time=datetime.now(), likes=8, comments=2, shares=1)
                ]
            return [
                CollectedItem(platform='weibo', content='品牌退款投诉升温，客服响应需要提速', author='用户A', publish_time=datetime.now(), likes=16, comments=4, shares=2)
            ]

        mock_collector = Mock()
        mock_collector.collect.side_effect = fake_collect
        mock_create.return_value = mock_collector

        def fake_analysis(data):
            joined = ' '.join((item.get('content', '') if isinstance(item, dict) else str(item)) for item in data)
            if '竞品' in joined:
                return {
                    'sentiment': {'data': {'statistics': {'positive_count': 1, 'neutral_count': 0, 'negative_count': 0, 'distribution': {'negative_ratio': 0.1}}}},
                    'trend': {'data': {'time_series': [], 'peak_time': None, 'peak_count': 0}},
                    'risk': {'data': {'risk_level': 'low', 'risk_score': 22, 'recommendations': ['持续观察竞品节奏']}},
                    'summary': {'total_items': 1}
                }
            return {
                'sentiment': {'data': {'statistics': {'positive_count': 0, 'neutral_count': 0, 'negative_count': 1, 'distribution': {'negative_ratio': 0.9}}}},
                'trend': {'data': {'time_series': [], 'peak_time': None, 'peak_count': 0}},
                'risk': {'data': {'risk_level': 'high', 'risk_score': 78, 'recommendations': ['优先处理退款投诉', '统一客服回应口径']}},
                'summary': {'total_items': 1}
            }

        mock_analysis.side_effect = fake_analysis

        dashboard_resp = client.get('/dashboard')
        assert dashboard_resp.status_code == 200
        assert b'data-view="overview"' in dashboard_resp.data
        assert b'data-view="group-overview"' in dashboard_resp.data
        assert b'data-view="competitor-overview"' in dashboard_resp.data

        group_brand_resp = client.post(
            '/api/monitor-groups',
            data=json.dumps({'name': '品牌组', 'description': '品牌主阵地'}),
            content_type='application/json'
        )
        group_brand_id = json.loads(group_brand_resp.data)['group']['group_id']

        group_rival_resp = client.post(
            '/api/monitor-groups',
            data=json.dumps({'name': '竞品组', 'description': '竞品观测'}),
            content_type='application/json'
        )
        group_rival_id = json.loads(group_rival_resp.data)['group']['group_id']

        brand_monitor_resp = client.post(
            '/api/monitors',
            data=json.dumps({
                'name': '品牌监控',
                'keywords': ['品牌A'],
                'platforms': ['weibo'],
                'group_id': group_brand_id,
                'interval_seconds': 600,
                'max_items': 10,
                'thresholds': {'negative_ratio': 0.3, 'risk_score': 50, 'min_items': 1}
            }),
            content_type='application/json'
        )
        brand_monitor_id = json.loads(brand_monitor_resp.data)['monitor']['monitor_id']

        rival_monitor_resp = client.post(
            '/api/monitors',
            data=json.dumps({
                'name': '竞品监控',
                'keywords': ['竞品A'],
                'platforms': ['weibo'],
                'group_id': group_rival_id,
                'interval_seconds': 600,
                'max_items': 10,
                'thresholds': {'negative_ratio': 0.3, 'risk_score': 50, 'min_items': 1}
            }),
            content_type='application/json'
        )
        rival_monitor_id = json.loads(rival_monitor_resp.data)['monitor']['monitor_id']

        pipeline_resp = client.post(
            '/api/dashboard/pipeline',
            data=json.dumps({'keyword': '品牌A', 'platforms': ['weibo'], 'max_items': 10}),
            content_type='application/json'
        )
        assert pipeline_resp.status_code == 200
        pipeline_data = json.loads(pipeline_resp.data)
        pipeline_id = pipeline_data['pipeline_id']
        collection_id = pipeline_data['collection_id']

        brand_run_resp = client.post(f'/api/monitors/{brand_monitor_id}/run')
        rival_run_resp = client.post(f'/api/monitors/{rival_monitor_id}/run')
        assert brand_run_resp.status_code == 200
        assert rival_run_resp.status_code == 200

        collections_resp = client.get('/api/collections')
        collection_detail_resp = client.get(f'/api/collections/{collection_id}?page=1&page_size=20')
        dashboard_data_resp = client.get('/api/dashboard/education')
        realtime_resp = client.get('/api/realtime/data?limit=120')
        report_resp = client.get('/api/report')
        export_docx_resp = client.get(f'/api/reports/{pipeline_id}/export?format=docx')
        export_pdf_resp = client.get(f'/api/reports/{pipeline_id}/export?format=pdf')
        groups_resp = client.get('/api/monitor-groups')
        monitors_resp = client.get('/api/monitors')
        group_overview_resp = client.get('/api/dashboard/groups-overview')
        competitor_overview_resp = client.get(f'/api/dashboard/competitor-overview?base_group_id={group_brand_id}')
        alert_active_resp = client.get('/api/alert/active')
        alert_stats_resp = client.get('/api/alert/stats')
        intel_resp = client.get('/api/intel/stats')

        assert collections_resp.status_code == 200
        assert collection_detail_resp.status_code == 200
        assert dashboard_data_resp.status_code == 200
        assert realtime_resp.status_code == 200
        assert report_resp.status_code == 200
        assert export_docx_resp.status_code == 200
        assert export_pdf_resp.status_code == 200
        assert groups_resp.status_code == 200
        assert monitors_resp.status_code == 200
        assert group_overview_resp.status_code == 200
        assert competitor_overview_resp.status_code == 200
        assert alert_active_resp.status_code == 200
        assert alert_stats_resp.status_code == 200
        assert intel_resp.status_code == 200

        groups_data = json.loads(groups_resp.data)
        monitors_data = json.loads(monitors_resp.data)
        group_overview_data = json.loads(group_overview_resp.data)
        competitor_overview_data = json.loads(competitor_overview_resp.data)
        alert_stats_data = json.loads(alert_stats_resp.data)
        dashboard_data = json.loads(dashboard_data_resp.data)

        assert groups_data['count'] == 2
        assert monitors_data['count'] == 2
        assert dashboard_data['success'] is True
        assert group_overview_data['overview']['group_count'] == 2
        assert competitor_overview_data['overview']['rival_count'] == 1
        assert competitor_overview_data['base_group']['group_id'] == group_brand_id
        assert alert_stats_data['stats']['total_alerts'] >= 1
        assert 'application/pdf' in export_pdf_resp.content_type

    def test_plaintext_ai_report_parser(self):
        """测试将普通文本 AI 输出解析为结构化报告"""
        from osint_cn.api import _extract_plaintext_ai_report

        content = """
        执行摘要：当前讨论集中在售后与退款体验。
        风险判断：负面反馈已有扩散趋势，需要统一回应口径。
        1. 客服 2 小时内完成首轮响应。
        2. 发布退款处理进度说明。
        3. 由品牌团队统一对外回应。
        """
        result = _extract_plaintext_ai_report(content, {'keyword': '测试产品'})

        assert result is not None
        assert result['source'] == 'ai_text'
        assert '售后' in result['executive_summary']
        assert len(result['action_recommendations']) == 3
        assert len(result['pr_talking_points']) == 3

    @patch('osint_cn.api.CollectorFactory.create')
    @patch('osint_cn.api.analyzer.comprehensive_analysis')
    def test_export_report_docx(self, mock_analysis, mock_create, client):
        """测试导出 Word 报告"""
        from osint_cn.collection import CollectedItem

        mock_collector = Mock()
        mock_collector.collect.return_value = [
            CollectedItem(platform='weibo', content='测试导出内容', author='用户A', publish_time=datetime.now())
        ]
        mock_create.return_value = mock_collector
        mock_analysis.return_value = {
            'sentiment': {'data': {'statistics': {'positive_count': 1, 'neutral_count': 0, 'negative_count': 0, 'distribution': {'negative_ratio': 0}}}},
            'trend': {'data': {'time_series': [], 'peak_time': None, 'peak_count': 0}},
            'risk': {'data': {'risk_level': 'low', 'risk_score': 8, 'recommendations': ['保持观察']}},
            'summary': {'total_items': 1}
        }

        pipeline_resp = client.post(
            '/api/dashboard/pipeline',
            data=json.dumps({'keyword': '导出测试', 'platforms': ['weibo'], 'max_items': 10}),
            content_type='application/json'
        )
        pipeline_data = json.loads(pipeline_resp.data)
        export_resp = client.get(f"/api/reports/{pipeline_data['pipeline_id']}/export?format=docx")

        assert export_resp.status_code == 200
        assert 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' in export_resp.content_type

    @patch('osint_cn.api.CollectorFactory.create')
    @patch('osint_cn.api.analyzer.comprehensive_analysis')
    def test_monitor_crud_and_run(self, mock_analysis, mock_create, client):
        """测试监控对象创建、列表和手动执行"""
        from osint_cn.collection import CollectedItem

        mock_collector = Mock()
        mock_collector.collect.return_value = [
            CollectedItem(platform='weibo', content='退款投诉增加', author='用户A', publish_time=datetime.now())
        ]
        mock_create.return_value = mock_collector
        mock_analysis.return_value = {
            'sentiment': {
                'data': {
                    'statistics': {
                        'positive_count': 0,
                        'neutral_count': 0,
                        'negative_count': 1,
                        'distribution': {'negative_ratio': 1.0}
                    }
                }
            },
            'trend': {'data': {'time_series': [], 'peak_time': None, 'peak_count': 0}},
            'risk': {'data': {'risk_level': 'high', 'risk_score': 75, 'recommendations': ['立即处理']}},
            'summary': {'total_items': 1}
        }

        create_resp = client.post(
            '/api/monitors',
            data=json.dumps({
                'name': '品牌客诉监控',
                'keywords': ['品牌A', '产品A'],
                'platforms': ['weibo'],
                'interval_seconds': 600,
                'max_items': 20,
                'thresholds': {'negative_ratio': 0.3, 'risk_score': 50, 'min_items': 1}
            }),
            content_type='application/json'
        )
        assert create_resp.status_code == 201
        create_data = json.loads(create_resp.data)
        monitor_id = create_data['monitor']['monitor_id']

        list_resp = client.get('/api/monitors')
        list_data = json.loads(list_resp.data)
        assert list_resp.status_code == 200
        assert list_data['count'] == 1

        run_resp = client.post(f'/api/monitors/{monitor_id}/run')
        run_data = json.loads(run_resp.data)
        assert run_resp.status_code == 200
        assert run_data['success'] is True
        assert len(run_data['pipeline_ids']) >= 1

    def test_monitor_group_crud(self, client):
        """测试监控分组创建、更新、删除"""
        create_resp = client.post(
            '/api/monitor-groups',
            data=json.dumps({'name': '品牌组', 'description': '品牌舆情监控', 'color': '#00aa88'}),
            content_type='application/json'
        )
        assert create_resp.status_code == 201
        group_data = json.loads(create_resp.data)
        group_id = group_data['group']['group_id']

        list_resp = client.get('/api/monitor-groups')
        list_data = json.loads(list_resp.data)
        assert list_resp.status_code == 200
        assert list_data['count'] == 1

        update_resp = client.put(
            f'/api/monitor-groups/{group_id}',
            data=json.dumps({'name': '品牌重点组'}),
            content_type='application/json'
        )
        update_data = json.loads(update_resp.data)
        assert update_resp.status_code == 200
        assert update_data['group']['name'] == '品牌重点组'

        delete_resp = client.delete(f'/api/monitor-groups/{group_id}')
        assert delete_resp.status_code == 200

    def test_monitor_assign_group(self, client):
        """测试监控对象绑定分组与标签"""
        group_resp = client.post(
            '/api/monitor-groups',
            data=json.dumps({'name': '竞品组'}),
            content_type='application/json'
        )
        group_id = json.loads(group_resp.data)['group']['group_id']

        monitor_resp = client.post(
            '/api/monitors',
            data=json.dumps({
                'name': '竞品监控',
                'keywords': ['竞品A'],
                'platforms': ['weibo'],
                'group_id': group_id,
                'tags': ['竞品', '品牌']
            }),
            content_type='application/json'
        )
        monitor_data = json.loads(monitor_resp.data)
        assert monitor_resp.status_code == 201
        assert monitor_data['monitor']['group_id'] == group_id
        assert monitor_data['monitor']['tags'] == ['竞品', '品牌']

    def test_monitor_max_items_allows_up_to_500(self, client):
        """测试监控对象最大采集量上限提升到 500"""
        monitor_resp = client.post(
            '/api/monitors',
            data=json.dumps({
                'name': '高采样监控',
                'keywords': ['品牌A'],
                'platforms': ['weibo'],
                'max_items': 999
            }),
            content_type='application/json'
        )
        monitor_data = json.loads(monitor_resp.data)
        assert monitor_resp.status_code == 201
        assert monitor_data['monitor']['max_items'] == 500

    @patch('osint_cn.api.CollectorFactory.create')
    @patch('osint_cn.api.analyzer.comprehensive_analysis')
    def test_dashboard_groups_overview_api(self, mock_analysis, mock_create, client):
        """测试分组总览聚合接口"""
        from osint_cn.api import MonitorGroup, MonitorProfile, monitor_groups_store, monitor_profiles_store, dashboard_pipeline_store, analysis_results_store

        group_id = 'group_test_brand'
        pipeline_id = 'pipeline_test_brand'
        analysis_id = 'analysis_test_brand'
        monitor_groups_store[group_id] = MonitorGroup(group_id=group_id, name='品牌组')
        monitor_profiles_store['monitor_test_brand'] = MonitorProfile(
            monitor_id='monitor_test_brand',
            name='品牌监控',
            keywords=['品牌A'],
            platforms=['weibo'],
            group_id=group_id,
            last_pipeline_ids=[pipeline_id]
        )
        dashboard_pipeline_store[pipeline_id] = {
            'created_at': datetime.now().isoformat(),
            'keyword': '品牌A',
            'platforms': ['weibo'],
            'analysis_id': analysis_id,
            'report': {'summary': '品牌组出现退款类投诉升温'},
            'wordcloud': [{'name': '退款', 'value': 5}, {'name': '投诉', 'value': 4}]
        }
        analysis_results_store[analysis_id] = {
            'created_at': datetime.now().isoformat(),
            'source_count': 1,
            'results': {
                'sentiment': {'data': {'statistics': {'distribution': {'negative_ratio': 1.0}}}},
                'risk': {'data': {'risk_score': 66}},
                'summary': {'total_items': 1}
            }
        }

        overview_resp = client.get('/api/dashboard/groups-overview')
        overview_data = json.loads(overview_resp.data)

        assert overview_resp.status_code == 200
        assert overview_data['success'] is True
        assert overview_data['overview']['group_count'] >= 1
        assert any(item['name'] == '品牌组' for item in overview_data['groups'])

    @patch('osint_cn.api.CollectorFactory.create')
    @patch('osint_cn.api.analyzer.comprehensive_analysis')
    def test_dashboard_competitor_overview_api(self, mock_analysis, mock_create, client):
        """测试竞品对比聚合接口"""
        from osint_cn.api import MonitorGroup, MonitorProfile, monitor_groups_store, monitor_profiles_store, dashboard_pipeline_store, analysis_results_store

        brand_group_id = 'group_brand'
        rival_group_id = 'group_rival'
        brand_pipeline_id = 'pipeline_brand'
        rival_pipeline_id = 'pipeline_rival'
        brand_analysis_id = 'analysis_brand'
        rival_analysis_id = 'analysis_rival'

        monitor_groups_store[brand_group_id] = MonitorGroup(group_id=brand_group_id, name='品牌组')
        monitor_groups_store[rival_group_id] = MonitorGroup(group_id=rival_group_id, name='竞品组')
        monitor_profiles_store['monitor_brand'] = MonitorProfile(
            monitor_id='monitor_brand',
            name='品牌监控',
            keywords=['品牌A'],
            platforms=['weibo'],
            group_id=brand_group_id,
            last_pipeline_ids=[brand_pipeline_id]
        )
        monitor_profiles_store['monitor_rival'] = MonitorProfile(
            monitor_id='monitor_rival',
            name='竞品监控',
            keywords=['品牌B'],
            platforms=['weibo'],
            group_id=rival_group_id,
            last_pipeline_ids=[rival_pipeline_id]
        )

        dashboard_pipeline_store[brand_pipeline_id] = {
            'created_at': datetime.now().isoformat(),
            'keyword': '品牌A',
            'platforms': ['weibo'],
            'analysis_id': brand_analysis_id,
            'report': {'summary': '品牌组声量较高，但仍需关注退款讨论'},
            'wordcloud': [{'name': '退款', 'value': 6}, {'name': '服务', 'value': 4}]
        }
        dashboard_pipeline_store[rival_pipeline_id] = {
            'created_at': datetime.now().isoformat(),
            'keyword': '品牌B',
            'platforms': ['weibo'],
            'analysis_id': rival_analysis_id,
            'report': {'summary': '竞品组近期热度追赶明显'},
            'wordcloud': [{'name': '退款', 'value': 3}, {'name': '体验', 'value': 5}]
        }
        analysis_results_store[brand_analysis_id] = {
            'created_at': datetime.now().isoformat(),
            'source_count': 1,
            'results': {
                'sentiment': {'data': {'statistics': {'distribution': {'negative_ratio': 0.25}}}},
                'risk': {'data': {'risk_score': 44}},
                'summary': {'total_items': 12}
            }
        }
        analysis_results_store[rival_analysis_id] = {
            'created_at': datetime.now().isoformat(),
            'source_count': 1,
            'results': {
                'sentiment': {'data': {'statistics': {'distribution': {'negative_ratio': 0.18}}}},
                'risk': {'data': {'risk_score': 36}},
                'summary': {'total_items': 9}
            }
        }

        overview_resp = client.get(f'/api/dashboard/competitor-overview?base_group_id={brand_group_id}')
        overview_data = json.loads(overview_resp.data)

        assert overview_resp.status_code == 200
        assert overview_data['success'] is True
        assert overview_data['base_group']['group_id'] == brand_group_id
        assert overview_data['overview']['rival_count'] == 1
        assert overview_data['comparisons'][0]['rival_name'] == '竞品组'
        assert overview_data['comparisons'][0]['keyword_overlap'] == ['退款']


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
