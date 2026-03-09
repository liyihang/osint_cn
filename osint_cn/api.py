import os
import sys
import logging
import uuid
from collections import Counter, defaultdict
from functools import wraps
from datetime import datetime
from typing import Optional, List

from flask import Flask, jsonify, request, render_template_string, g
from pydantic import ValidationError

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from processing import TextProcessor
from osint_cn.analysis import OSINTAnalyzer
from osint_cn.collection import CollectorFactory
from osint_cn.config import get_config
from osint_cn.models import (
    TextAnalysisRequest, SentimentRequest, KeywordRequest,
    CollectRequest, AnalyzeRequest, TaskCreateRequest,
    SentimentResponse, KeywordResponse, CollectResponse,
    HealthResponse, ErrorResponse, Platform
)
from osint_cn.security import (
    require_api_key, optional_api_key, rate_limit,
    setup_security_middleware, api_key_manager
)
from osint_cn.scheduler import (
    scheduler, TaskType, TaskConfig, TaskStatus
)
from osint_cn.realtime import (
    get_realtime_collector, get_streaming_collector,
    RealtimeCollector, CollectedItem
)
from osint_cn.intelligence import (
    get_intelligence_analyzer, IntelligenceAnalyzer,
    ThreatLevel, IntelligenceType, IntelligenceCategory
)
from osint_cn.relation import (
    get_knowledge_graph, get_social_network,
    KnowledgeGraph, SocialNetworkAnalyzer
)
from osint_cn.alert import (
    get_alert_manager, AlertManager, AlertLevel, AlertRule, RuleType
)
from storage.service import (
    get_storage, CollectionRecord, CollectedItemRecord
)
from osint_cn.batch_collector import (
    get_scheduler, BatchCollectorScheduler, TaskStatus as BatchTaskStatus
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False  # 支持中文 JSON

# 设置安全中间件
setup_security_middleware(app)

# 初始化组件
config = get_config()
text_processor = TextProcessor()
analyzer = OSINTAnalyzer(text_processor)

# 初始化核心模块
realtime_collector = get_realtime_collector()
intelligence_analyzer = get_intelligence_analyzer()
knowledge_graph = get_knowledge_graph()
social_network = get_social_network()
alert_manager = get_alert_manager()
storage_backend = get_storage()

def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in ('1', 'true', 'yes', 'on')


ENABLE_SCHEDULER = _env_flag('ENABLE_SCHEDULER', True)
ENABLE_BACKGROUND_SERVICES = _env_flag('ENABLE_BACKGROUND_SERVICES', True)
ENFORCE_API_KEY = _env_flag('ENFORCE_API_KEY', False)


def _init_background_services() -> None:
    if ENABLE_SCHEDULER:
        try:
            scheduler.start()
            logger.info('Scheduler started')
        except Exception as exc:
            logger.exception(f'Failed to start scheduler: {exc}')
    else:
        logger.info('Scheduler startup disabled by ENABLE_SCHEDULER')

    if ENABLE_BACKGROUND_SERVICES:
        try:
            realtime_collector.start()
            logger.info('Realtime collector started')
        except Exception as exc:
            logger.exception(f'Failed to start realtime collector: {exc}')

        try:
            alert_manager.start()
            logger.info('Alert manager started')
        except Exception as exc:
            logger.exception(f'Failed to start alert manager: {exc}')
    else:
        logger.info('Background services startup disabled by ENABLE_BACKGROUND_SERVICES')


_init_background_services()

# 数据存储（内存，生产环境应使用数据库）
collected_data_store = {}
analysis_results_store = {}


# ============ 错误处理 ============

class APIError(Exception):
    """API 错误"""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code


@app.errorhandler(APIError)
def handle_api_error(error):
    return jsonify({'error': error.message, 'status': 'error'}), error.status_code


@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Not Found',
        'message': '请求的资源不存在',
        'available_endpoints': [
            'GET /',
            'GET /health',
            'GET /api/platforms',
            'POST /api/collect',
            'POST /api/analyze',
            'POST /api/process-text',
            'POST /api/sentiment',
            'POST /api/keywords',
            'GET /api/report'
        ]
    }), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}")
    return jsonify({'error': 'Internal Server Error', 'status': 'error'}), 500


def require_json(f):
    """装饰器：要求 JSON 请求体"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not request.is_json:
            raise APIError('Content-Type must be application/json', 400)
        return f(*args, **kwargs)
    return decorated


def validate_request(model_class):
    """装饰器：使用 Pydantic 模型验证请求"""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            try:
                data = request.get_json() or {}
                validated = model_class(**data)
                g.validated_data = validated
                return f(*args, **kwargs)
            except ValidationError as e:
                errors = []
                for err in e.errors():
                    errors.append({
                        'field': '.'.join(str(x) for x in err['loc']),
                        'message': err['msg'],
                        'type': err['type']
                    })
                return jsonify({
                    'success': False,
                    'error': 'validation_error',
                    'message': '请求参数验证失败',
                    'details': errors
                }), 400
        return decorated
    return decorator


PUBLIC_PATH_PREFIXES = ('/', '/dashboard', '/health')
PUBLIC_API_PATHS = {'/api/platforms'}


@app.before_request
def enforce_api_key_if_needed():
    if not ENFORCE_API_KEY:
        return None

    path = request.path or '/'
    if path in PUBLIC_PATH_PREFIXES or path in PUBLIC_API_PATHS:
        return None

    if path.startswith('/api/'):
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        if not api_key:
            return jsonify({
                'success': False,
                'error': 'unauthorized',
                'message': '生产模式已开启 API Key 强制校验，请提供 X-API-Key'
            }), 401

        key_info = api_key_manager.validate(api_key)
        if not key_info:
            return jsonify({
                'success': False,
                'error': 'forbidden',
                'message': 'API Key 无效或已禁用'
            }), 403

        g.api_key = api_key
        g.api_key_info = key_info

    return None


# ============ 首页和健康检查 ============

# 导入仪表板模板
from osint_cn.dashboard import DASHBOARD_HTML

INDEX_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>OSINT CN - 开源情报系统</title>
    <meta charset="utf-8">
    <meta http-equiv="refresh" content="0; url=/dashboard">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; 
               max-width: 900px; margin: 50px auto; padding: 20px; background: #f5f5f5; text-align: center; }
        a { color: #007bff; text-decoration: none; font-size: 1.2rem; }
    </style>
</head>
<body>
    <h1>🔍 OSINT CN</h1>
    <p>正在跳转到仪表板...</p>
    <p><a href="/dashboard">点击这里手动跳转</a></p>
</body>
</html>
'''

START_TIME = datetime.now()


@app.route('/')
def index():
    """首页"""
    return render_template_string(INDEX_HTML, start_time=START_TIME.strftime('%Y-%m-%d %H:%M:%S'))


@app.route('/dashboard')
def dashboard():
    """仪表板页面"""
    return render_template_string(DASHBOARD_HTML)


@app.route('/health', methods=['GET'])
@rate_limit(limit=100)
def health():
    """健康检查"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0',
        'uptime_seconds': (datetime.now() - START_TIME).total_seconds(),
        'scheduler': scheduler.get_scheduler_info()
    })


# ============ 平台信息 ============

