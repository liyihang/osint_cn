"""
实时互联网情报采集模块
支持多平台并发采集、增量更新、WebSocket实时推送
"""

import asyncio
import hashlib
import json
import logging
import threading
import time
from abc import ABC, abstractmethod
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Callable, Any, Set
from queue import Queue, Empty
import redis

logger = logging.getLogger(__name__)


class CollectionStatus(Enum):
    """采集状态"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


class DataPriority(Enum):
    """数据优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class CollectedItem:
    """采集到的数据项"""
    id: str
    platform: str
    content: str
    author: str
    url: str
    timestamp: datetime
    raw_data: Dict[str, Any]
    priority: DataPriority = DataPriority.NORMAL
    metadata: Dict[str, Any] = field(default_factory=dict)
    hash: str = ""
    
    def __post_init__(self):
        if not self.hash:
            self.hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """计算内容哈希，用于去重"""
        content = f"{self.platform}:{self.author}:{self.content[:200]}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['priority'] = self.priority.value
        return data


@dataclass
class CollectionTask:
    """采集任务"""
    task_id: str
    platforms: List[str]
    keywords: List[str]
    interval_seconds: int = 60
    max_items_per_run: int = 100
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    status: CollectionStatus = CollectionStatus.IDLE
    stats: Dict[str, int] = field(default_factory=lambda: {
        'total_collected': 0,
        'duplicates_skipped': 0,
        'errors': 0
    })


class DataDeduplicator:
    """数据去重器"""
    
    def __init__(self, max_size: int = 100000, redis_client: Optional[redis.Redis] = None):
        self.max_size = max_size
        self.redis_client = redis_client
        self.local_cache: Set[str] = set()
        self.cache_queue: deque = deque(maxlen=max_size)
    
    def is_duplicate(self, item: CollectedItem) -> bool:
        """检查是否重复"""
        if self.redis_client:
            return self._check_redis(item.hash)
        return self._check_local(item.hash)
    
    def _check_redis(self, hash_value: str) -> bool:
        """使用Redis检查重复"""
        key = f"osint:dedup:{hash_value}"
        if self.redis_client.exists(key):
            return True
        # 设置24小时过期
        self.redis_client.setex(key, 86400, "1")
        return False
    
    def _check_local(self, hash_value: str) -> bool:
        """使用本地缓存检查重复"""
        if hash_value in self.local_cache:
            return True
        
        # 添加到缓存
        if len(self.local_cache) >= self.max_size:
            # 移除最老的
            old_hash = self.cache_queue.popleft()
            self.local_cache.discard(old_hash)
        
        self.local_cache.add(hash_value)
        self.cache_queue.append(hash_value)
        return False
    
    def clear(self):
        """清空去重缓存"""
        self.local_cache.clear()
        self.cache_queue.clear()


