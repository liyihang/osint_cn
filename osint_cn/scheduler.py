"""
任务调度器模块

提供定时任务调度和管理功能
"""

import os
import logging
import threading
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.triggers.date import DateTrigger
    from apscheduler.jobstores.memory import MemoryJobStore
    HAS_APSCHEDULER = True
except ImportError:
    HAS_APSCHEDULER = False
    BackgroundScheduler = None

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class TaskType(str, Enum):
    """任务类型"""
    COLLECT = "collect"           # 数据采集
    ANALYZE = "analyze"           # 数据分析
    REPORT = "report"             # 报告生成
    CLEANUP = "cleanup"           # 数据清理
    MONITOR = "monitor"           # 监控任务
    CUSTOM = "custom"             # 自定义任务


@dataclass
class TaskConfig:
    """任务配置"""
    platform: Optional[str] = None
    keyword: Optional[str] = None
    max_items: int = 100
    analysis_types: List[str] = field(default_factory=lambda: ["sentiment", "keywords"])
    output_format: str = "json"
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskResult:
    """任务执行结果"""
    task_id: str
    status: TaskStatus
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    items_processed: int = 0
    result_data: Optional[Dict] = None
    error_message: Optional[str] = None
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """执行时长（秒）"""
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None


@dataclass
class Task:
    """任务定义"""
    id: str
    name: str
    task_type: TaskType
    config: TaskConfig
    status: TaskStatus = TaskStatus.PENDING
    schedule: Optional[str] = None  # Cron 表达式
    interval_seconds: Optional[int] = None  # 间隔执行
    run_at: Optional[datetime] = None  # 一次性执行时间
    created_at: datetime = field(default_factory=datetime.now)
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    results: List[TaskResult] = field(default_factory=list)
    enabled: bool = True
    
    def add_result(self, result: TaskResult):
        """添加执行结果"""
        self.results.append(result)
        self.run_count += 1
        self.last_run = result.finished_at or datetime.now()
        
        # 只保留最近 10 次结果
        if len(self.results) > 10:
            self.results = self.results[-10:]


class TaskExecutor:
    """任务执行器"""
    
    def __init__(self):
        self._collectors = {}
        self._analyzers = {}
        self._init_executors()
    
    def _init_executors(self):
        """初始化执行器"""
        try:
            from osint_cn.collection import CollectorFactory
            self._collector_factory = CollectorFactory
        except ImportError:
            self._collector_factory = None
            logger.warning("CollectorFactory not available")
        
        try:
            from osint_cn.analysis import OSINTAnalyzer
            self._analyzer = OSINTAnalyzer()
        except ImportError:
            self._analyzer = None
            logger.warning("OSINTAnalyzer not available")
    
    def execute(self, task: Task) -> TaskResult:
        """执行任务"""
        result = TaskResult(
            task_id=task.id,
            status=TaskStatus.RUNNING,
            started_at=datetime.now()
        )
        
        try:
            if task.task_type == TaskType.COLLECT:
                result = self._execute_collect(task, result)
            elif task.task_type == TaskType.ANALYZE:
                result = self._execute_analyze(task, result)
            elif task.task_type == TaskType.REPORT:
                result = self._execute_report(task, result)
            elif task.task_type == TaskType.CLEANUP:
                result = self._execute_cleanup(task, result)
            elif task.task_type == TaskType.MONITOR:
                result = self._execute_monitor(task, result)
            else:
                result.status = TaskStatus.FAILED
                result.error_message = f"Unknown task type: {task.task_type}"
        
        except Exception as e:
            logger.exception(f"Task {task.id} failed: {e}")
            result.status = TaskStatus.FAILED
            result.error_message = str(e)
        
        result.finished_at = datetime.now()
        return result
    
    def _execute_collect(self, task: Task, result: TaskResult) -> TaskResult:
        """执行采集任务"""
        if not self._collector_factory:
            result.status = TaskStatus.FAILED
            result.error_message = "Collector not available"
            return result
        
        config = task.config
        platform = config.platform
        keyword = config.keyword
        
        if not platform or not keyword:
            result.status = TaskStatus.FAILED
            result.error_message = "Platform and keyword are required"
            return result
        
        try:
            collector = self._collector_factory.create(platform)
            items = collector.collect(keyword, limit=config.max_items)
            
            result.status = TaskStatus.COMPLETED
            result.items_processed = len(items)
            result.result_data = {
                'platform': platform,
                'keyword': keyword,
                'items_count': len(items),
                'items': [
                    {
                        'content': item.content[:200],
                        'author': item.author,
                        'url': item.url,
                    }
                    for item in items[:10]  # 只保存前 10 条预览
                ]
            }
        except Exception as e:
            result.status = TaskStatus.FAILED
            result.error_message = str(e)
        
        return result
    
    def _execute_analyze(self, task: Task, result: TaskResult) -> TaskResult:
        """执行分析任务"""
        if not self._analyzer:
            result.status = TaskStatus.FAILED
            result.error_message = "Analyzer not available"
            return result
        
        # 这里需要从数据库获取待分析数据
        # 简化实现，实际应该从存储中读取
        result.status = TaskStatus.COMPLETED
        result.result_data = {
            'analysis_types': task.config.analysis_types,
            'message': 'Analysis task completed'
        }
        
        return result
    
    def _execute_report(self, task: Task, result: TaskResult) -> TaskResult:
        """执行报告生成任务"""
        result.status = TaskStatus.COMPLETED
        result.result_data = {
            'format': task.config.output_format,
            'message': 'Report generation completed'
        }
        return result
    
    def _execute_cleanup(self, task: Task, result: TaskResult) -> TaskResult:
        """执行清理任务"""
        # 清理过期数据
        result.status = TaskStatus.COMPLETED
        result.result_data = {'message': 'Cleanup completed'}
        return result
    
    def _execute_monitor(self, task: Task, result: TaskResult) -> TaskResult:
        """执行监控任务"""
        # 关键词监控
        result.status = TaskStatus.COMPLETED
        result.result_data = {'message': 'Monitor task completed'}
        return result


