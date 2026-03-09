#!/bin/bash

# OSINT CN - 数据库初始化脚本
# 用法: ./init_db.sh

set -e

echo "=========================================="
echo "OSINT CN - 数据库初始化"
echo "=========================================="

# 配置变量
POSTGRES_USER=${POSTGRES_USER:-user}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-password}
POSTGRES_DB=${POSTGRES_DB:-db_name}
POSTGRES_HOST=${POSTGRES_HOST:-postgres}

MONGO_DB=${MONGO_DB:-osint_db}
MONGO_HOST=${MONGO_HOST:-mongo}

ES_HOST=${ES_HOST:-elasticsearch}
ES_PORT=${ES_PORT:-9200}

# 等待服务就绪
wait_for_service() {
    local host=$1
    local port=$2
    local max_attempts=30
    local attempt=1
    
    echo "等待 $host:$port 就绪..."
    
    while ! nc -z $host $port 2>/dev/null; do
        if [ $attempt -ge $max_attempts ]; then
            echo "错误: $host:$port 连接超时"
            return 1
        fi
        echo "  尝试 $attempt/$max_attempts..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo "$host:$port 已就绪"
}

# ==========================================
# PostgreSQL 初始化
# ==========================================
echo ""
echo ">>> 初始化 PostgreSQL..."

wait_for_service $POSTGRES_HOST 5432

PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB << 'EOSQL'

-- 创建数据采集表
CREATE TABLE IF NOT EXISTS collected_data (
    id SERIAL PRIMARY KEY,
    platform VARCHAR(50) NOT NULL,
    content TEXT,
    author VARCHAR(255),
    author_id VARCHAR(100),
    url TEXT,
    publish_time TIMESTAMP,
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_collected_data_platform ON collected_data(platform);
CREATE INDEX IF NOT EXISTS idx_collected_data_created_at ON collected_data(created_at);
CREATE INDEX IF NOT EXISTS idx_collected_data_author ON collected_data(author);

-- 创建分析结果表
CREATE TABLE IF NOT EXISTS analysis_results (
    id SERIAL PRIMARY KEY,
    analysis_type VARCHAR(50) NOT NULL,
    task_id VARCHAR(100),
    data JSONB,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_analysis_results_type ON analysis_results(analysis_type);
CREATE INDEX IF NOT EXISTS idx_analysis_results_task_id ON analysis_results(task_id);

-- 创建任务表
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(100) UNIQUE NOT NULL,
    task_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    config JSONB,
    result JSONB,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_type ON tasks(task_type);

-- 创建关键词表
CREATE TABLE IF NOT EXISTS keywords (
    id SERIAL PRIMARY KEY,
    keyword VARCHAR(255) NOT NULL,
    platform VARCHAR(50),
    frequency INTEGER DEFAULT 0,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(keyword, platform)
);

EOSQL

echo "PostgreSQL 初始化完成"

# ==========================================
# MongoDB 初始化
# ==========================================
echo ""
echo ">>> 初始化 MongoDB..."

wait_for_service $MONGO_HOST 27017

mongosh --host $MONGO_HOST --eval "
    // 切换到数据库
    db = db.getSiblingDB('$MONGO_DB');
    
    // 创建集合
    db.createCollection('raw_data');
    db.createCollection('processed_data');
    db.createCollection('user_profiles');
    db.createCollection('relationships');
    
    // 创建索引
    db.raw_data.createIndex({ platform: 1, created_at: -1 });
    db.raw_data.createIndex({ author_id: 1 });
    db.raw_data.createIndex({ 'metadata.keywords': 1 });
    
    db.processed_data.createIndex({ source_id: 1 });
    db.processed_data.createIndex({ 'sentiment.score': 1 });
    
    db.user_profiles.createIndex({ platform: 1, user_id: 1 }, { unique: true });
    
    db.relationships.createIndex({ from_id: 1 });
    db.relationships.createIndex({ to_id: 1 });
    db.relationships.createIndex({ type: 1 });
    
    print('MongoDB 集合和索引创建完成');
"

echo "MongoDB 初始化完成"

# ==========================================
# Elasticsearch 初始化
# ==========================================
echo ""
echo ">>> 初始化 Elasticsearch..."

wait_for_service $ES_HOST $ES_PORT

# 创建内容索引
curl -s -X PUT "http://$ES_HOST:$ES_PORT/osint_content" -H 'Content-Type: application/json' -d '
{
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "analysis": {
            "analyzer": {
                "chinese_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase"]
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "platform": { "type": "keyword" },
            "content": { 
                "type": "text",
                "analyzer": "chinese_analyzer"
            },
            "title": { 
                "type": "text",
                "analyzer": "chinese_analyzer"
            },
            "author": { "type": "keyword" },
            "author_id": { "type": "keyword" },
            "url": { "type": "keyword" },
            "publish_time": { "type": "date" },
            "likes": { "type": "integer" },
            "comments": { "type": "integer" },
            "shares": { "type": "integer" },
            "sentiment_score": { "type": "float" },
            "sentiment_label": { "type": "keyword" },
            "keywords": { "type": "keyword" },
            "created_at": { "type": "date" }
        }
    }
}
' && echo ""

# 创建分析结果索引
curl -s -X PUT "http://$ES_HOST:$ES_PORT/osint_analysis" -H 'Content-Type: application/json' -d '
{
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0
    },
    "mappings": {
        "properties": {
            "analysis_type": { "type": "keyword" },
            "task_id": { "type": "keyword" },
            "data": { "type": "object", "enabled": false },
            "created_at": { "type": "date" }
        }
    }
}
' && echo ""

echo "Elasticsearch 初始化完成"

# ==========================================
# 完成
# ==========================================
echo ""
echo "=========================================="
echo "所有数据库初始化完成！"
echo "=========================================="