@app.route('/api/platforms', methods=['GET'])
@rate_limit(limit=100)
def get_platforms():
    """获取支持的平台列表"""
    platforms_info = CollectorFactory.get_platform_info()
    return jsonify({
        'success': True,
        'platforms': platforms_info,
        'count': len(platforms_info)
    })


# ============ 数据采集 ============

@app.route('/api/collect', methods=['POST'])
@require_json
@optional_api_key
@rate_limit(limit=30)
def collect():
    """
    数据采集接口
    
    Request:
        {
            "platform": "weibo",
            "keyword": "搜索关键词",
            "max_items": 100
        }
    """
    data = request.json
    
    # 使用 Pydantic 验证
    try:
        req = CollectRequest(**data)
    except ValidationError as e:
        return jsonify({
            'success': False,
            'error': 'validation_error',
            'details': e.errors()
        }), 400
    
    try:
        collector = CollectorFactory.create(req.platform.value)
        items = collector.collect(req.keyword, limit=req.max_items)
        
        # 生成采集 ID 并存储
        collection_id = str(uuid.uuid4())
        
        # 转换为可序列化格式
        results = []
        for item in items:
            item_data = {
                'id': str(uuid.uuid4()),
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
            results.append(item_data)
        
        # 存储采集数据
        collected_data_store[collection_id] = {
            'platform': req.platform.value,
            'keyword': req.keyword,
            'collected_at': datetime.now().isoformat(),
            'items': results
        }

        try:
            collection_record = CollectionRecord(
                id=collection_id,
                platform=req.platform.value,
                keyword=req.keyword,
                collected_at=datetime.now(),
                items_count=len(results),
                metadata={'api_source': 'collect'}
            )
            storage_backend.save_collection(collection_record)

            item_records: List[CollectedItemRecord] = []
            for item_data in results:
                publish_time = None
                if item_data.get('publish_time'):
                    try:
                        publish_time = datetime.fromisoformat(item_data['publish_time'])
                    except Exception:
                        publish_time = None

                item_records.append(CollectedItemRecord(
                    id=item_data['id'],
                    collection_id=collection_id,
                    platform=item_data['platform'],
                    content=item_data['content'],
                    author=item_data.get('author', ''),
                    author_id=item_data.get('author_id', ''),
                    url=item_data.get('url', ''),
                    publish_time=publish_time,
                    likes=item_data.get('likes', 0),
                    comments=item_data.get('comments', 0),
                    shares=item_data.get('shares', 0),
                    metadata=item_data.get('metadata', {})
                ))

            if item_records:
                storage_backend.save_items(collection_id, item_records)
        except Exception as e:
            logger.warning(f"Storage persistence failed, fallback to memory only: {e}")
        
        return jsonify({
            'success': True,
            'collection_id': collection_id,
            'platform': req.platform.value,
            'keyword': req.keyword,
            'items_collected': len(results),
            'data': results[:20]  # 只返回前 20 条
        }), 200
        
    except ValueError as e:
        raise APIError(str(e), 400)
    except Exception as e:
        logger.error(f"Collection error: {e}")
        raise APIError(f'Collection failed: {str(e)}', 500)


@app.route('/api/collections', methods=['GET'])
@optional_api_key
@rate_limit(limit=60)
def list_collections():
    """获取采集记录列表"""
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)

    try:
        records = storage_backend.list_collections(page=page, page_size=page_size)
        collections = [
            {
                'id': r.id,
                'platform': r.platform,
                'keyword': r.keyword,
                'collected_at': r.collected_at.isoformat() if hasattr(r.collected_at, 'isoformat') else r.collected_at,
                'items_count': r.items_count,
                'status': getattr(r, 'status', 'completed')
            }
            for r in records
        ]
        if collections:
            return jsonify({
                'success': True,
                'collections': collections,
                'count': len(collections),
                'page': page,
                'page_size': page_size
            })
    except Exception as e:
        logger.warning(f"Storage list failed, fallback to memory: {e}")

    collections = []
    for cid, data in collected_data_store.items():
        collections.append({
            'id': cid,
            'platform': data['platform'],
            'keyword': data['keyword'],
            'collected_at': data['collected_at'],
            'items_count': len(data['items'])
        })
    
    return jsonify({
        'success': True,
        'collections': collections,
        'count': len(collections)
    })


@app.route('/api/collections/<collection_id>', methods=['GET'])
@optional_api_key
@rate_limit(limit=60)
def get_collection(collection_id):
    """获取采集数据详情"""
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)

    try:
        record = storage_backend.get_collection(collection_id)
        if record:
            rows = storage_backend.get_items(collection_id, page=page, page_size=page_size)
            data_rows = []
            for row in rows:
                data_rows.append({
                    'id': row.id,
                    'platform': row.platform,
                    'content': row.content,
                    'author': row.author,
                    'author_id': row.author_id,
                    'url': row.url,
                    'publish_time': row.publish_time.isoformat() if row.publish_time else None,
                    'likes': row.likes,
                    'comments': row.comments,
                    'shares': row.shares,
                    'metadata': row.metadata,
                    'collected_at': row.created_at.isoformat() if row.created_at else None
                })

            return jsonify({
                'success': True,
                'collection_id': record.id,
                'platform': record.platform,
                'keyword': record.keyword,
                'collected_at': record.collected_at.isoformat() if hasattr(record.collected_at, 'isoformat') else record.collected_at,
                'total': record.items_count,
                'page': page,
                'page_size': page_size,
                'data': data_rows
            })
    except Exception as e:
        logger.warning(f"Storage detail failed, fallback to memory: {e}")

    data = collected_data_store.get(collection_id)
    if not data:
        raise APIError('Collection not found', 404)
    
    items = data['items']
    start = (page - 1) * page_size
    end = start + page_size
    
    return jsonify({
        'success': True,
        'collection_id': collection_id,
        'platform': data['platform'],
        'keyword': data['keyword'],
        'collected_at': data['collected_at'],
        'total': len(items),
        'page': page,
        'page_size': page_size,
        'data': items[start:end]
    })


# ============ 文本处理 ============

@app.route('/api/process-text', methods=['POST'])
@require_json
@optional_api_key
@rate_limit(limit=60)
def process_text():
    """
    文本处理接口
    
    Request:
        {
            "text": "要处理的文本",
            "operations": ["segment", "clean", "entities"]
        }
    """
    data = request.json
    text = data.get('text', '')
    operations = data.get('operations', ['segment', 'clean'])
    
    if not text:
        raise APIError('Missing required field: text')
    
    result = {'original': text}
    
    if 'clean' in operations:
        result['cleaned'] = text_processor.clean_text(text)
    
    if 'segment' in operations:
        words = text_processor.segment(text)
        result['segments'] = words
        result['segments_without_stopwords'] = text_processor.remove_stopwords(words)
    
    if 'entities' in operations:
        result['entities'] = text_processor.extract_entities(text)
    
    return jsonify({
        'success': True,
        'result': result
    }), 200


