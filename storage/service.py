"""
数据存储服务层

提供统一的数据存储接口，支持多种后端
"""

import os
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class CollectionRecord:
    """采集记录"""
    id: str
    platform: str
    keyword: str
    collected_at: datetime
    items_count: int
    status: str = "completed"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CollectedItemRecord:
    """采集数据项"""
    id: str
    collection_id: str
    platform: str
    content: str
    author: str = ""
    author_id: str = ""
    url: str = ""
    publish_time: Optional[datetime] = None
    likes: int = 0
    comments: int = 0
    shares: int = 0
    sentiment: Optional[str] = None
    sentiment_score: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class AnalysisRecord:
    """分析记录"""
    id: str
    collection_id: Optional[str]
    analysis_type: str
    created_at: datetime
    source_count: int
    results: Dict[str, Any]


class BaseStorage(ABC):
    """存储抽象基类"""
    
    @abstractmethod
    def save_collection(self, record: CollectionRecord) -> str:
        """保存采集记录"""
        pass
    
    @abstractmethod
    def get_collection(self, collection_id: str) -> Optional[CollectionRecord]:
        """获取采集记录"""
        pass
    
    @abstractmethod
    def list_collections(self, page: int = 1, page_size: int = 20) -> List[CollectionRecord]:
        """列出采集记录"""
        pass
    
    @abstractmethod
    def save_items(self, collection_id: str, items: List[CollectedItemRecord]) -> int:
        """批量保存采集数据"""
        pass
    
    @abstractmethod
    def get_items(self, collection_id: str, page: int = 1, page_size: int = 20) -> List[CollectedItemRecord]:
        """获取采集数据"""
        pass
    
    @abstractmethod
    def save_analysis(self, record: AnalysisRecord) -> str:
        """保存分析结果"""
        pass
    
    @abstractmethod
    def get_analysis(self, analysis_id: str) -> Optional[AnalysisRecord]:
        """获取分析结果"""
        pass


class MemoryStorage(BaseStorage):
    """内存存储（开发测试用）"""
    
    def __init__(self):
        self._collections: Dict[str, CollectionRecord] = {}
        self._items: Dict[str, List[CollectedItemRecord]] = {}
        self._analyses: Dict[str, AnalysisRecord] = {}
    
    def save_collection(self, record: CollectionRecord) -> str:
        self._collections[record.id] = record
        self._items[record.id] = []
        return record.id
    
    def get_collection(self, collection_id: str) -> Optional[CollectionRecord]:
        return self._collections.get(collection_id)
    
    def list_collections(self, page: int = 1, page_size: int = 20) -> List[CollectionRecord]:
        all_records = sorted(
            self._collections.values(),
            key=lambda x: x.collected_at,
            reverse=True
        )
        start = (page - 1) * page_size
        return all_records[start:start + page_size]
    
    def save_items(self, collection_id: str, items: List[CollectedItemRecord]) -> int:
        if collection_id not in self._items:
            self._items[collection_id] = []
        self._items[collection_id].extend(items)
        
        # 更新采集记录的数量
        if collection_id in self._collections:
            self._collections[collection_id].items_count = len(self._items[collection_id])
        
        return len(items)
    
    def get_items(self, collection_id: str, page: int = 1, page_size: int = 20) -> List[CollectedItemRecord]:
        items = self._items.get(collection_id, [])
        start = (page - 1) * page_size
        return items[start:start + page_size]
    
    def get_all_items(self, collection_id: str) -> List[CollectedItemRecord]:
        return self._items.get(collection_id, [])
    
    def save_analysis(self, record: AnalysisRecord) -> str:
        self._analyses[record.id] = record
        return record.id
    
    def get_analysis(self, analysis_id: str) -> Optional[AnalysisRecord]:
        return self._analyses.get(analysis_id)
    
    def list_analyses(self, page: int = 1, page_size: int = 20) -> List[AnalysisRecord]:
        all_records = sorted(
            self._analyses.values(),
            key=lambda x: x.created_at,
            reverse=True
        )
        start = (page - 1) * page_size
        return all_records[start:start + page_size]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_items = sum(len(items) for items in self._items.values())
        return {
            'collections_count': len(self._collections),
            'items_count': total_items,
            'analyses_count': len(self._analyses)
        }