class RealtimeCollector:
    """实时采集器"""
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        max_workers: int = 5,
        buffer_size: int = 1000
    ):
        self.redis_client = None
        if redis_url:
            try:
                self.redis_client = redis.from_url(redis_url)
            except Exception as e:
                logger.warning(f"Redis连接失败: {e}, 使用本地模式")
        
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # 数据缓冲区
        self.data_buffer: Queue = Queue(maxsize=buffer_size)
        self.priority_buffer: Dict[DataPriority, Queue] = {
            p: Queue() for p in DataPriority
        }
        
        # 去重器
        self.deduplicator = DataDeduplicator(redis_client=self.redis_client)
        
        # 任务管理
        self.tasks: Dict[str, CollectionTask] = {}
        self.running = False
        self.collection_thread: Optional[threading.Thread] = None
        
        # 回调函数
        self.on_data_callbacks: List[Callable[[CollectedItem], None]] = []
        self.on_error_callbacks: List[Callable[[str, Exception], None]] = []
        
        # 统计
        self.stats = {
            'total_collected': 0,
            'duplicates_skipped': 0,
            'errors': 0,
            'platforms': {}
        }
    
    def add_callback(self, callback: Callable[[CollectedItem], None]):
        """添加数据回调"""
        self.on_data_callbacks.append(callback)
    
    def add_error_callback(self, callback: Callable[[str, Exception], None]):
        """添加错误回调"""
        self.on_error_callbacks.append(callback)
    
    def create_task(
        self,
        platforms: List[str],
        keywords: List[str],
        interval_seconds: int = 60,
        max_items: int = 100
    ) -> str:
        """创建采集任务"""
        import uuid
        task_id = str(uuid.uuid4())[:8]
        
        task = CollectionTask(
            task_id=task_id,
            platforms=platforms,
            keywords=keywords,
            interval_seconds=interval_seconds,
            max_items_per_run=max_items,
            next_run=datetime.now()
        )
        
        self.tasks[task_id] = task
        logger.info(f"创建采集任务: {task_id}, 平台: {platforms}, 关键词: {keywords}")
        return task_id
    
    def remove_task(self, task_id: str) -> bool:
        """删除采集任务"""
        if task_id in self.tasks:
            del self.tasks[task_id]
            logger.info(f"删除采集任务: {task_id}")
            return True
        return False
    
    def pause_task(self, task_id: str) -> bool:
        """暂停任务"""
        if task_id in self.tasks:
            self.tasks[task_id].enabled = False
            self.tasks[task_id].status = CollectionStatus.PAUSED
            return True
        return False
    
    def resume_task(self, task_id: str) -> bool:
        """恢复任务"""
        if task_id in self.tasks:
            self.tasks[task_id].enabled = True
            self.tasks[task_id].status = CollectionStatus.IDLE
            self.tasks[task_id].next_run = datetime.now()
            return True
        return False
    
    def start(self):
        """启动实时采集"""
        if self.running:
            return
        
        self.running = True
        self.collection_thread = threading.Thread(target=self._collection_loop, daemon=True)
        self.collection_thread.start()
        logger.info("实时采集器已启动")
    
    def stop(self):
        """停止实时采集"""
        self.running = False
        if self.collection_thread:
            self.collection_thread.join(timeout=5)
        logger.info("实时采集器已停止")
    
    def _collection_loop(self):
        """采集主循环"""
        while self.running:
            now = datetime.now()
            
            for task_id, task in list(self.tasks.items()):
                if not task.enabled:
                    continue
                
                if task.next_run and now >= task.next_run:
                    try:
                        task.status = CollectionStatus.RUNNING
                        self._execute_task(task)
                        task.last_run = now
                        task.next_run = now + timedelta(seconds=task.interval_seconds)
                        task.status = CollectionStatus.IDLE
                    except Exception as e:
                        task.status = CollectionStatus.ERROR
                        task.stats['errors'] += 1
                        logger.error(f"任务 {task_id} 执行失败: {e}")
                        self._notify_error(task_id, e)
            
            time.sleep(1)
    
    def _execute_task(self, task: CollectionTask):
        """执行采集任务"""
        from osint_cn.collection import CollectorFactory
        
        futures = []
        for platform in task.platforms:
            for keyword in task.keywords:
                future = self.executor.submit(
                    self._collect_single,
                    platform,
                    keyword,
                    task.max_items_per_run // len(task.keywords)
                )
                futures.append((platform, keyword, future))
        
        for platform, keyword, future in futures:
            try:
                items = future.result(timeout=30)
                for item in items:
                    self._process_item(item, task)
            except Exception as e:
                logger.error(f"采集 {platform}/{keyword} 失败: {e}")
    
    def _collect_single(
        self,
        platform: str,
        keyword: str,
        max_items: int
    ) -> List[CollectedItem]:
        """单次采集"""
        from osint_cn.collection import CollectorFactory
        
        items = []
        try:
            collector = CollectorFactory.create(platform)
            raw_data = collector.collect(keyword, max_items=max_items)
            
            for entry in raw_data.get('data', []):
                item = CollectedItem(
                    id=str(entry.get('id', '')),
                    platform=platform,
                    content=entry.get('content', entry.get('text', '')),
                    author=entry.get('author', entry.get('user', {}).get('name', 'Unknown')),
                    url=entry.get('url', ''),
                    timestamp=datetime.now(),
                    raw_data=entry,
                    metadata={'keyword': keyword}
                )
                items.append(item)
        except Exception as e:
            logger.error(f"采集错误 {platform}: {e}")
        
        return items
    
    def _process_item(self, item: CollectedItem, task: CollectionTask):
        """处理采集项"""
        # 去重检查
        if self.deduplicator.is_duplicate(item):
            task.stats['duplicates_skipped'] += 1
            self.stats['duplicates_skipped'] += 1
            return
        
        # 更新统计
        task.stats['total_collected'] += 1
        self.stats['total_collected'] += 1
        
        if item.platform not in self.stats['platforms']:
            self.stats['platforms'][item.platform] = 0
        self.stats['platforms'][item.platform] += 1
        
        # 放入缓冲区
        try:
            self.data_buffer.put_nowait(item)
            self.priority_buffer[item.priority].put_nowait(item)
        except:
            pass
        
        # 通知回调
        for callback in self.on_data_callbacks:
            try:
                callback(item)
            except Exception as e:
                logger.error(f"回调执行失败: {e}")
        
        # 发布到Redis（如果可用）
        if self.redis_client:
            try:
                self.redis_client.publish(
                    'osint:realtime:data',
                    json.dumps(item.to_dict(), ensure_ascii=False)
                )
            except:
                pass
    
    def _notify_error(self, task_id: str, error: Exception):
        """通知错误"""
        for callback in self.on_error_callbacks:
            try:
                callback(task_id, error)
            except:
                pass
    
    def get_buffer_data(self, max_items: int = 100) -> List[Dict]:
        """获取缓冲区数据"""
        items = []
        while len(items) < max_items:
            try:
                item = self.data_buffer.get_nowait()
                items.append(item.to_dict())
            except Empty:
                break
        return items
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            **self.stats,
            'active_tasks': len([t for t in self.tasks.values() if t.enabled]),
            'total_tasks': len(self.tasks),
            'buffer_size': self.data_buffer.qsize()
        }
    
    def get_task_info(self, task_id: str) -> Optional[Dict]:
        """获取任务信息"""
        if task_id not in self.tasks:
            return None
        
        task = self.tasks[task_id]
        return {
            'task_id': task.task_id,
            'platforms': task.platforms,
            'keywords': task.keywords,
            'interval_seconds': task.interval_seconds,
            'enabled': task.enabled,
            'status': task.status.value,
            'created_at': task.created_at.isoformat(),
            'last_run': task.last_run.isoformat() if task.last_run else None,
            'next_run': task.next_run.isoformat() if task.next_run else None,
            'stats': task.stats
        }
    
    def list_tasks(self) -> List[Dict]:
        """列出所有任务"""
        return [self.get_task_info(tid) for tid in self.tasks.keys()]