@app.route('/api/sentiment', methods=['POST'])
@require_json
@optional_api_key
@rate_limit(limit=60)
def sentiment():
    """
    情感分析接口
    
    Request:
        {"text": "文本内容"}
        或
        {"texts": ["文本1", "文本2"]}
    """
    data = request.json
    
    if 'text' in data:
        result = text_processor.sentiment_analysis(data['text'])
        return jsonify({
            'success': True,
            'result': {
                'sentiment': result.sentiment,
                'score': result.score,
                'confidence': result.confidence
            }
        }), 200
    
    elif 'texts' in data:
        texts = data['texts']
        if not isinstance(texts, list):
            raise APIError('texts must be a list')
        
        results = []
        for text in texts:
            result = text_processor.sentiment_analysis(text)
            results.append({
                'text': text[:100],
                'sentiment': result.sentiment,
                'score': result.score,
                'confidence': result.confidence
            })
        
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        }), 200
    
    else:
        raise APIError('Missing required field: text or texts')


@app.route('/api/keywords', methods=['POST'])
@require_json
@optional_api_key
@rate_limit(limit=60)
def keywords():
    """
    关键词提取接口
    
    Request:
        {
            "text": "文本内容",
            "top_k": 10,
            "method": "tfidf"  // tfidf 或 textrank
        }
    """
    data = request.json
    text = data.get('text', '')
    top_k = data.get('top_k', 10)
    method = data.get('method', 'tfidf')
    
    if not text:
        raise APIError('Missing required field: text')
    
    keywords = text_processor.extract_keywords(text, top_k=top_k, method=method)
    
    return jsonify({
        'success': True,
        'keywords': [
            {'keyword': kw.keyword, 'weight': kw.weight, 'frequency': kw.frequency}
            for kw in keywords
        ]
    }), 200


# ============ 数据分析 ============

@app.route('/api/analyze', methods=['POST'])
@require_json
@optional_api_key
@rate_limit(limit=30)
def analyze():
    """
    综合分析接口
    
    Request:
        {
            "data": [
                {"content": "文本1", "author": "作者1", ...},
                {"content": "文本2", "author": "作者2", ...}
            ]
        }
        或
        {
            "collection_id": "采集ID"
        }
    """
    req_data = request.json
    
    # 支持直接传入数据或使用采集 ID
    if 'collection_id' in req_data:
        collection_id = req_data['collection_id']
        stored = collected_data_store.get(collection_id)
        if not stored:
            raise APIError('Collection not found', 404)
        data = stored['items']
    else:
        data = req_data.get('data', [])
    
    if not data:
        raise APIError('Missing required field: data or collection_id')
    
    if not isinstance(data, list):
        raise APIError('data must be a list')
    
    # 执行分析
    results = analyzer.comprehensive_analysis(data)
    
    # 存储分析结果
    analysis_id = str(uuid.uuid4())
    analysis_results_store[analysis_id] = {
        'created_at': datetime.now().isoformat(),
        'source_count': len(data),
        'results': results
    }
    
    return jsonify({
        'success': True,
        'analysis_id': analysis_id,
        'analysis': results
    }), 200


@app.route('/api/analyze/sentiment', methods=['POST'])
@require_json
@optional_api_key
@rate_limit(limit=30)
def analyze_sentiment():
    """批量情感分析"""
    texts = request.json.get('texts', [])
    
    if not texts:
        raise APIError('Missing required field: texts')
    
    result = analyzer.sentiment_analysis(texts)
    
    return jsonify({
        'success': True,
        'result': result.to_dict()
    }), 200


@app.route('/api/analyze/trend', methods=['POST'])
@require_json
@optional_api_key
@rate_limit(limit=30)
def analyze_trend():
    """趋势分析"""
    data = request.json.get('data', [])
    time_field = request.json.get('time_field', 'publish_time')
    interval = request.json.get('interval', 'day')
    
    if not data:
        raise APIError('Missing required field: data')
    
    result = analyzer.trend_analysis(data, time_field=time_field, interval=interval)
    
    return jsonify({
        'success': True,
        'result': result.to_dict()
    }), 200


@app.route('/api/analyze/risk', methods=['POST'])
@require_json
@optional_api_key
@rate_limit(limit=30)
def analyze_risk():
    """风险评估"""
    data = request.json.get('data', [])
    context = request.json.get('context', {})
    
    if not data:
        raise APIError('Missing required field: data')
    
    result = analyzer.risk_assessment(data, context=context)
    
    return jsonify({
        'success': True,
        'result': result.to_dict()
    }), 200


# ============ 任务管理 ============

@app.route('/api/tasks', methods=['GET'])
@optional_api_key
@rate_limit(limit=60)
def list_tasks():
    """获取任务列表"""
    tasks = scheduler.get_all_tasks()
    
    task_list = []
    for task in tasks:
        task_list.append({
            'id': task.id,
            'name': task.name,
            'type': task.task_type.value,
            'status': task.status.value,
            'enabled': task.enabled,
            'schedule': task.schedule,
            'interval_seconds': task.interval_seconds,
            'created_at': task.created_at.isoformat(),
            'last_run': task.last_run.isoformat() if task.last_run else None,
            'next_run': task.next_run.isoformat() if task.next_run else None,
            'run_count': task.run_count
        })
    
    return jsonify({
        'success': True,
        'tasks': task_list,
        'count': len(task_list),
        'scheduler_info': scheduler.get_scheduler_info()
    })


@app.route('/api/tasks', methods=['POST'])
@require_json
@require_api_key
@rate_limit(limit=30)
def create_task():
    """创建任务"""
    data = request.json
    
    name = data.get('name')
    task_type = data.get('task_type', 'collect')
    schedule = data.get('schedule')  # Cron 表达式
    interval_seconds = data.get('interval_seconds')
    config_data = data.get('config', {})
    
    if not name:
        raise APIError('Missing required field: name')
    
    # 解析任务类型
    try:
        task_type_enum = TaskType(task_type)
    except ValueError:
        raise APIError(f'Invalid task_type: {task_type}')
    
    # 创建任务配置
    task_config = TaskConfig(
        platform=config_data.get('platform'),
        keyword=config_data.get('keyword'),
        max_items=config_data.get('max_items', 100),
        analysis_types=config_data.get('analysis_types', ['sentiment', 'keywords']),
        extra=config_data.get('extra', {})
    )
    
    # 创建任务
    task = scheduler.create_task(
        name=name,
        task_type=task_type_enum,
        config=task_config,
        schedule=schedule,
        interval_seconds=interval_seconds,
        enabled=True
    )
    
    return jsonify({
        'success': True,
        'message': 'Task created',
        'task': {
            'id': task.id,
            'name': task.name,
            'type': task.task_type.value,
            'status': task.status.value
        }
    }), 201


@app.route('/api/tasks/<task_id>', methods=['GET'])
@optional_api_key
@rate_limit(limit=60)
def get_task(task_id):
    """获取任务详情"""
    task = scheduler.get_task(task_id)
    if not task:
        raise APIError('Task not found', 404)
    
    # 获取执行历史
    history = scheduler.get_task_history(task_id)
    history_data = []
    for result in history:
        history_data.append({
            'status': result.status.value,
            'started_at': result.started_at.isoformat() if result.started_at else None,
            'finished_at': result.finished_at.isoformat() if result.finished_at else None,
            'duration_seconds': result.duration_seconds,
            'items_processed': result.items_processed,
            'error': result.error_message
        })
    
    return jsonify({
        'success': True,
        'task': {
            'id': task.id,
            'name': task.name,
            'type': task.task_type.value,
            'status': task.status.value,
            'enabled': task.enabled,
            'config': {
                'platform': task.config.platform,
                'keyword': task.config.keyword,
                'max_items': task.config.max_items
            },
            'schedule': task.schedule,
            'interval_seconds': task.interval_seconds,
            'created_at': task.created_at.isoformat(),
            'last_run': task.last_run.isoformat() if task.last_run else None,
            'next_run': task.next_run.isoformat() if task.next_run else None,
            'run_count': task.run_count
        },
        'history': history_data
    })


