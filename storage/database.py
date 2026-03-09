import os
from typing import Optional, Any, Dict, List
import logging

logger = logging.getLogger(__name__)


class Database:
    """统一数据库连接管理类"""
    
    def __init__(self, db_type: str, **kwargs):
        self.db_type = db_type
        self.connection = None
        self.config = kwargs
        self.connect(**kwargs)

    def connect(self, **kwargs):
        """根据数据库类型建立连接"""
        try:
            if self.db_type == 'postgresql':
                self.connection = self.connect_postgresql(**kwargs)
            elif self.db_type == 'mongodb':
                self.connection = self.connect_mongodb(**kwargs)
            elif self.db_type == 'elasticsearch':
                self.connection = self.connect_elasticsearch(**kwargs)
            elif self.db_type == 'redis':
                self.connection = self.connect_redis(**kwargs)
            elif self.db_type == 'neo4j':
                self.connection = self.connect_neo4j(**kwargs)
            else:
                raise ValueError(f"Unsupported database type: {self.db_type}")
            logger.info(f"Successfully connected to {self.db_type}")
        except Exception as e:
            logger.error(f"Failed to connect to {self.db_type}: {e}")
            raise

    def connect_postgresql(self, **kwargs) -> Any:
        """PostgreSQL 连接"""
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(
            host=kwargs.get('host', os.getenv('POSTGRES_HOST', 'postgres')),
            port=kwargs.get('port', os.getenv('POSTGRES_PORT', 5432)),
            user=kwargs.get('user', os.getenv('POSTGRES_USER', 'user')),
            password=kwargs.get('password', os.getenv('POSTGRES_PASSWORD', 'password')),
            database=kwargs.get('database', os.getenv('POSTGRES_DB', 'db_name')),
            cursor_factory=RealDictCursor
        )
        return conn

    def connect_mongodb(self, **kwargs) -> Any:
        """MongoDB 连接"""
        from pymongo import MongoClient
        
        host = kwargs.get('host', os.getenv('MONGO_HOST', 'mongo'))
        port = kwargs.get('port', int(os.getenv('MONGO_PORT', 27017)))
        client = MongoClient(host, port)
        db_name = kwargs.get('database', os.getenv('MONGO_DB', 'osint_db'))
        return client[db_name]

    def connect_elasticsearch(self, **kwargs) -> Any:
        """Elasticsearch 连接"""
        from elasticsearch import Elasticsearch
        
        host = kwargs.get('host', os.getenv('ES_HOST', 'elasticsearch'))
        port = kwargs.get('port', int(os.getenv('ES_PORT', 9200)))
        return Elasticsearch([{'host': host, 'port': port, 'scheme': 'http'}])

    def connect_redis(self, **kwargs) -> Any:
        """Redis 连接"""
        import redis
        
        return redis.Redis(
            host=kwargs.get('host', os.getenv('REDIS_HOST', 'redis')),
            port=kwargs.get('port', int(os.getenv('REDIS_PORT', 6379))),
            db=kwargs.get('db', 0),
            decode_responses=True
        )

    def connect_neo4j(self, **kwargs) -> Any:
        """Neo4j 连接"""
        from neo4j import GraphDatabase
        
        uri = kwargs.get('uri', f"bolt://{os.getenv('NEO4J_HOST', 'neo4j')}:7687")
        user = kwargs.get('user', os.getenv('NEO4J_USER', 'neo4j'))
        password = kwargs.get('password', os.getenv('NEO4J_PASSWORD', 'password'))
        return GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        """关闭数据库连接"""
        if self.connection:
            if self.db_type == 'neo4j':
                self.connection.close()
            elif self.db_type in ['postgresql']:
                self.connection.close()
            elif self.db_type == 'mongodb':
                self.connection.client.close()
            logger.info(f"Closed connection to {self.db_type}")


