"""
批量采集任务调度器

功能:
- 批量任务创建与管理
- 自动任务队列调度
- 并发控制与限流
- 任务状态实时跟踪
- 结果自动汇总与报告生成
"""

import uuid
import time
import threading
from datetime import datetime
from typing import List, Dict, Optional, Any
from enum import Enum
from dataclasses import dataclass, asdict, field, is_dataclass
from queue import Queue, Empty
import logging

from .collection import CollectorFactory
from storage.service import get_storage, CollectionRecord, CollectedItemRecord


logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"      # 等待执行
    RUNNING = "running"      # 执行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 失败
    CANCELLED = "cancelled"  # 已取消


@dataclass
class SubTask:
    """单个采集子任务"""
    id: str
    platform: str
    keyword: str
    max_items: int = 10
    status: TaskStatus = TaskStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    items_collected: int = 0
    collection_id: Optional[str] = None  # 对应的collection记录ID
    error: Optional[str] = None


@dataclass
class BatchTask:
    """批量采集任务"""
    id: str
    name: str
    subtasks: List[SubTask]
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    total_items: int = 0
    success_count: int = 0
    failed_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'status': self.status.value,
            'total_items': self.total_items,
            'success_count': self.success_count,
            'failed_count': self.failed_count,
            'subtasks': [
                {
                    'id': st.id,
                    'platform': st.platform,
                    'keyword': st.keyword,
                    'max_items': st.max_items,
                    'status': st.status.value,
                    'started_at': st.started_at.isoformat() if st.started_at else None,
                    'completed_at': st.completed_at.isoformat() if st.completed_at else None,
                    'items_collected': st.items_collected,
                    'collection_id': st.collection_id,
                    'error': st.error
                }
                for st in self.subtasks
            ],
            'metadata': self.metadata
        }