@app.route('/api/tasks/<task_id>/run', methods=['POST'])
@require_api_key
@rate_limit(limit=10)
def run_task(task_id):
    """立即执行任务"""
    result = scheduler.run_now(task_id)
    if not result:
        raise APIError('Task not found', 404)
    
    return jsonify({
        'success': True,
        'message': 'Task executed',
        'result': {
            'status': result.status.value,
            'items_processed': result.items_processed,
            'duration_seconds': result.duration_seconds,
            'error': result.error_message
        }
    })


@app.route('/api/tasks/<task_id>/pause', methods=['POST'])
@require_api_key
@rate_limit(limit=30)
def pause_task(task_id):
    """暂停任务"""
    if scheduler.pause_task(task_id):
        return jsonify({'success': True, 'message': 'Task paused'})
    raise APIError('Task not found', 404)


@app.route('/api/tasks/<task_id>/resume', methods=['POST'])
@require_api_key
@rate_limit(limit=30)
def resume_task(task_id):
    """恢复任务"""
    if scheduler.resume_task(task_id):
        return jsonify({'success': True, 'message': 'Task resumed'})
    raise APIError('Task not found', 404)


@app.route('/api/tasks/<task_id>', methods=['DELETE'])
@require_api_key
@rate_limit(limit=30)
def delete_task(task_id):
    """删除任务"""
    if scheduler.delete_task(task_id):
        return jsonify({'success': True, 'message': 'Task deleted'})
    raise APIError('Task not found', 404)


# ============ 报告 ============

@app.route('/api/report', methods=['GET'])
@rate_limit(limit=30)
def report():
    """生成系统报告"""
    report_data = {
        'report_time': datetime.now().isoformat(),
        'system_status': 'healthy',
        'available_platforms': CollectorFactory.available_platforms(),
        'features': {
            'collection': ['微博', '知乎', '抖音', '百度', '微信公众号', '小红书', 'B站', '贴吧', '头条'],
            'processing': ['中文分词', '情感分析', '关键词提取', '命名实体识别'],
            'analysis': ['情感统计', '关系网络', '趋势分析', '风险评估']
        },
        'statistics': {
            'uptime_seconds': (datetime.now() - START_TIME).total_seconds(),
            'api_version': '1.0.0',
            'collections_count': len(collected_data_store),
            'analysis_count': len(analysis_results_store),
            'tasks_count': len(scheduler.get_all_tasks())
        }
    }
    
    return jsonify({
        'success': True,
        'report': report_data
    }), 200


@app.route('/api/dashboard/education', methods=['GET'])
@optional_api_key
@rate_limit(limit=60)
def education_dashboard_data():
    """教育舆情大屏聚合数据"""
    province_keywords = [
        '北京', '上海', '天津', '重庆', '河北', '山西', '辽宁', '吉林', '黑龙江', '江苏',
        '浙江', '安徽', '福建', '江西', '山东', '河南', '湖北', '湖南', '广东', '海南',
        '四川', '贵州', '云南', '陕西', '甘肃', '青海', '台湾', '内蒙古', '广西', '西藏',
        '宁夏', '新疆', '香港', '澳门'
    ]

    collection_records = sorted(
        collected_data_store.values(),
        key=lambda x: x.get('collected_at', ''),
        reverse=True
    )

    recent_items = []
    for record in collection_records[:30]:
        for item in record.get('items', [])[:30]:
            merged = {
                'platform': record.get('platform', item.get('platform', 'unknown')),
                'keyword': record.get('keyword', ''),
                **item
            }
            recent_items.append(merged)

    recent_items = recent_items[:400]

    platform_counter = Counter()
    province_counter = Counter()
    sentiment_counter = Counter({'positive': 0, 'neutral': 0, 'negative': 0})
    trend_counter = defaultdict(int)
    heat_total = 0

    for item in recent_items:
        platform = item.get('platform') or 'unknown'
        platform_counter[platform] += 1

        content = (item.get('content') or '').strip()
        for province in province_keywords:
            if province in content:
                province_counter[province] += 1

        likes = int(item.get('likes') or 0)
        comments = int(item.get('comments') or 0)
        shares = int(item.get('shares') or 0)
        heat_total += max(1, likes + comments * 2 + shares * 3)

        if content:
            try:
                result = text_processor.sentiment_analysis(content)
                sentiment_counter[result.sentiment] += 1
            except Exception:
                sentiment_counter['neutral'] += 1

        time_text = item.get('publish_time') or item.get('collected_at')
        if time_text:
            try:
                dt = datetime.fromisoformat(str(time_text).replace('Z', '+00:00'))
                hour_key = f"{dt.hour:02d}:00"
                trend_counter[hour_key] += 1
            except Exception:
                pass

    if not province_counter:
        province_counter.update({
            '北京': 26, '上海': 28, '广东': 24, '江苏': 20,
            '浙江': 18, '山东': 16, '四川': 14, '湖北': 13
        })

    if not trend_counter:
        trend_counter.update({'17:00': 6, '18:00': 8, '19:00': 7, '20:00': 9, '21:00': 8, '22:00': 7, '23:00': 7})

    top_news = []
    for item in recent_items[:12]:
        text = (item.get('content') or '').replace('\n', ' ').strip()
        if not text:
            continue
        top_news.append(text[:80])

    if not top_news:
        top_news = [
            '暂未采集到实时舆情数据，请先创建采集任务。',
            '建议监控关键词：师资、收费、校园安全、课程质量。'
        ]

    active_alerts = []
    try:
        active_alerts = alert_manager.get_active_alerts()
    except Exception:
        active_alerts = []

    alerts_payload = []
    for alert in (active_alerts or [])[:5]:
        if isinstance(alert, dict):
            alerts_payload.append(alert)
        elif hasattr(alert, 'to_dict'):
            alerts_payload.append(alert.to_dict())

    return jsonify({
        'success': True,
        'dashboard': {
            'updated_at': datetime.now().isoformat(),
            'overview': {
                'total_heat': heat_total,
                'collections_count': len(collected_data_store),
                'analysis_count': len(analysis_results_store),
                'active_alerts': len(active_alerts or [])
            },
            'news': top_news,
            'platform_distribution': dict(platform_counter),
            'sentiment': {
                'positive': sentiment_counter['positive'],
                'neutral': sentiment_counter['neutral'],
                'negative': sentiment_counter['negative']
            },
            'trend': dict(sorted(trend_counter.items(), key=lambda x: x[0])),
            'province_heat': [
                {'name': name, 'value': value * 120}
                for name, value in province_counter.most_common()
            ],
            'alerts': alerts_payload
        }
    })


# ============ 分析结果查询 ============