class MongoStorage(BaseStorage):
    """MongoDB 存储"""
    
    def __init__(self, uri: str = None, database: str = "osint_db"):
        try:
            from pymongo import MongoClient
            
            uri = uri or os.getenv('MONGO_URI', 'mongodb://localhost:27017')
            self._client = MongoClient(uri)
            self._db = self._client[database]
            self._collections_col = self._db['collections']
            self._items_col = self._db['items']
            self._analyses_col = self._db['analyses']
            
            # 创建索引
            self._collections_col.create_index('collected_at')
            self._items_col.create_index('collection_id')
            self._items_col.create_index([('content', 'text')])
            
            logger.info("MongoDB storage initialized")
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB: {e}")
            raise
    
    def save_collection(self, record: CollectionRecord) -> str:
        doc = asdict(record)
        doc['_id'] = record.id
        self._collections_col.replace_one({'_id': record.id}, doc, upsert=True)
        return record.id
    
    def get_collection(self, collection_id: str) -> Optional[CollectionRecord]:
        doc = self._collections_col.find_one({'_id': collection_id})
        if doc:
            doc.pop('_id', None)
            return CollectionRecord(**doc)
        return None
    
    def list_collections(self, page: int = 1, page_size: int = 20) -> List[CollectionRecord]:
        skip = (page - 1) * page_size
        docs = self._collections_col.find().sort('collected_at', -1).skip(skip).limit(page_size)
        
        records = []
        for doc in docs:
            doc.pop('_id', None)
            records.append(CollectionRecord(**doc))
        return records
    
    def save_items(self, collection_id: str, items: List[CollectedItemRecord]) -> int:
        if not items:
            return 0
        
        docs = []
        for item in items:
            doc = asdict(item)
            doc['_id'] = item.id
            doc['collection_id'] = collection_id
            docs.append(doc)
        
        result = self._items_col.insert_many(docs)
        
        # 更新采集记录的数量
        count = self._items_col.count_documents({'collection_id': collection_id})
        self._collections_col.update_one(
            {'_id': collection_id},
            {'$set': {'items_count': count}}
        )
        
        return len(result.inserted_ids)
    
    def get_items(self, collection_id: str, page: int = 1, page_size: int = 20) -> List[CollectedItemRecord]:
        skip = (page - 1) * page_size
        docs = self._items_col.find({'collection_id': collection_id}).skip(skip).limit(page_size)
        
        records = []
        for doc in docs:
            doc.pop('_id', None)
            records.append(CollectedItemRecord(**doc))
        return records
    
    def save_analysis(self, record: AnalysisRecord) -> str:
        doc = asdict(record)
        doc['_id'] = record.id
        self._analyses_col.replace_one({'_id': record.id}, doc, upsert=True)
        return record.id
    
    def get_analysis(self, analysis_id: str) -> Optional[AnalysisRecord]:
        doc = self._analyses_col.find_one({'_id': analysis_id})
        if doc:
            doc.pop('_id', None)
            return AnalysisRecord(**doc)
        return None
    
    def search_items(self, query: str, collection_id: str = None, limit: int = 100) -> List[CollectedItemRecord]:
        """全文搜索"""
        filter_doc = {'$text': {'$search': query}}
        if collection_id:
            filter_doc['collection_id'] = collection_id
        
        docs = self._items_col.find(filter_doc).limit(limit)
        
        records = []
        for doc in docs:
            doc.pop('_id', None)
            records.append(CollectedItemRecord(**doc))
        return records


