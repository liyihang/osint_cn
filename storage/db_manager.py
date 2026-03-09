"""
数据库服务管理模块

提供数据库连接池管理、健康检查和自动重连机制
"""

import os
import time
import logging
import threading
from typing import Dict, Optional, Any
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class DatabaseStatus(Enum):
    """数据库状态"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    ERROR = "error"


@dataclass
class DatabaseHealth:
    """数据库健康状态"""
    name: str
    status: DatabaseStatus
    latency_ms: float = 0.0
    error: Optional[str] = None
    last_check: Optional[float] = None


class DatabaseManager:
    """数据库连接管理器"""
    
    def __init__(self):
        self._connections: Dict[str, Any] = {}
        self._health: Dict[str, DatabaseHealth] = {}
        self._lock = threading.Lock()
        self._config = self._load_config()
        self._retry_config = {
            'max_retries': 3,
            'retry_delay': 2,
            'backoff_factor': 2
        }
    
    def _load_config(self) -> Dict:
        """从环境变量加载配置"""
        return {
            'postgres': {
                'host': os.getenv('POSTGRES_HOST', 'localhost'),
                'port': int(os.getenv('POSTGRES_PORT', 5432)),
                'user': os.getenv('POSTGRES_USER', 'user'),
                'password': os.getenv('POSTGRES_PASSWORD', 'password'),
                'database': os.getenv('POSTGRES_DB', 'db_name'),
            },
            'mongo': {
                'host': os.getenv('MONGO_HOST', 'localhost'),
                'port': int(os.getenv('MONGO_PORT', 27017)),
                'database': os.getenv('MONGO_DB', 'osint_db'),
            },
            'redis': {
                'host': os.getenv('REDIS_HOST', 'localhost'),
                'port': int(os.getenv('REDIS_PORT', 6379)),
                'db': int(os.getenv('REDIS_DB', 0)),
            },
            'elasticsearch': {
                'host': os.getenv('ES_HOST', 'localhost'),
                'port': int(os.getenv('ES_PORT', 9200)),
            },
            'neo4j': {
                'host': os.getenv('NEO4J_HOST', 'localhost'),
                'port': int(os.getenv('NEO4J_PORT', 7687)),
                'user': os.getenv('NEO4J_USER', 'neo4j'),
                'password': os.getenv('NEO4J_PASSWORD', 'password'),
            }
        }
    
    def connect_postgres(self, force_reconnect: bool = False) -> Any:
        """连接 PostgreSQL"""
        if 'postgres' in self._connections and not force_reconnect:
            return self._connections['postgres']
        
        import psycopg2
        from psycopg2 import pool
        from psycopg2.extras import RealDictCursor
        
        config = self._config['postgres']
        
        connection_pool = pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=10,
            host=config['host'],
            port=config['port'],
            user=config['user'],
            password=config['password'],
            database=config['database'],
            cursor_factory=RealDictCursor
        )
        
        self._connections['postgres'] = connection_pool
        self._health['postgres'] = DatabaseHealth(
            name='postgres',
            status=DatabaseStatus.CONNECTED,
            last_check=time.time()
        )
        
        logger.info("PostgreSQL connection pool created")
        return connection_pool
    
    def connect_mongo(self, force_reconnect: bool = False) -> Any:
        """连接 MongoDB"""
        if 'mongo' in self._connections and not force_reconnect:
            return self._connections['mongo']
        
        from pymongo import MongoClient
        
        config = self._config['mongo']
        
        client = MongoClient(
            host=config['host'],
            port=config['port'],
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            maxPoolSize=10
        )
        
        db = client[config['database']]
        
        self._connections['mongo'] = db
        self._health['mongo'] = DatabaseHealth(
            name='mongo',
            status=DatabaseStatus.CONNECTED,
            last_check=time.time()
        )
        
        logger.info("MongoDB connection established")
        return db
    
    def connect_redis(self, force_reconnect: bool = False) -> Any:
        """连接 Redis"""
        if 'redis' in self._connections and not force_reconnect:
            return self._connections['redis']
        
        import redis
        
        config = self._config['redis']
        
        pool = redis.ConnectionPool(
            host=config['host'],
            port=config['port'],
            db=config['db'],
            max_connections=10,
            decode_responses=True
        )
        
        client = redis.Redis(connection_pool=pool)
        
        self._connections['redis'] = client
        self._health['redis'] = DatabaseHealth(
            name='redis',
            status=DatabaseStatus.CONNECTED,
            last_check=time.time()
        )
        
        logger.info("Redis connection established")
        return client
    
    def connect_elasticsearch(self, force_reconnect: bool = False) -> Any:
        """连接 Elasticsearch"""
        if 'elasticsearch' in self._connections and not force_reconnect:
            return self._connections['elasticsearch']
        
        from elasticsearch import Elasticsearch
        
        config = self._config['elasticsearch']
        
        es = Elasticsearch(
            [{'host': config['host'], 'port': config['port'], 'scheme': 'http'}],
            timeout=30,
            max_retries=3,
            retry_on_timeout=True
        )
        
        self._connections['elasticsearch'] = es
        self._health['elasticsearch'] = DatabaseHealth(
            name='elasticsearch',
            status=DatabaseStatus.CONNECTED,
            last_check=time.time()
        )
        
        logger.info("Elasticsearch connection established")
        return es
    
    def connect_neo4j(self, force_reconnect: bool = False) -> Any:
        """连接 Neo4j"""
        if 'neo4j' in self._connections and not force_reconnect:
            return self._connections['neo4j']
        
        from neo4j import GraphDatabase
        
        config = self._config['neo4j']
        uri = f"bolt://{config['host']}:{config['port']}"
        
        driver = GraphDatabase.driver(
            uri,
            auth=(config['user'], config['password']),
            max_connection_lifetime=3600,
            max_connection_pool_size=10
        )
        
        self._connections['neo4j'] = driver
        self._health['neo4j'] = DatabaseHealth(
            name='neo4j',
            status=DatabaseStatus.CONNECTED,
            last_check=time.time()
        )
        
        logger.info("Neo4j connection established")
        return driver
    
    def connect_all(self) -> Dict[str, bool]:
        """连接所有数据库"""
        results = {}
        
        for db_name in ['postgres', 'mongo', 'redis', 'elasticsearch', 'neo4j']:
            try:
                connect_method = getattr(self, f'connect_{db_name}')
                connect_method()
                results[db_name] = True
            except Exception as e:
                logger.error(f"Failed to connect to {db_name}: {e}")
                results[db_name] = False
                self._health[db_name] = DatabaseHealth(
                    name=db_name,
                    status=DatabaseStatus.ERROR,
                    error=str(e),
                    last_check=time.time()
                )
        
        return results
    
    def get_connection(self, db_name: str) -> Optional[Any]:
        """获取数据库连接"""
        return self._connections.get(db_name)
    
    @contextmanager
    def postgres_connection(self):
        """PostgreSQL 连接上下文管理器"""
        pool = self._connections.get('postgres')
        if not pool:
            pool = self.connect_postgres()
        
        conn = pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            pool.putconn(conn)
    
    def check_health(self, db_name: str) -> DatabaseHealth:
        """检查单个数据库健康状态"""
        start_time = time.time()
        
        try:
            if db_name == 'postgres':
                with self.postgres_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute('SELECT 1')
                        
            elif db_name == 'mongo':
                db = self._connections.get('mongo')
                if db:
                    db.command('ping')
                    
            elif db_name == 'redis':
                client = self._connections.get('redis')
                if client:
                    client.ping()
                    
            elif db_name == 'elasticsearch':
                es = self._connections.get('elasticsearch')
                if es:
                    es.ping()
                    
            elif db_name == 'neo4j':
                driver = self._connections.get('neo4j')
                if driver:
                    driver.verify_connectivity()
            
            latency = (time.time() - start_time) * 1000
            
            health = DatabaseHealth(
                name=db_name,
                status=DatabaseStatus.CONNECTED,
                latency_ms=round(latency, 2),
                last_check=time.time()
            )
            
        except Exception as e:
            health = DatabaseHealth(
                name=db_name,
                status=DatabaseStatus.ERROR,
                error=str(e),
                last_check=time.time()
            )
        
        self._health[db_name] = health
        return health
    
    def check_all_health(self) -> Dict[str, DatabaseHealth]:
        """检查所有数据库健康状态"""
        for db_name in self._connections.keys():
            self.check_health(db_name)
        return self._health.copy()
    
    def get_health_summary(self) -> Dict:
        """获取健康状态摘要"""
        self.check_all_health()
        
        summary = {
            'overall': 'healthy',
            'databases': {}
        }
        
        for name, health in self._health.items():
            summary['databases'][name] = {
                'status': health.status.value,
                'latency_ms': health.latency_ms,
                'error': health.error
            }
            
            if health.status != DatabaseStatus.CONNECTED:
                summary['overall'] = 'degraded'
        
        return summary
    
    def reconnect(self, db_name: str) -> bool:
        """重连数据库"""
        retry_delay = self._retry_config['retry_delay']
        
        for attempt in range(self._retry_config['max_retries']):
            try:
                logger.info(f"Attempting to reconnect to {db_name} (attempt {attempt + 1})")
                
                connect_method = getattr(self, f'connect_{db_name}')
                connect_method(force_reconnect=True)
                
                logger.info(f"Successfully reconnected to {db_name}")
                return True
                
            except Exception as e:
                logger.warning(f"Reconnection attempt {attempt + 1} failed: {e}")
                time.sleep(retry_delay)
                retry_delay *= self._retry_config['backoff_factor']
        
        logger.error(f"Failed to reconnect to {db_name} after all retries")
        return False
    
    def close_all(self):
        """关闭所有连接"""
        for name, conn in self._connections.items():
            try:
                if name == 'postgres' and hasattr(conn, 'closeall'):
                    conn.closeall()
                elif name == 'mongo' and hasattr(conn, 'client'):
                    conn.client.close()
                elif name == 'neo4j' and hasattr(conn, 'close'):
                    conn.close()
                elif hasattr(conn, 'close'):
                    conn.close()
                    
                logger.info(f"Closed connection to {name}")
                
            except Exception as e:
                logger.warning(f"Error closing {name} connection: {e}")
        
        self._connections.clear()
        self._health.clear()


# 全局数据库管理器实例
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """获取数据库管理器实例（单例）"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def init_databases():
    """初始化所有数据库连接"""
    manager = get_db_manager()
    return manager.connect_all()


def get_postgres():
    """获取 PostgreSQL 连接"""
    return get_db_manager().get_connection('postgres')


def get_mongo():
    """获取 MongoDB 连接"""
    return get_db_manager().get_connection('mongo')


def get_redis():
    """获取 Redis 连接"""
    return get_db_manager().get_connection('redis')


def get_elasticsearch():
    """获取 Elasticsearch 连接"""
    return get_db_manager().get_connection('elasticsearch')


def get_neo4j():
    """获取 Neo4j 连接"""
    return get_db_manager().get_connection('neo4j')