@app.route('/api/analysis/<analysis_id>', methods=['GET'])
@optional_api_key
@rate_limit(limit=60)
def get_analysis(analysis_id):
    """获取分析结果"""
    result = analysis_results_store.get(analysis_id)
    if not result:
        raise APIError('Analysis not found', 404)
    
    return jsonify({
        'success': True,
        'analysis_id': analysis_id,
        'created_at': result['created_at'],
        'source_count': result['source_count'],
        'results': result['results']
    })


# ============ API Key 管理（仅管理员）============

@app.route('/api/keys', methods=['POST'])
@require_api_key
@rate_limit(limit=10)
def create_api_key():
    """创建新的 API Key"""
    from osint_cn.security import api_key_manager
    
    # 检查是否是管理员
    if g.api_key_info.get('role') != 'admin':
        raise APIError('Admin role required', 403)
    
    data = request.json or {}
    name = data.get('name', 'new_key')
    role = data.get('role', 'user')
    rate_limit_val = data.get('rate_limit', 100)
    
    new_key = api_key_manager.generate_key(name, role, rate_limit_val)
    
    return jsonify({
        'success': True,
        'message': 'API Key created',
        'api_key': new_key,
        'note': '请妥善保存此 API Key，它不会再次显示'
    }), 201


# ============ 实时采集 API ============

@app.route('/api/realtime/tasks', methods=['GET'])
@optional_api_key
@rate_limit(limit=60)
def list_realtime_tasks():
    """列出实时采集任务"""
    tasks = realtime_collector.list_tasks()
    return jsonify({
        'success': True,
        'tasks': tasks,
        'stats': realtime_collector.get_stats()
    })


@app.route('/api/realtime/tasks', methods=['POST'])
@require_api_key
@require_json
@rate_limit(limit=20)
def create_realtime_task():
    """创建实时采集任务"""
    data = request.json
    
    platforms = data.get('platforms', ['weibo'])
    keywords = data.get('keywords', [])
    interval = data.get('interval_seconds', 60)
    max_items = data.get('max_items', 100)
    
    if not keywords:
        raise APIError('keywords 不能为空', 400)
    
    task_id = realtime_collector.create_task(
        platforms=platforms,
        keywords=keywords,
        interval_seconds=interval,
        max_items=max_items
    )
    
    return jsonify({
        'success': True,
        'task_id': task_id,
        'message': '实时采集任务已创建'
    }), 201


@app.route('/api/realtime/tasks/<task_id>', methods=['DELETE'])
@require_api_key
@rate_limit(limit=20)
def delete_realtime_task(task_id):
    """删除实时采集任务"""
    if realtime_collector.remove_task(task_id):
        return jsonify({'success': True, 'message': '任务已删除'})
    raise APIError('任务不存在', 404)


@app.route('/api/realtime/tasks/<task_id>/pause', methods=['POST'])
@require_api_key
@rate_limit(limit=20)
def pause_realtime_task(task_id):
    """暂停实时采集任务"""
    if realtime_collector.pause_task(task_id):
        return jsonify({'success': True, 'message': '任务已暂停'})
    raise APIError('任务不存在', 404)


@app.route('/api/realtime/tasks/<task_id>/resume', methods=['POST'])
@require_api_key
@rate_limit(limit=20)
def resume_realtime_task(task_id):
    """恢复实时采集任务"""
    if realtime_collector.resume_task(task_id):
        return jsonify({'success': True, 'message': '任务已恢复'})
    raise APIError('任务不存在', 404)


@app.route('/api/realtime/data', methods=['GET'])
@optional_api_key
@rate_limit(limit=100)
def get_realtime_data():
    """获取实时采集数据"""
    limit = request.args.get('limit', 100, type=int)
    data = realtime_collector.get_buffer_data(max_items=limit)
    return jsonify({
        'success': True,
        'data': data,
        'count': len(data)
    })


# ============ 情报分析 API ============

@app.route('/api/intel/analyze', methods=['POST'])
@require_api_key
@require_json
@rate_limit(limit=60)
def analyze_intelligence():
    """分析情报"""
    data = request.json
    content = data.get('content', '')
    source = data.get('source', 'unknown')
    source_url = data.get('source_url', '')
    intel_type = data.get('intel_type', 'osint')
    source_category = data.get('source_category', 'unknown')
    
    if not content:
        raise APIError('content 不能为空', 400)
    
    # 转换情报类型
    try:
        intel_type_enum = IntelligenceType(intel_type)
    except:
        intel_type_enum = IntelligenceType.OSINT
    
    result = intelligence_analyzer.analyze(
        content=content,
        source=source,
        source_url=source_url,
        intel_type=intel_type_enum,
        source_category=source_category,
        metadata=data.get('metadata')
    )
    
    return jsonify({
        'success': True,
        'intel': result.to_dict()
    })


@app.route('/api/intel/search', methods=['GET'])
@optional_api_key
@rate_limit(limit=60)
def search_intelligence():
    """搜索情报"""
    keyword = request.args.get('keyword')
    category = request.args.get('category')
    threat_level = request.args.get('threat_level')
    limit = request.args.get('limit', 50, type=int)
    
    # 转换参数
    category_enum = None
    if category:
        try:
            category_enum = IntelligenceCategory(category)
        except:
            pass
    
    threat_level_enum = None
    if threat_level:
        try:
            threat_level_enum = ThreatLevel[threat_level.upper()]
        except:
            pass
    
    results = intelligence_analyzer.search_intel(
        keyword=keyword,
        category=category_enum,
        threat_level=threat_level_enum,
        limit=limit
    )
    
    return jsonify({
        'success': True,
        'results': results,
        'count': len(results)
    })


@app.route('/api/intel/<intel_id>', methods=['GET'])
@optional_api_key
@rate_limit(limit=60)
def get_intelligence_detail(intel_id):
    """获取情报详情"""
    detail = intelligence_analyzer.get_intel(intel_id)
    if not detail:
        raise APIError('情报不存在', 404)
    return jsonify({
        'success': True,
        'intel': detail
    })


@app.route('/api/intel/report', methods=['POST'])
@require_api_key
@require_json
@rate_limit(limit=10)
def generate_intel_report():
    """生成态势报告"""
    data = request.json
    period_hours = data.get('period_hours', 24)
    title = data.get('title')
    
    report = intelligence_analyzer.generate_situation_report(
        period_hours=period_hours,
        title=title
    )
    
    return jsonify({
        'success': True,
        'report': report.to_dict()
    })


@app.route('/api/intel/dashboard', methods=['GET'])
@optional_api_key
@rate_limit(limit=60)
def get_intel_dashboard():
    """获取情报仪表板数据"""
    data = intelligence_analyzer.get_dashboard_data()
    return jsonify({
        'success': True,
        'data': data
    })


@app.route('/api/intel/stats', methods=['GET'])
@optional_api_key
@rate_limit(limit=60)
def get_intel_stats():
    """获取情报统计"""
    stats = intelligence_analyzer.get_stats()
    return jsonify({
        'success': True,
        'stats': stats
    })


# ============ 威胁指标 (IOC) API ============