class PostgresStorage(BaseStorage):
    """PostgreSQL 存储"""
    
    def __init__(self, uri: str = None):
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            import json
            
            uri = uri or os.getenv('DATABASE_URL')
            if not uri:
                host = os.getenv('POSTGRES_HOST', 'localhost')
                port = os.getenv('POSTGRES_PORT', '5432')
                user = os.getenv('POSTGRES_USER', 'user')
                password = os.getenv('POSTGRES_PASSWORD', 'password')
                database = os.getenv('POSTGRES_DB', 'osint_db')
                uri = f"postgresql://{user}:{password}@{host}:{port}/{database}"
            
            self._conn = psycopg2.connect(uri)
            self._conn.autocommit = True
            
            self._init_tables()
            logger.info("PostgreSQL storage initialized")
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL: {e}")
            raise
    
    def _init_tables(self):
        """初始化数据表"""
        with self._conn.cursor() as cur:
            # 采集记录表
            cur.execute('''
                CREATE TABLE IF NOT EXISTS collections (
                    id VARCHAR(64) PRIMARY KEY,
                    platform VARCHAR(32) NOT NULL,
                    keyword VARCHAR(255) NOT NULL,
                    collected_at TIMESTAMP NOT NULL,
                    items_count INTEGER DEFAULT 0,
                    status VARCHAR(32) DEFAULT 'completed',
                    metadata JSONB DEFAULT '{}'
                )
            ''')
            
            # 采集数据表
            cur.execute('''
                CREATE TABLE IF NOT EXISTS collected_items (
                    id VARCHAR(64) PRIMARY KEY,
                    collection_id VARCHAR(64) REFERENCES collections(id),
                    platform VARCHAR(32) NOT NULL,
                    content TEXT,
                    author VARCHAR(255),
                    author_id VARCHAR(255),
                    url TEXT,
                    publish_time TIMESTAMP,
                    likes INTEGER DEFAULT 0,
                    comments INTEGER DEFAULT 0,
                    shares INTEGER DEFAULT 0,
                    sentiment VARCHAR(32),
                    sentiment_score FLOAT,
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 分析记录表
            cur.execute('''
                CREATE TABLE IF NOT EXISTS analyses (
                    id VARCHAR(64) PRIMARY KEY,
                    collection_id VARCHAR(64),
                    analysis_type VARCHAR(64) NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    source_count INTEGER DEFAULT 0,
                    results JSONB DEFAULT '{}'
                )
            ''')
            
            # 创建索引
            cur.execute('CREATE INDEX IF NOT EXISTS idx_collections_collected_at ON collections(collected_at DESC)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_items_collection_id ON collected_items(collection_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_items_content ON collected_items USING gin(to_tsvector(\'simple\', content))')
    
    def save_collection(self, record: CollectionRecord) -> str:
        import json
        
        with self._conn.cursor() as cur:
            cur.execute('''
                INSERT INTO collections (id, platform, keyword, collected_at, items_count, status, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    items_count = EXCLUDED.items_count,
                    status = EXCLUDED.status,
                    metadata = EXCLUDED.metadata
            ''', (
                record.id, record.platform, record.keyword,
                record.collected_at, record.items_count, record.status,
                json.dumps(record.metadata)
            ))
        return record.id
    
    def get_collection(self, collection_id: str) -> Optional[CollectionRecord]:
        from psycopg2.extras import RealDictCursor
        
        with self._conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT * FROM collections WHERE id = %s', (collection_id,))
            row = cur.fetchone()
            if row:
                return CollectionRecord(**dict(row))
        return None
    
    def list_collections(self, page: int = 1, page_size: int = 20) -> List[CollectionRecord]:
        from psycopg2.extras import RealDictCursor
        
        offset = (page - 1) * page_size
        with self._conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('''
                SELECT * FROM collections 
                ORDER BY collected_at DESC 
                LIMIT %s OFFSET %s
            ''', (page_size, offset))
            
            return [CollectionRecord(**dict(row)) for row in cur.fetchall()]
    
    def save_items(self, collection_id: str, items: List[CollectedItemRecord]) -> int:
        import json
        from psycopg2.extras import execute_values
        
        if not items:
            return 0
        
        with self._conn.cursor() as cur:
            values = [
                (
                    item.id, collection_id, item.platform, item.content,
                    item.author, item.author_id, item.url, item.publish_time,
                    item.likes, item.comments, item.shares,
                    item.sentiment, item.sentiment_score,
                    json.dumps(item.metadata), item.created_at
                )
                for item in items
            ]
            
            execute_values(cur, '''
                INSERT INTO collected_items 
                (id, collection_id, platform, content, author, author_id, url, 
                 publish_time, likes, comments, shares, sentiment, sentiment_score, 
                 metadata, created_at)
                VALUES %s
            ''', values)
            
            # 更新数量
            cur.execute('''
                UPDATE collections SET items_count = (
                    SELECT COUNT(*) FROM collected_items WHERE collection_id = %s
                ) WHERE id = %s
            ''', (collection_id, collection_id))
        
        return len(items)
    
    def get_items(self, collection_id: str, page: int = 1, page_size: int = 20) -> List[CollectedItemRecord]:
        from psycopg2.extras import RealDictCursor
        
        offset = (page - 1) * page_size
        with self._conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('''
                SELECT * FROM collected_items 
                WHERE collection_id = %s 
                LIMIT %s OFFSET %s
            ''', (collection_id, page_size, offset))
            
            return [CollectedItemRecord(**dict(row)) for row in cur.fetchall()]
    
    def save_analysis(self, record: AnalysisRecord) -> str:
        import json
        
        with self._conn.cursor() as cur:
            cur.execute('''
                INSERT INTO analyses (id, collection_id, analysis_type, created_at, source_count, results)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET results = EXCLUDED.results
            ''', (
                record.id, record.collection_id, record.analysis_type,
                record.created_at, record.source_count, 
                json.dumps(record.results)
            ))
        return record.id
    
    def get_analysis(self, analysis_id: str) -> Optional[AnalysisRecord]:
        from psycopg2.extras import RealDictCursor
        
        with self._conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT * FROM analyses WHERE id = %s', (analysis_id,))
            row = cur.fetchone()
            if row:
                return AnalysisRecord(**dict(row))
        return None


class StorageFactory:
    """存储工厂"""
    
    @staticmethod
    def create(storage_type: str = None) -> BaseStorage:
        """
        创建存储实例
        
        Args:
            storage_type: 存储类型 (memory, mongo, postgres)
                         如果不指定，从环境变量 STORAGE_TYPE 读取
        """
        storage_type = storage_type or os.getenv('STORAGE_TYPE', 'memory')
        
        if storage_type == 'memory':
            return MemoryStorage()
        elif storage_type == 'mongo':
            return MongoStorage()
        elif storage_type == 'postgres':
            return PostgresStorage()
        else:
            logger.warning(f"Unknown storage type: {storage_type}, using memory")
            return MemoryStorage()


# 全局存储实例
_storage: Optional[BaseStorage] = None


def get_storage() -> BaseStorage:
    """获取存储实例"""
    global _storage
    if _storage is None:
        _storage = StorageFactory.create()
    return _storage


def init_storage(storage_type: str = None) -> BaseStorage:
    """初始化存储"""
    global _storage
    _storage = StorageFactory.create(storage_type)
    return _storage