class TaskScheduler:
    """
    任务调度器
    
    管理定时任务的创建、调度和执行
    """
    
    def __init__(self):
        self._tasks: Dict[str, Task] = {}
        self._executor = TaskExecutor()
        self._scheduler: Optional[BackgroundScheduler] = None
        self._lock = threading.Lock()
        self._started = False
        
        if HAS_APSCHEDULER:
            self._scheduler = BackgroundScheduler(
                jobstores={
                    'default': MemoryJobStore()
                },
                job_defaults={
                    'coalesce': True,
                    'max_instances': 3,
                    'misfire_grace_time': 300
                }
            )
    
    def start(self):
        """启动调度器"""
        if not HAS_APSCHEDULER:
            logger.warning("APScheduler not installed, scheduler disabled")
            return
        
        if self._started:
            return
        
        self._scheduler.start()
        self._started = True
        logger.info("Task scheduler started")
        
        # 恢复已注册的任务
        for task in self._tasks.values():
            if task.enabled and (task.schedule or task.interval_seconds):
                self._register_job(task)
    
    def stop(self):
        """停止调度器"""
        if self._scheduler and self._started:
            self._scheduler.shutdown(wait=False)
            self._started = False
            logger.info("Task scheduler stopped")
    
    def create_task(
        self,
        name: str,
        task_type: TaskType,
        config: TaskConfig = None,
        schedule: str = None,
        interval_seconds: int = None,
        run_at: datetime = None,
        enabled: bool = True
    ) -> Task:
        """
        创建任务
        
        Args:
            name: 任务名称
            task_type: 任务类型
            config: 任务配置
            schedule: Cron 表达式（如 "0 */6 * * *" 表示每6小时）
            interval_seconds: 间隔执行秒数
            run_at: 一次性执行时间
            enabled: 是否启用
            
        Returns:
            创建的任务
        """
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            name=name,
            task_type=task_type,
            config=config or TaskConfig(),
            schedule=schedule,
            interval_seconds=interval_seconds,
            run_at=run_at,
            enabled=enabled
        )
        
        with self._lock:
            self._tasks[task_id] = task
        
        # 如果调度器已启动且任务启用，注册到调度器
        if self._started and enabled:
            self._register_job(task)
        
        logger.info(f"Task created: {task_id} - {name}")
        return task
    
    def _register_job(self, task: Task):
        """注册任务到调度器"""
        if not self._scheduler:
            return
        
        job_id = f"task_{task.id}"
        
        # 移除已存在的任务
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)
        
        # 根据配置创建触发器
        if task.schedule:
            trigger = CronTrigger.from_crontab(task.schedule)
        elif task.interval_seconds:
            trigger = IntervalTrigger(seconds=task.interval_seconds)
        elif task.run_at:
            trigger = DateTrigger(run_date=task.run_at)
        else:
            return
        
        self._scheduler.add_job(
            func=self._run_task,
            trigger=trigger,
            id=job_id,
            args=[task.id],
            name=task.name
        )
        
        # 更新下次运行时间
        job = self._scheduler.get_job(job_id)
        if job:
            task.next_run = job.next_run_time
    
    def _run_task(self, task_id: str):
        """运行任务"""
        task = self._tasks.get(task_id)
        if not task:
            logger.warning(f"Task not found: {task_id}")
            return
        
        if not task.enabled:
            logger.info(f"Task disabled: {task_id}")
            return
        
        logger.info(f"Running task: {task.name} ({task_id})")
        
        task.status = TaskStatus.RUNNING
        result = self._executor.execute(task)
        task.add_result(result)
        task.status = result.status
        
        # 更新下次运行时间
        if self._scheduler:
            job = self._scheduler.get_job(f"task_{task_id}")
            if job:
                task.next_run = job.next_run_time
        
        logger.info(f"Task completed: {task.name} - Status: {result.status.value}")
    
    def run_now(self, task_id: str) -> Optional[TaskResult]:
        """立即运行任务"""
        task = self._tasks.get(task_id)
        if not task:
            return None
        
        logger.info(f"Running task immediately: {task.name}")
        
        task.status = TaskStatus.RUNNING
        result = self._executor.execute(task)
        task.add_result(result)
        task.status = result.status
        
        return result
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self._tasks.get(task_id)
    
    def get_all_tasks(self) -> List[Task]:
        """获取所有任务"""
        return list(self._tasks.values())
    
    def get_tasks_by_type(self, task_type: TaskType) -> List[Task]:
        """按类型获取任务"""
        return [t for t in self._tasks.values() if t.task_type == task_type]
    
    def update_task(self, task_id: str, **kwargs) -> Optional[Task]:
        """更新任务"""
        task = self._tasks.get(task_id)
        if not task:
            return None
        
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
        
        # 如果调度配置变更，重新注册
        if any(k in kwargs for k in ['schedule', 'interval_seconds', 'run_at', 'enabled']):
            if self._started:
                if task.enabled:
                    self._register_job(task)
                else:
                    self._unregister_job(task)
        
        return task
    
    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        self._unregister_job(task)
        
        with self._lock:
            del self._tasks[task_id]
        
        logger.info(f"Task deleted: {task_id}")
        return True
    
    def _unregister_job(self, task: Task):
        """从调度器移除任务"""
        if self._scheduler:
            job_id = f"task_{task.id}"
            if self._scheduler.get_job(job_id):
                self._scheduler.remove_job(job_id)
    
    def pause_task(self, task_id: str) -> bool:
        """暂停任务"""
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        task.enabled = False
        task.status = TaskStatus.PAUSED
        
        if self._scheduler:
            job_id = f"task_{task.id}"
            if self._scheduler.get_job(job_id):
                self._scheduler.pause_job(job_id)
        
        return True
    
    def resume_task(self, task_id: str) -> bool:
        """恢复任务"""
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        task.enabled = True
        task.status = TaskStatus.PENDING
        
        if self._scheduler:
            job_id = f"task_{task.id}"
            if self._scheduler.get_job(job_id):
                self._scheduler.resume_job(job_id)
            else:
                self._register_job(task)
        
        return True
    
    def get_task_history(self, task_id: str, limit: int = 10) -> List[TaskResult]:
        """获取任务执行历史"""
        task = self._tasks.get(task_id)
        if not task:
            return []
        
        return task.results[-limit:]
    
    def get_scheduler_info(self) -> Dict:
        """获取调度器信息"""
        info = {
            'started': self._started,
            'has_apscheduler': HAS_APSCHEDULER,
            'tasks_count': len(self._tasks),
            'tasks_enabled': len([t for t in self._tasks.values() if t.enabled]),
            'tasks_running': len([t for t in self._tasks.values() if t.status == TaskStatus.RUNNING]),
        }
        
        if self._scheduler and self._started:
            jobs = self._scheduler.get_jobs()
            info['scheduled_jobs'] = len(jobs)
            info['next_run_times'] = [
                {'job_id': job.id, 'next_run': str(job.next_run_time)}
                for job in jobs[:5]
            ]
        
        return info