@app.route('/api/ioc/add', methods=['POST'])
@require_api_key
@require_json
@rate_limit(limit=100)
def add_threat_indicator():
    """添加威胁指标"""
    data = request.json
    
    indicator_type = data.get('type')
    value = data.get('value')
    
    if not indicator_type or not value:
        raise APIError('type 和 value 必填', 400)
    
    indicator_id = intelligence_analyzer.threat_intel.add_indicator(
        indicator_type=indicator_type,
        value=value,
        threat_type=data.get('threat_type', 'unknown'),
        confidence=data.get('confidence', 0.5),
        source=data.get('source', 'api'),
        tags=data.get('tags', [])
    )
    
    return jsonify({
        'success': True,
        'indicator_id': indicator_id
    }), 201


@app.route('/api/ioc/check', methods=['POST'])
@optional_api_key
@require_json
@rate_limit(limit=200)
def check_threat_indicator():
    """检查威胁指标"""
    data = request.json
    
    indicator_type = data.get('type')
    value = data.get('value')
    
    if not indicator_type or not value:
        raise APIError('type 和 value 必填', 400)
    
    indicator = intelligence_analyzer.threat_intel.check_indicator(indicator_type, value)
    
    return jsonify({
        'success': True,
        'found': indicator is not None,
        'indicator': indicator.to_dict() if indicator else None
    })


@app.route('/api/ioc/search', methods=['GET'])
@optional_api_key
@rate_limit(limit=60)
def search_threat_indicators():
    """搜索威胁指标"""
    indicator_type = request.args.get('type')
    value_pattern = request.args.get('pattern')
    min_confidence = request.args.get('min_confidence', 0.0, type=float)
    
    results = intelligence_analyzer.threat_intel.search_indicators(
        indicator_type=indicator_type,
        value_pattern=value_pattern,
        min_confidence=min_confidence
    )
    
    return jsonify({
        'success': True,
        'indicators': results,
        'count': len(results)
    })


@app.route('/api/ioc/stats', methods=['GET'])
@optional_api_key
@rate_limit(limit=60)
def get_ioc_stats():
    """获取威胁指标统计"""
    stats = intelligence_analyzer.threat_intel.get_stats()
    return jsonify({
        'success': True,
        'stats': stats
    })


# ============ 关系挖掘 API ============

@app.route('/api/graph/add', methods=['POST'])
@require_api_key
@require_json
@rate_limit(limit=60)
def add_to_graph():
    """添加文档到知识图谱"""
    data = request.json
    text = data.get('text', '')
    source = data.get('source', 'unknown')
    author = data.get('author')
    
    if not text:
        raise APIError('text 不能为空', 400)
    
    result = knowledge_graph.add_document(
        text=text,
        source=source,
        author=author,
        metadata=data.get('metadata')
    )
    
    return jsonify({
        'success': True,
        'result': result
    })


@app.route('/api/graph/entity/<name>', methods=['GET'])
@optional_api_key
@rate_limit(limit=60)
def query_entity(name):
    """查询实体"""
    result = knowledge_graph.query_entity(name)
    if not result:
        raise APIError('实体不存在', 404)
    return jsonify({
        'success': True,
        'result': result
    })


@app.route('/api/graph/subgraph/<entity_id>', methods=['GET'])
@optional_api_key
@rate_limit(limit=30)
def get_subgraph(entity_id):
    """获取子图"""
    depth = request.args.get('depth', 2, type=int)
    max_nodes = request.args.get('max_nodes', 100, type=int)
    
    result = knowledge_graph.get_subgraph(entity_id, depth=depth, max_nodes=max_nodes)
    return jsonify({
        'success': True,
        'subgraph': result
    })


@app.route('/api/graph/path', methods=['GET'])
@optional_api_key
@rate_limit(limit=30)
def find_entity_path():
    """查找实体之间的路径"""
    source_id = request.args.get('source')
    target_id = request.args.get('target')
    
    if not source_id or not target_id:
        raise APIError('source 和 target 参数必填', 400)
    
    path = knowledge_graph.find_path(source_id, target_id)
    return jsonify({
        'success': True,
        'path': path,
        'found': path is not None
    })


@app.route('/api/graph/stats', methods=['GET'])
@optional_api_key
@rate_limit(limit=60)
def get_graph_stats():
    """获取图谱统计"""
    stats = knowledge_graph.get_stats()
    return jsonify({
        'success': True,
        'stats': stats
    })


@app.route('/api/graph/export/neo4j', methods=['GET'])
@require_api_key
@rate_limit(limit=10)
def export_to_neo4j():
    """导出为 Neo4j 格式"""
    data = knowledge_graph.export_for_neo4j()
    return jsonify({
        'success': True,
        'data': data
    })


# ============ 社交网络分析 API ============

@app.route('/api/social/user', methods=['POST'])
@require_api_key
@require_json
@rate_limit(limit=60)
def add_social_user():
    """添加社交用户"""
    data = request.json
    
    user_id = data.get('user_id')
    username = data.get('username')
    platform = data.get('platform', 'unknown')
    
    if not user_id or not username:
        raise APIError('user_id 和 username 必填', 400)
    
    node = social_network.add_user(
        user_id=user_id,
        username=username,
        platform=platform,
        followers=data.get('followers', 0),
        following=data.get('following', 0),
        posts=data.get('posts', 0)
    )
    
    return jsonify({
        'success': True,
        'user': node.to_dict()
    })


@app.route('/api/social/interaction', methods=['POST'])
@require_api_key
@require_json
@rate_limit(limit=100)
def add_social_interaction():
    """添加社交互动"""
    data = request.json
    
    source_id = data.get('source_id')
    target_id = data.get('target_id')
    weight = data.get('weight', 1.0)
    
    if not source_id or not target_id:
        raise APIError('source_id 和 target_id 必填', 400)
    
    social_network.add_interaction(source_id, target_id, weight)
    
    return jsonify({
        'success': True,
        'message': '互动关系已添加'
    })


@app.route('/api/social/influence', methods=['GET'])
@optional_api_key
@rate_limit(limit=30)
def calculate_influence():
    """计算影响力"""
    ranks = social_network.calculate_pagerank()
    return jsonify({
        'success': True,
        'ranks': {k: round(v, 6) for k, v in sorted(ranks.items(), key=lambda x: x[1], reverse=True)[:50]}
    })


@app.route('/api/social/communities', methods=['GET'])
@optional_api_key
@rate_limit(limit=30)
def detect_communities():
    """社区检测"""
    min_size = request.args.get('min_size', 3, type=int)
    communities = social_network.detect_communities(min_community_size=min_size)
    return jsonify({
        'success': True,
        'communities': communities,
        'count': len(communities)
    })


@app.route('/api/social/connectors', methods=['GET'])
@optional_api_key
@rate_limit(limit=30)
def find_key_connectors():
    """找出关键连接者"""
    top_n = request.args.get('top', 10, type=int)
    connectors = social_network.find_key_connectors(top_n=top_n)
    return jsonify({
        'success': True,
        'connectors': connectors
    })


@app.route('/api/social/network/<user_id>', methods=['GET'])
@optional_api_key
@rate_limit(limit=30)
def get_user_network(user_id):
    """获取用户社交网络"""
    depth = request.args.get('depth', 2, type=int)
    network = social_network.get_user_network(user_id, depth=depth)
    return jsonify({
        'success': True,
        'network': network
    })


@app.route('/api/social/stats', methods=['GET'])
@optional_api_key
@rate_limit(limit=60)
def get_social_stats():
    """获取社交网络统计"""
    stats = social_network.get_stats()
    return jsonify({
        'success': True,
        'stats': stats
    })