class PostgresRepository:
    """PostgreSQL 数据仓库"""
    
    def __init__(self, db: Database):
        self.db = db
        self.conn = db.connection
    
    def execute(self, query: str, params: tuple = None) -> List[Dict]:
        """执行查询"""
        with self.conn.cursor() as cursor:
            cursor.execute(query, params)
            if cursor.description:
                return cursor.fetchall()
            self.conn.commit()
            return []
    
    def insert_collected_data(self, platform: str, data: Dict) -> int:
        """插入采集数据"""
        query = """
            INSERT INTO collected_data (platform, content, metadata, created_at)
            VALUES (%s, %s, %s, NOW())
            RETURNING id
        """
        import json
        result = self.execute(query, (platform, data.get('content', ''), json.dumps(data)))
        return result[0]['id'] if result else None
    
    def get_collected_data(self, platform: str = None, limit: int = 100) -> List[Dict]:
        """获取采集数据"""
        if platform:
            query = "SELECT * FROM collected_data WHERE platform = %s ORDER BY created_at DESC LIMIT %s"
            return self.execute(query, (platform, limit))
        else:
            query = "SELECT * FROM collected_data ORDER BY created_at DESC LIMIT %s"
            return self.execute(query, (limit,))


class MongoRepository:
    """MongoDB 数据仓库"""
    
    def __init__(self, db: Database):
        self.db = db.connection
    
    def insert_document(self, collection: str, document: Dict) -> str:
        """插入文档"""
        result = self.db[collection].insert_one(document)
        return str(result.inserted_id)
    
    def find_documents(self, collection: str, query: Dict = None, limit: int = 100) -> List[Dict]:
        """查询文档"""
        cursor = self.db[collection].find(query or {}).limit(limit)
        return list(cursor)
    
    def update_document(self, collection: str, query: Dict, update: Dict) -> int:
        """更新文档"""
        result = self.db[collection].update_many(query, {'$set': update})
        return result.modified_count


class RedisCache:
    """Redis 缓存"""
    
    def __init__(self, db: Database):
        self.redis = db.connection
    
    def set(self, key: str, value: str, expire: int = 3600) -> bool:
        """设置缓存"""
        return self.redis.setex(key, expire, value)
    
    def get(self, key: str) -> Optional[str]:
        """获取缓存"""
        return self.redis.get(key)
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        return self.redis.delete(key) > 0
    
    def add_to_queue(self, queue_name: str, item: str) -> int:
        """添加到队列"""
        return self.redis.rpush(queue_name, item)
    
    def pop_from_queue(self, queue_name: str) -> Optional[str]:
        """从队列取出"""
        return self.redis.lpop(queue_name)


class ElasticsearchIndex:
    """Elasticsearch 索引操作"""
    
    def __init__(self, db: Database):
        self.es = db.connection
    
    def index_document(self, index: str, document: Dict, doc_id: str = None) -> Dict:
        """索引文档"""
        return self.es.index(index=index, body=document, id=doc_id)
    
    def search(self, index: str, query: Dict, size: int = 10) -> List[Dict]:
        """搜索文档"""
        result = self.es.search(index=index, body=query, size=size)
        return [hit['_source'] for hit in result['hits']['hits']]
    
    def full_text_search(self, index: str, text: str, fields: List[str] = None) -> List[Dict]:
        """全文搜索"""
        query = {
            'query': {
                'multi_match': {
                    'query': text,
                    'fields': fields or ['content', 'title', 'description']
                }
            }
        }
        return self.search(index, query)


class Neo4jGraph:
    """Neo4j 图数据库操作"""
    
    def __init__(self, db: Database):
        self.driver = db.connection
    
    def execute(self, query: str, params: Dict = None) -> List[Dict]:
        """执行 Cypher 查询"""
        with self.driver.session() as session:
            result = session.run(query, params or {})
            return [record.data() for record in result]
    
    def create_entity(self, label: str, properties: Dict) -> Dict:
        """创建实体节点"""
        query = f"CREATE (n:{label} $props) RETURN n"
        result = self.execute(query, {'props': properties})
        return result[0] if result else None
    
    def create_relationship(self, from_id: str, to_id: str, rel_type: str, properties: Dict = None) -> Dict:
        """创建关系"""
        query = """
            MATCH (a), (b)
            WHERE a.id = $from_id AND b.id = $to_id
            CREATE (a)-[r:%s $props]->(b)
            RETURN r
        """ % rel_type
        return self.execute(query, {'from_id': from_id, 'to_id': to_id, 'props': properties or {}})
    
    def find_relationships(self, entity_id: str, depth: int = 2) -> List[Dict]:
        """查找关系网络"""
        query = """
            MATCH path = (n {id: $entity_id})-[*1..%d]-(m)
            RETURN path
        """ % depth
        return self.execute(query, {'entity_id': entity_id})