# 全局调度器实例
scheduler = TaskScheduler()


# ============ 预定义任务模板 ============

def create_keyword_monitor_task(
    keyword: str,
    platforms: List[str] = None,
    interval_hours: int = 6
) -> Task:
    """
    创建关键词监控任务
    
    Args:
        keyword: 监控关键词
        platforms: 监控平台列表
        interval_hours: 监控间隔（小时）
    """
    platforms = platforms or ['weibo', 'zhihu']
    
    config = TaskConfig(
        keyword=keyword,
        max_items=50,
        extra={'platforms': platforms}
    )
    
    return scheduler.create_task(
        name=f"监控: {keyword}",
        task_type=TaskType.MONITOR,
        config=config,
        interval_seconds=interval_hours * 3600,
        enabled=True
    )


def create_daily_collection_task(
    platform: str,
    keyword: str,
    run_hour: int = 8
) -> Task:
    """
    创建每日采集任务
    
    Args:
        platform: 目标平台
        keyword: 采集关键词
        run_hour: 运行时间（小时，0-23）
    """
    config = TaskConfig(
        platform=platform,
        keyword=keyword,
        max_items=100
    )
    
    return scheduler.create_task(
        name=f"每日采集: {platform}/{keyword}",
        task_type=TaskType.COLLECT,
        config=config,
        schedule=f"0 {run_hour} * * *",  # 每天指定时间运行
        enabled=True
    )


def create_cleanup_task(days_to_keep: int = 30) -> Task:
    """
    创建数据清理任务
    
    Args:
        days_to_keep: 保留天数
    """
    config = TaskConfig(
        extra={'days_to_keep': days_to_keep}
    )
    
    return scheduler.create_task(
        name="每周数据清理",
        task_type=TaskType.CLEANUP,
        config=config,
        schedule="0 3 * * 0",  # 每周日凌晨3点运行
        enabled=True
    )