# ============ 风险预警 API ============

@app.route('/api/alert/rules', methods=['GET'])
@optional_api_key
@rate_limit(limit=60)
def list_alert_rules():
    """列出预警规则"""
    rules = alert_manager.rule_engine.list_rules()
    return jsonify({
        'success': True,
        'rules': rules,
        'count': len(rules)
    })


@app.route('/api/alert/rules', methods=['POST'])
@require_api_key
@require_json
@rate_limit(limit=20)
def create_alert_rule():
    """创建预警规则"""
    data = request.json
    
    name = data.get('name')
    rule_type = data.get('type', 'keyword')
    level = data.get('level', 'WARNING')
    
    if not name:
        raise APIError('name 必填', 400)
    
    config = {
        'keywords': data.get('keywords', []),
        'regex_pattern': data.get('regex_pattern'),
        'threshold_field': data.get('threshold_field'),
        'threshold_value': data.get('threshold_value', 0),
        'threshold_operator': data.get('threshold_operator', '>'),
        'sentiment_threshold': data.get('sentiment_threshold', -0.5),
        'frequency_count': data.get('frequency_count', 10),
        'frequency_window_minutes': data.get('frequency_window_minutes', 60),
        'notify_channels': data.get('notify_channels', []),
        'cooldown_minutes': data.get('cooldown_minutes', 30),
        'description': data.get('description', '')
    }
    
    rule_id = alert_manager.create_custom_rule(name, rule_type, level, config)
    
    return jsonify({
        'success': True,
        'rule_id': rule_id,
        'message': '预警规则已创建'
    }), 201


@app.route('/api/alert/rules/<rule_id>', methods=['DELETE'])
@require_api_key
@rate_limit(limit=20)
def delete_alert_rule(rule_id):
    """删除预警规则"""
    if alert_manager.rule_engine.remove_rule(rule_id):
        return jsonify({'success': True, 'message': '规则已删除'})
    raise APIError('规则不存在', 404)


@app.route('/api/alert/rules/<rule_id>/enable', methods=['POST'])
@require_api_key
@rate_limit(limit=20)
def enable_alert_rule(rule_id):
    """启用预警规则"""
    if alert_manager.rule_engine.enable_rule(rule_id):
        return jsonify({'success': True, 'message': '规则已启用'})
    raise APIError('规则不存在', 404)


@app.route('/api/alert/rules/<rule_id>/disable', methods=['POST'])
@require_api_key
@rate_limit(limit=20)
def disable_alert_rule(rule_id):
    """禁用预警规则"""
    if alert_manager.rule_engine.disable_rule(rule_id):
        return jsonify({'success': True, 'message': '规则已禁用'})
    raise APIError('规则不存在', 404)


@app.route('/api/alert/check', methods=['POST'])
@require_api_key
@require_json
@rate_limit(limit=100)
def check_content_alert():
    """检查内容是否触发预警"""
    data = request.json
    content = data.get('content', '')
    source = data.get('source', 'api')
    
    if not content:
        raise APIError('content 不能为空', 400)
    
    alerts = alert_manager.process_content(
        content=content,
        source=source,
        metadata=data.get('metadata')
    )
    
    return jsonify({
        'success': True,
        'triggered': len(alerts) > 0,
        'alerts': [a.to_dict() for a in alerts]
    })


@app.route('/api/alert/active', methods=['GET'])
@optional_api_key
@rate_limit(limit=60)
def get_active_alerts():
    """获取活跃预警"""
    level = request.args.get('level')
    level_enum = AlertLevel[level.upper()] if level else None
    
    alerts = alert_manager.get_active_alerts(level=level_enum)
    return jsonify({
        'success': True,
        'alerts': alerts,
        'count': len(alerts)
    })


@app.route('/api/alert/history', methods=['GET'])
@optional_api_key
@rate_limit(limit=60)
def get_alert_history():
    """获取预警历史"""
    limit = request.args.get('limit', 100, type=int)
    level = request.args.get('level')
    level_enum = AlertLevel[level.upper()] if level else None
    
    history = alert_manager.get_alert_history(limit=limit, level=level_enum)
    return jsonify({
        'success': True,
        'alerts': history,
        'count': len(history)
    })


@app.route('/api/alert/<alert_id>/acknowledge', methods=['POST'])
@require_api_key
@rate_limit(limit=60)
def acknowledge_alert(alert_id):
    """确认预警"""
    user = request.json.get('user', 'api_user') if request.json else 'api_user'
    
    if alert_manager.acknowledge_alert(alert_id, user):
        return jsonify({'success': True, 'message': '预警已确认'})
    raise APIError('预警不存在', 404)


@app.route('/api/alert/<alert_id>/resolve', methods=['POST'])
@require_api_key
@rate_limit(limit=60)
def resolve_alert(alert_id):
    """解决预警"""
    if alert_manager.resolve_alert(alert_id):
        return jsonify({'success': True, 'message': '预警已解决'})
    raise APIError('预警不存在', 404)


@app.route('/api/alert/stats', methods=['GET'])
@optional_api_key
@rate_limit(limit=60)
def get_alert_stats():
    """获取预警统计"""
    stats = alert_manager.get_stats()
    return jsonify({
        'success': True,
        'stats': stats
    })


# ============ 综合情报接口 ============

@app.route('/api/intelligence/process', methods=['POST'])
@require_api_key
@require_json
@rate_limit(limit=30)
def process_intelligence():
    """综合情报处理 - 一站式分析"""
    data = request.json
    content = data.get('content', '')
    source = data.get('source', 'unknown')
    source_url = data.get('source_url', '')
    author = data.get('author')
    
    if not content:
        raise APIError('content 不能为空', 400)
    
    results = {
        'content_id': str(uuid.uuid4())[:8],
        'processed_at': datetime.now().isoformat()
    }
    
    # 1. 情报分析
    intel_result = intelligence_analyzer.analyze(
        content=content,
        source=source,
        source_url=source_url,
        metadata={'author': author}
    )
    results['intelligence'] = intel_result.to_dict()
    
    # 2. 实体识别和关系抽取
    results['graph'] = knowledge_graph.add_document(
        text=content,
        source=source,
        author=author
    )
    
    # 3. 风险预警检查
    alerts = alert_manager.process_content(
        content=content,
        source=source,
        metadata={'author': author}
    )
    results['alerts'] = {
        'triggered': len(alerts) > 0,
        'count': len(alerts),
        'alerts': [a.to_dict() for a in alerts]
    }
    
    return jsonify({
        'success': True,
        'results': results
    })


@app.route('/api/intelligence/dashboard', methods=['GET'])
@optional_api_key
@rate_limit(limit=30)
def get_intelligence_dashboard():
    """情报仪表板 - 综合概览"""
    dashboard = {
        'updated_at': datetime.now().isoformat(),
        'realtime': realtime_collector.get_stats(),
        'intelligence': intelligence_analyzer.get_dashboard_data(),
        'graph': knowledge_graph.get_stats(),
        'social': social_network.get_stats(),
        'alerts': alert_manager.get_stats()
    }
    
    return jsonify({
        'success': True,
        'dashboard': dashboard
    })


# =============================================================================
# 批量采集任务 API
# =============================================================================

