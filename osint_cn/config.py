import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

# 尝试加载 python-dotenv
try:
    from dotenv import load_dotenv
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False


def _load_env_file(env_file: str = None) -> None:
    """
    加载 .env 文件中的环境变量
    
    优先级顺序:
    1. 指定的 env_file 参数
    2. 环境变量 OSINT_ENV_FILE
    3. 当前目录的 .env 文件
    4. 项目根目录的 .env 文件
    """
    if not HAS_DOTENV:
        return
    
    if env_file and Path(env_file).exists():
        load_dotenv(env_file)
        return
    
    # 从环境变量获取 .env 文件路径
    env_from_var = os.getenv('OSINT_ENV_FILE')
    if env_from_var and Path(env_from_var).exists():
        load_dotenv(env_from_var)
        return
    
    # 查找 .env 文件的可能位置
    possible_paths = [
        Path('.env'),
        Path(__file__).parent.parent / '.env',
        Path.cwd() / '.env',
    ]
    
    for path in possible_paths:
        if path.exists():
            load_dotenv(path)
            return


# 在模块加载时自动加载 .env 文件
_load_env_file()


@dataclass
class DatabaseConfig:
    """数据库配置"""
    host: str = 'localhost'
    port: int = 5432
    user: str = 'user'
    password: str = 'password'
    database: str = 'osint_db'
    
    @classmethod
    def from_env(cls, prefix: str = 'POSTGRES') -> 'DatabaseConfig':
        """从环境变量加载配置"""
        return cls(
            host=os.getenv(f'{prefix}_HOST', 'localhost'),
            port=int(os.getenv(f'{prefix}_PORT', '5432')),
            user=os.getenv(f'{prefix}_USER', 'user'),
            password=os.getenv(f'{prefix}_PASSWORD', 'password'),
            database=os.getenv(f'{prefix}_DB', 'osint_db')
        )
    
    def to_url(self) -> str:
        """转换为连接 URL"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass
class RedisConfig:
    """Redis 配置"""
    host: str = 'localhost'
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> 'RedisConfig':
        return cls(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', '6379')),
            db=int(os.getenv('REDIS_DB', '0')),
            password=os.getenv('REDIS_PASSWORD')
        )


@dataclass
class MongoConfig:
    """MongoDB 配置"""
    host: str = 'localhost'
    port: int = 27017
    database: str = 'osint_db'
    username: Optional[str] = None
    password: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> 'MongoConfig':
        return cls(
            host=os.getenv('MONGO_HOST', 'localhost'),
            port=int(os.getenv('MONGO_PORT', '27017')),
            database=os.getenv('MONGO_DB', 'osint_db'),
            username=os.getenv('MONGO_USER'),
            password=os.getenv('MONGO_PASSWORD')
        )
    
    def to_url(self) -> str:
        if self.username and self.password:
            return f"mongodb://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        return f"mongodb://{self.host}:{self.port}/{self.database}"


@dataclass
class ElasticsearchConfig:
    """Elasticsearch 配置"""
    host: str = 'localhost'
    port: int = 9200
    scheme: str = 'http'
    username: Optional[str] = None
    password: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> 'ElasticsearchConfig':
        return cls(
            host=os.getenv('ES_HOST', 'localhost'),
            port=int(os.getenv('ES_PORT', '9200')),
            scheme=os.getenv('ES_SCHEME', 'http'),
            username=os.getenv('ES_USER'),
            password=os.getenv('ES_PASSWORD')
        )


@dataclass
class Neo4jConfig:
    """Neo4j 配置"""
    host: str = 'localhost'
    port: int = 7687
    user: str = 'neo4j'
    password: str = 'password'
    
    @classmethod
    def from_env(cls) -> 'Neo4jConfig':
        return cls(
            host=os.getenv('NEO4J_HOST', 'localhost'),
            port=int(os.getenv('NEO4J_PORT', '7687')),
            user=os.getenv('NEO4J_USER', 'neo4j'),
            password=os.getenv('NEO4J_PASSWORD', 'password')
        )
    
    def to_uri(self) -> str:
        return f"bolt://{self.host}:{self.port}"


@dataclass
class CollectionConfig:
    """采集配置"""
    rate_limit: float = 1.0  # 请求间隔（秒）
    max_retries: int = 3
    timeout: int = 30
    max_items: int = 1000
    user_agent: str = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    
    # 平台 Cookie（可选）
    weibo_cookie: str = ''
    zhihu_cookie: str = ''


@dataclass
class AnalysisConfig:
    """分析配置"""
    sentiment_threshold_positive: float = 0.2
    sentiment_threshold_negative: float = -0.2
    risk_alert_threshold: float = 0.75
    risk_warning_threshold: float = 0.5
    max_keywords: int = 20


@dataclass
class Config:
    """主配置类"""
    debug: bool = True
    secret_key: str = 'your_secret_key_change_in_production'
    log_level: str = 'INFO'
    log_file: str = 'logs/app.log'
    
    # 子配置
    postgres: DatabaseConfig = field(default_factory=DatabaseConfig)
    mongo: MongoConfig = field(default_factory=MongoConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    elasticsearch: ElasticsearchConfig = field(default_factory=ElasticsearchConfig)
    neo4j: Neo4jConfig = field(default_factory=Neo4jConfig)
    collection: CollectionConfig = field(default_factory=CollectionConfig)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    
    @classmethod
    def from_env(cls) -> 'Config':
        """从环境变量加载配置"""
        return cls(
            debug=os.getenv('DEBUG', 'true').lower() == 'true',
            secret_key=os.getenv('SECRET_KEY', 'your_secret_key_change_in_production'),
            log_level=os.getenv('LOG_LEVEL', 'INFO'),
            postgres=DatabaseConfig.from_env('POSTGRES'),
            mongo=MongoConfig.from_env(),
            redis=RedisConfig.from_env(),
            elasticsearch=ElasticsearchConfig.from_env(),
            neo4j=Neo4jConfig.from_env(),
        )
    
    @classmethod
    def from_yaml(cls, path: str) -> 'Config':
        """从 YAML 文件加载配置"""
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        config = cls()
        
        if 'debug' in data:
            config.debug = data['debug']
        if 'secret_key' in data:
            config.secret_key = data['secret_key']
        if 'log_level' in data:
            config.log_level = data['log_level']
        
        # 加载数据库配置
        if 'database' in data:
            db = data['database']
            config.postgres = DatabaseConfig(
                host=db.get('host', 'localhost'),
                port=db.get('port', 5432),
                user=db.get('username', 'user'),
                password=db.get('password', 'password'),
                database=db.get('database', 'osint_db')
            )
        
        # 加载采集配置
        if 'collection' in data:
            coll = data['collection']
            config.collection = CollectionConfig(
                max_items=coll.get('max_items', 1000),
                rate_limit=coll.get('collection_interval', 60) / 60  # 转换为秒
            )
        
        # 加载分析配置
        if 'analysis' in data:
            analysis = data['analysis']
            thresholds = analysis.get('thresholds', {})
            config.analysis = AnalysisConfig(
                risk_alert_threshold=thresholds.get('alert', 0.75),
                risk_warning_threshold=thresholds.get('warning', 0.5)
            )
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'debug': self.debug,
            'log_level': self.log_level,
            'postgres': {
                'host': self.postgres.host,
                'port': self.postgres.port,
                'database': self.postgres.database
            },
            'mongo': {
                'host': self.mongo.host,
                'port': self.mongo.port,
                'database': self.mongo.database
            },
            'redis': {
                'host': self.redis.host,
                'port': self.redis.port
            },
            'elasticsearch': {
                'host': self.elasticsearch.host,
                'port': self.elasticsearch.port
            },
            'neo4j': {
                'host': self.neo4j.host,
                'port': self.neo4j.port
            }
        }


# 全局配置实例
_config: Optional[Config] = None


def get_config(env_file: str = None) -> Config:
    """
    获取配置实例
    
    Args:
        env_file: 可选的 .env 文件路径，首次调用时会加载
        
    Returns:
        Config 实例
    """
    global _config
    if _config is None:
        # 加载 .env 文件
        if env_file:
            _load_env_file(env_file)
        
        # 优先从环境变量加载，如果存在配置文件则从文件加载
        config_path = os.getenv('CONFIG_PATH', 'config/default.yaml')
        if os.path.exists(config_path):
            _config = Config.from_yaml(config_path)
            # 用环境变量覆盖敏感配置
            _override_from_env(_config)
        else:
            _config = Config.from_env()
    return _config


def _override_from_env(config: Config) -> None:
    """使用环境变量覆盖配置中的敏感信息"""
    # 覆盖 secret_key
    if os.getenv('SECRET_KEY'):
        config.secret_key = os.getenv('SECRET_KEY')
    
    # 覆盖数据库密码
    if os.getenv('POSTGRES_PASSWORD'):
        config.postgres.password = os.getenv('POSTGRES_PASSWORD')
    if os.getenv('MONGO_PASSWORD'):
        config.mongo.password = os.getenv('MONGO_PASSWORD')
    if os.getenv('REDIS_PASSWORD'):
        config.redis.password = os.getenv('REDIS_PASSWORD')
    if os.getenv('ES_PASSWORD'):
        config.elasticsearch.password = os.getenv('ES_PASSWORD')
    if os.getenv('NEO4J_PASSWORD'):
        config.neo4j.password = os.getenv('NEO4J_PASSWORD')
    
    # 覆盖 Cookie
    if os.getenv('WEIBO_COOKIE'):
        config.collection.weibo_cookie = os.getenv('WEIBO_COOKIE')
    if os.getenv('ZHIHU_COOKIE'):
        config.collection.zhihu_cookie = os.getenv('ZHIHU_COOKIE')


def reload_config(path: str = None, env_file: str = None) -> Config:
    """
    重新加载配置
    
    Args:
        path: YAML 配置文件路径
        env_file: .env 文件路径
        
    Returns:
        新的 Config 实例
    """
    global _config
    
    # 重新加载 .env 文件
    if env_file:
        _load_env_file(env_file)
    
    if path:
        _config = Config.from_yaml(path)
        _override_from_env(_config)
    else:
        _config = Config.from_env()
    return _config


def get_env(key: str, default: str = None) -> Optional[str]:
    """
    获取环境变量，支持 .env 文件
    
    Args:
        key: 环境变量名
        default: 默认值
        
    Returns:
        环境变量值
    """
    return os.getenv(key, default)


def get_env_bool(key: str, default: bool = False) -> bool:
    """获取布尔类型环境变量"""
    value = os.getenv(key)
    if value is None:
        return default
    return value.lower() in ('true', '1', 'yes', 'on')


def get_env_int(key: str, default: int = 0) -> int:
    """获取整数类型环境变量"""
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def get_env_float(key: str, default: float = 0.0) -> float:
    """获取浮点数类型环境变量"""
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default