class StreamingCollector:
    """流式采集器 - 支持WebSocket推送"""
    
    def __init__(self, realtime_collector: RealtimeCollector):
        self.collector = realtime_collector
        self.subscribers: Dict[str, Queue] = {}
        self.running = False
    
    def subscribe(self, client_id: str) -> Queue:
        """订阅数据流"""
        if client_id not in self.subscribers:
            self.subscribers[client_id] = Queue(maxsize=1000)
        return self.subscribers[client_id]
    
    def unsubscribe(self, client_id: str):
        """取消订阅"""
        if client_id in self.subscribers:
            del self.subscribers[client_id]
    
    def start(self):
        """启动流式推送"""
        self.running = True
        self.collector.add_callback(self._broadcast)
        self.collector.start()
    
    def stop(self):
        """停止流式推送"""
        self.running = False
        self.collector.stop()
    
    def _broadcast(self, item: CollectedItem):
        """广播数据到所有订阅者"""
        data = item.to_dict()
        for client_id, queue in list(self.subscribers.items()):
            try:
                queue.put_nowait(data)
            except:
                # 队列满，跳过
                pass
    
    def get_data(self, client_id: str, timeout: float = 1.0) -> Optional[Dict]:
        """获取订阅数据"""
        if client_id not in self.subscribers:
            return None
        
        try:
            return self.subscribers[client_id].get(timeout=timeout)
        except Empty:
            return None


# 全局实例
_realtime_collector: Optional[RealtimeCollector] = None
_streaming_collector: Optional[StreamingCollector] = None


def get_realtime_collector(redis_url: Optional[str] = None) -> RealtimeCollector:
    """获取实时采集器实例"""
    global _realtime_collector
    if _realtime_collector is None:
        _realtime_collector = RealtimeCollector(redis_url=redis_url)
    return _realtime_collector


def get_streaming_collector(redis_url: Optional[str] = None) -> StreamingCollector:
    """获取流式采集器实例"""
    global _streaming_collector
    if _streaming_collector is None:
        collector = get_realtime_collector(redis_url)
        _streaming_collector = StreamingCollector(collector)
    return _streaming_collector