class BatchCollectorScheduler:
    """批量采集任务调度器"""
    
    def __init__(self, max_workers: int = 3, storage_backend=None):
        """
        初始化调度器
        
        Args:
            max_workers: 最大并发工作线程数
            storage_backend: 存储后端实例
        """
        self.max_workers = max_workers
        self.storage_backend = storage_backend or get_storage()
        
        # 任务存储
        self.tasks: Dict[str, BatchTask] = {}
        self.task_queue: Queue = Queue()
        
        # 工作线程池
        self.workers: List[threading.Thread] = []
        self.running = False
        self.lock = threading.Lock()
        
        logger.info(f"批量采集调度器初始化完成: max_workers={max_workers}")
    
    def create_batch_task(
        self,
        name: str,
        platforms_keywords: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> BatchTask:
        """
        创建批量采集任务
        
        Args:
            name: 任务名称
            platforms_keywords: 平台和关键词列表，格式: [{"platform": "weibo", "keyword": "教育", "max_items": 10}, ...]
            metadata: 任务元数据
        
        Returns:
            BatchTask: 创建的批量任务对象
        """
        task_id = str(uuid.uuid4())
        
        # 创建子任务列表
        subtasks = []
        for item in platforms_keywords:
            subtask = SubTask(
                id=str(uuid.uuid4()),
                platform=item['platform'],
                keyword=item['keyword'],
                max_items=item.get('max_items', 10)
            )
            subtasks.append(subtask)
        
        # 创建批量任务
        batch_task = BatchTask(
            id=task_id,
            name=name,
            subtasks=subtasks,
            created_at=datetime.now(),
            metadata=metadata or {}
        )
        
        with self.lock:
            self.tasks[task_id] = batch_task
        
        logger.info(f"创建批量任务: {task_id}, 名称: {name}, 子任务数: {len(subtasks)}")
        return batch_task
    
    def submit_task(self, task_id: str) -> bool:
        """
        提交任务到执行队列
        
        Args:
            task_id: 任务ID
        
        Returns:
            bool: 是否成功提交
        """
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                logger.error(f"任务不存在: {task_id}")
                return False
            
            if task.status != TaskStatus.PENDING:
                logger.warning(f"任务状态不允许提交: {task_id}, status={task.status}")
                return False
            
            # 将所有子任务加入队列
            for subtask in task.subtasks:
                self.task_queue.put((task_id, subtask.id))
            
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
        
        logger.info(f"任务已提交到队列: {task_id}, 子任务数: {len(task.subtasks)}")
        return True
    
    def start(self):
        """启动调度器"""
        if self.running:
            logger.warning("调度器已在运行中")
            return
        
        self.running = True
        
        # 启动工作线程
        for i in range(self.max_workers):
            worker = threading.Thread(target=self._worker, name=f"BatchWorker-{i}", daemon=True)
            worker.start()
            self.workers.append(worker)
        
        logger.info(f"批量采集调度器已启动: {self.max_workers} 个工作线程")
    
    def stop(self):
        """停止调度器"""
        self.running = False
        logger.info("批量采集调度器正在停止...")
        
        # 等待工作线程结束
        for worker in self.workers:
            worker.join(timeout=5)
        
        self.workers.clear()
        logger.info("批量采集调度器已停止")
    
    def _worker(self):
        """工作线程函数"""
        thread_name = threading.current_thread().name
        logger.info(f"{thread_name} 启动")
        
        while self.running:
            try:
                # 从队列获取任务 (超时1秒)
                task_id, subtask_id = self.task_queue.get(timeout=1)
                
                # 执行子任务
                self._execute_subtask(task_id, subtask_id)
                
                self.task_queue.task_done()
                
            except Empty:
                continue
            except Exception as e:
                logger.error(f"{thread_name} 执行任务时异常: {e}", exc_info=True)
        
        logger.info(f"{thread_name} 停止")
    
    def _execute_subtask(self, task_id: str, subtask_id: str):
        """
        执行单个子任务
        
        Args:
            task_id: 批量任务ID
            subtask_id: 子任务ID
        """
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                logger.error(f"任务不存在: {task_id}")
                return
            
            subtask = next((st for st in task.subtasks if st.id == subtask_id), None)
            if not subtask:
                logger.error(f"子任务不存在: {subtask_id}")
                return
            
            subtask.status = TaskStatus.RUNNING
            subtask.started_at = datetime.now()
        
        logger.info(f"开始执行子任务: {subtask_id}, platform={subtask.platform}, keyword={subtask.keyword}")
        
        try:
            # 使用 CollectorFactory 创建采集器
            collector = CollectorFactory.create(subtask.platform)
            
            # 执行采集
            raw_items = collector.collect(
                keyword=subtask.keyword,
                limit=subtask.max_items
            )

            items = []
            for raw_item in raw_items or []:
                if is_dataclass(raw_item):
                    items.append(asdict(raw_item))
                elif isinstance(raw_item, dict):
                    items.append(raw_item)

            items_count = len(items)
            
            # 存储到数据库
            collection_id = None
            if items:
                try:
                    # 创建 CollectionRecord
                    collection_record = CollectionRecord(
                        id=str(uuid.uuid4()),
                        platform=subtask.platform,
                        keyword=subtask.keyword,
                        collected_at=datetime.now(),
                        items_count=items_count,
                        status='completed',
                        metadata={
                            'batch_task_id': task_id,
                            'subtask_id': subtask_id,
                            'collector': collector.__class__.__name__
                        }
                    )
                    
                    # 保存 collection
                    self.storage_backend.save_collection(collection_record)
                    collection_id = collection_record.id
                    
                    # 保存采集项
                    item_records = [
                        CollectedItemRecord(
                            id=str(uuid.uuid4()),
                            collection_id=collection_id,
                            platform=subtask.platform,
                            content=item.get('content', item.get('title', '')),
                            author=item.get('author', ''),
                            url=item.get('url', ''),
                            publish_time=item.get('publish_time'),
                            likes=item.get('likes', 0),
                            comments=item.get('comments', 0),
                            shares=item.get('shares', 0),
                            metadata=item
                        )
                        for item in items
                    ]
                    
                    self.storage_backend.save_items(item_records)
                    logger.info(f"子任务 {subtask_id} 数据已存储: collection_id={collection_id}, items={items_count}")
                    
                except Exception as e:
                    logger.error(f"存储子任务 {subtask_id} 数据失败: {e}", exc_info=True)
            
            # 更新子任务状态
            with self.lock:
                subtask.status = TaskStatus.COMPLETED
                subtask.completed_at = datetime.now()
                subtask.items_collected = items_count
                subtask.collection_id = collection_id
                
                task.total_items += items_count
                task.success_count += 1
            
            logger.info(f"子任务执行成功: {subtask_id}, 采集 {items_count} 条数据")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"子任务执行失败: {subtask_id}, error={error_msg}", exc_info=True)
            
            with self.lock:
                subtask.status = TaskStatus.FAILED
                subtask.completed_at = datetime.now()
                subtask.error = error_msg
                task.failed_count += 1
        
        # 检查批量任务是否全部完成
        self._check_task_completion(task_id)
    
    def _check_task_completion(self, task_id: str):
        """
        检查批量任务是否完成
        
        Args:
            task_id: 任务ID
        """
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return
            
            # 检查所有子任务是否完成
            all_completed = all(
                st.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
                for st in task.subtasks
            )
            
            if all_completed and task.status == TaskStatus.RUNNING:
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now()
                
                duration = (task.completed_at - task.started_at).total_seconds()
                logger.info(
                    f"批量任务完成: {task_id}, "
                    f"成功={task.success_count}, 失败={task.failed_count}, "
                    f"总条数={task.total_items}, 耗时={duration:.1f}秒"
                )
    
    def get_task(self, task_id: str) -> Optional[BatchTask]:
        """
        获取任务详情
        
        Args:
            task_id: 任务ID
        
        Returns:
            Optional[BatchTask]: 任务对象，不存在返回None
        """
        with self.lock:
            return self.tasks.get(task_id)
    
    def list_tasks(self, status: Optional[TaskStatus] = None, limit: int = 50) -> List[BatchTask]:
        """
        列出任务
        
        Args:
            status: 按状态过滤，None表示所有
            limit: 返回数量限制
        
        Returns:
            List[BatchTask]: 任务列表
        """
        with self.lock:
            tasks = list(self.tasks.values())
        
        # 按创建时间倒序
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        
        # 过滤状态
        if status:
            tasks = [t for t in tasks if t.status == status]
        
        return tasks[:limit]
    
    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
        
        Returns:
            bool: 是否成功取消
        """
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                logger.error(f"任务不存在: {task_id}")
                return False
            
            if task.status not in (TaskStatus.PENDING, TaskStatus.RUNNING):
                logger.warning(f"任务状态不允许取消: {task_id}, status={task.status}")
                return False
            
            # 取消所有未执行的子任务
            for subtask in task.subtasks:
                if subtask.status == TaskStatus.PENDING:
                    subtask.status = TaskStatus.CANCELLED
                    subtask.completed_at = datetime.now()
            
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()
        
        logger.info(f"任务已取消: {task_id}")
        return True
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取调度器统计信息
        
        Returns:
            Dict: 统计数据
        """
        with self.lock:
            total_tasks = len(self.tasks)
            pending = sum(1 for t in self.tasks.values() if t.status == TaskStatus.PENDING)
            running = sum(1 for t in self.tasks.values() if t.status == TaskStatus.RUNNING)
            completed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED)
            failed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.FAILED)
            cancelled = sum(1 for t in self.tasks.values() if t.status == TaskStatus.CANCELLED)
            
            total_items = sum(t.total_items for t in self.tasks.values())
            
            queue_size = self.task_queue.qsize()
        
        return {
            'scheduler_running': self.running,
            'max_workers': self.max_workers,
            'active_workers': len([w for w in self.workers if w.is_alive()]),
            'queue_size': queue_size,
            'total_tasks': total_tasks,
            'tasks_by_status': {
                'pending': pending,
                'running': running,
                'completed': completed,
                'failed': failed,
                'cancelled': cancelled
            },
            'total_items_collected': total_items
        }


# 全局调度器实例
_scheduler: Optional[BatchCollectorScheduler] = None
_scheduler_lock = threading.Lock()


def get_scheduler() -> BatchCollectorScheduler:
    """获取全局调度器实例 (单例模式)"""
    global _scheduler
    
    if _scheduler is None:
        with _scheduler_lock:
            if _scheduler is None:
                _scheduler = BatchCollectorScheduler(max_workers=3)
                _scheduler.start()
    
    return _scheduler


def shutdown_scheduler():
    """关闭全局调度器"""
    global _scheduler
    
    if _scheduler:
        with _scheduler_lock:
            if _scheduler:
                _scheduler.stop()
                _scheduler = None