@app.route('/api/batch/collect', methods=['POST'])
@optional_api_key
@rate_limit(limit=20)
def batch_collect():
    """
    批量创建采集任务
    
    请求体:
    {
        "name": "教育行业舆情监测",
        "tasks": [
            {"platform": "weibo", "keyword": "在线教育", "max_items": 20},
            {"platform": "zhihu", "keyword": "教育改革", "max_items": 15},
            {"platform": "douyin", "keyword": "职业培训", "max_items": 10}
        ],
        "auto_start": true
    }
    
    响应:
    {
        "success": true,
        "task_id": "uuid",
        "name": "教育行业舆情监测",
        "subtasks_count": 3,
        "status": "running",
        "created_at": "2026-03-08T15:00:00"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': '请求体为空'
            }), 400
        
        name = data.get('name', f'批量任务_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        tasks = data.get('tasks', [])
        auto_start = data.get('auto_start', True)
        metadata = data.get('metadata', {})
        
        if not tasks:
            return jsonify({
                'success': False,
                'error': 'tasks 不能为空'
            }), 400
        
        # 验证每个子任务
        for i, task in enumerate(tasks):
            if 'platform' not in task:
                return jsonify({
                    'success': False,
                    'error': f'第 {i+1} 个任务缺少 platform 字段'
                }), 400
            
            if 'keyword' not in task:
                return jsonify({
                    'success': False,
                    'error': f'第 {i+1} 个任务缺少 keyword 字段'
                }), 400
            
            # 验证平台是否支持
            try:
                Platform(task['platform'])
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': f'不支持的平台: {task["platform"]}'
                }), 400
        
        # 获取调度器
        scheduler = get_scheduler()
        
        # 创建批量任务
        batch_task = scheduler.create_batch_task(
            name=name,
            platforms_keywords=tasks,
            metadata=metadata
        )
        
        # 自动启动
        if auto_start:
            scheduler.submit_task(batch_task.id)
        
        return jsonify({
            'success': True,
            'task_id': batch_task.id,
            'name': batch_task.name,
            'subtasks_count': len(batch_task.subtasks),
            'status': batch_task.status.value,
            'created_at': batch_task.created_at.isoformat()
        })
    
    except Exception as e:
        logger.error(f"创建批量任务失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/batch/tasks', methods=['GET'])
@optional_api_key
@rate_limit(limit=60)
def list_batch_tasks():
    """
    获取批量任务列表
    
    查询参数:
    - status: 按状态过滤 (pending/running/completed/failed/cancelled)
    - limit: 返回数量 (默认50)
    
    响应:
    {
        "success": true,
        "tasks": [
            {
                "id": "uuid",
                "name": "教育行业舆情监测",
                "status": "completed",
                "created_at": "2026-03-08T15:00:00",
                "completed_at": "2026-03-08T15:05:23",
                "total_items": 45,
                "success_count": 3,
                "failed_count": 0,
                "subtasks": [...]
            }
        ],
        "count": 1
    }
    """
    try:
        status_str = request.args.get('status')
        limit = int(request.args.get('limit', 50))
        
        status_filter = None
        if status_str:
            try:
                status_filter = BatchTaskStatus(status_str)
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': f'无效的状态值: {status_str}'
                }), 400
        
        # 获取调度器
        scheduler = get_scheduler()
        
        # 获取任务列表
        tasks = scheduler.list_tasks(status=status_filter, limit=limit)
        
        return jsonify({
            'success': True,
            'tasks': [task.to_dict() for task in tasks],
            'count': len(tasks)
        })
    
    except Exception as e:
        logger.error(f"获取批量任务列表失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/batch/tasks/<task_id>', methods=['GET'])
@optional_api_key
@rate_limit(limit=60)
def get_batch_task(task_id):
    """
    获取批量任务详情
    
    响应:
    {
        "success": true,
        "task": {
            "id": "uuid",
            "name": "教育行业舆情监测",
            "status": "completed",
            "created_at": "2026-03-08T15:00:00",
            "started_at": "2026-03-08T15:00:01",
            "completed_at": "2026-03-08T15:05:23",
            "total_items": 45,
            "success_count": 3,
            "failed_count": 0,
            "subtasks": [
                {
                    "id": "subtask-uuid",
                    "platform": "weibo",
                    "keyword": "在线教育",
                    "max_items": 20,
                    "status": "completed",
                    "items_collected": 18,
                    "collection_id": "collection-uuid",
                    "started_at": "2026-03-08T15:00:01",
                    "completed_at": "2026-03-08T15:01:45"
                }
            ]
        }
    }
    """
    try:
        # 获取调度器
        scheduler = get_scheduler()
        
        # 获取任务
        task = scheduler.get_task(task_id)
        
        if not task:
            return jsonify({
                'success': False,
                'error': '任务不存在'
            }), 404
        
        return jsonify({
            'success': True,
            'task': task.to_dict()
        })
    
    except Exception as e:
        logger.error(f"获取批量任务详情失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/batch/tasks/<task_id>/start', methods=['POST'])
@optional_api_key
@rate_limit(limit=20)
def start_batch_task(task_id):
    """
    启动批量任务
    
    响应:
    {
        "success": true,
        "task_id": "uuid",
        "status": "running"
    }
    """
    try:
        # 获取调度器
        scheduler = get_scheduler()
        
        # 提交任务
        success = scheduler.submit_task(task_id)
        
        if not success:
            return jsonify({
                'success': False,
                'error': '任务启动失败,可能任务不存在或状态不允许启动'
            }), 400
        
        task = scheduler.get_task(task_id)
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'status': task.status.value if task else 'unknown'
        })
    
    except Exception as e:
        logger.error(f"启动批量任务失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/batch/tasks/<task_id>/cancel', methods=['POST'])
@optional_api_key
@rate_limit(limit=20)
def cancel_batch_task(task_id):
    """
    取消批量任务
    
    响应:
    {
        "success": true,
        "task_id": "uuid",
        "status": "cancelled"
    }
    """
    try:
        # 获取调度器
        scheduler = get_scheduler()
        
        # 取消任务
        success = scheduler.cancel_task(task_id)
        
        if not success:
            return jsonify({
                'success': False,
                'error': '任务取消失败,可能任务不存在或状态不允许取消'
            }), 400
        
        task = scheduler.get_task(task_id)
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'status': task.status.value if task else 'unknown'
        })
    
    except Exception as e:
        logger.error(f"取消批量任务失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/batch/stats', methods=['GET'])
@optional_api_key
@rate_limit(limit=100)
def get_batch_stats():
    """
    获取批量采集调度器统计信息
    
    响应:
    {
        "success": true,
        "stats": {
            "scheduler_running": true,
            "max_workers": 3,
            "active_workers": 3,
            "queue_size": 5,
            "total_tasks": 10,
            "tasks_by_status": {
                "pending": 2,
                "running": 3,
                "completed": 4,
                "failed": 1,
                "cancelled": 0
            },
            "total_items_collected": 256
        }
    }
    """
    try:
        # 获取调度器
        scheduler = get_scheduler()
        
        # 获取统计信息
        stats = scheduler.get_statistics()
        
        return jsonify({
            'success': True,
            'stats': stats
        })
    
    except Exception as e:
        logger.error(f"获取批量统计信息失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)