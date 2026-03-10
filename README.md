# OSINT CN - 开源情报系统

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue.svg)](https://docs.docker.com/compose/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

一个专注于中文互联网的开源情报采集与分析系统，提供多平台数据采集、中文文本处理、智能分析等功能。

## 🌟 功能特性

### 📊 多平台数据采集
- **微博** - 搜索采集、用户主页采集
- **知乎** - 问答内容、用户信息
- **百度** - 搜索结果采集
- **抖音** - 短视频信息（需要额外配置）

### 📝 中文文本处理
- 中文分词（基于 jieba）
- 情感分析（正面/负面/中性）
- 关键词提取（TF-IDF / TextRank）
- 命名实体识别（人名、地名、机构）
- 文本摘要、相似度计算

### 📈 智能分析
- **情感统计** - 批量分析情感倾向
- **趋势分析** - 时间序列、增长率、峰值检测
- **关系网络** - 用户关系图谱、社区检测
- **风险评估** - 关键词风险、传播风险、综合评分

### 🔧 系统特性
- RESTful API 接口
- Docker 一键部署
- 多数据库支持（PostgreSQL、MongoDB、Redis、Elasticsearch、Neo4j）
- 完善的日志和错误追踪

## 🚀 快速开始

### 环境要求
- Docker & Docker Compose
- Python 3.9+ (如需本地开发)

### 使用 Docker 部署

1. **克隆项目**
```bash
git clone https://github.com/liyihang/osint_cn.git
cd osint_cn
```

2. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，填入你的配置
```

3. **启动服务**
```bash
docker-compose up -d
```

4. **访问系统**
- 首页: http://localhost:5001/
- 健康检查: http://localhost:5001/health
- Neo4j 管理界面: http://localhost:7474/

### 本地开发

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 运行
flask run --host=0.0.0.0 --port=5000
```

## 📖 API 文档

### 基础接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 首页（API 文档） |
| `/health` | GET | 健康检查 |
| `/api/platforms` | GET | 获取支持的平台列表 |

### 数据采集

```bash
# 采集单平台数据（示例：B站）
curl -X POST http://localhost:5001/api/collect \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "bilibili",
    "keyword": "人工智能",
    "max_items": 20
  }'

# 可选平台：weibo / douyin / kuaishou / zhihu / baidu / wechat / xiaohongshu / bilibili / tieba / toutiao

# 查询采集记录（已落库存储层）
curl 'http://localhost:5001/api/collections?page=1&page_size=10'

# 查询采集明细
curl 'http://localhost:5001/api/collections/<collection_id>?page=1&page_size=20'
```

### 文本处理

```bash
# 情感分析
curl -X POST http://localhost:5001/api/sentiment \
  -H "Content-Type: application/json" \
  -d '{"text": "这个产品真的很棒，非常满意！"}'

# 响应:
# {"result": {"sentiment": "positive", "score": 0.7, "confidence": 0.143}, "status": "success"}
```

```bash
# 关键词提取
curl -X POST http://localhost:5001/api/keywords \
  -H "Content-Type: application/json" \
  -d '{
    "text": "人工智能正在改变各行各业，机器学习和深度学习技术得到广泛应用",
    "top_k": 5
  }'
```

```bash
# 文本处理（分词、实体识别）
curl -X POST http://localhost:5001/api/process-text \
  -H "Content-Type: application/json" \
  -d '{
    "text": "张三在北京工作",
    "operations": ["segment", "entities"]
  }'
```

### 数据分析

```bash
# 综合分析
curl -X POST http://localhost:5001/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "data": [
      {"content": "这个产品真的很棒", "author": "用户A"},
      {"content": "太差了，非常失望", "author": "用户B"}
    ]
  }'

# 风险评估
curl -X POST http://localhost:5001/api/analyze/risk \
  -H "Content-Type: application/json" \
  -d '{
    "data": [{"content": "需要分析的内容..."}]
  }'

# Dashboard 一体化流水线：多渠道采集 + 词云 + 舆情报告
curl -X POST http://localhost:5001/api/dashboard/pipeline \
  -H "Content-Type: application/json" \
  -d '{
    "keyword": "某公司或产品名",
    "platforms": ["weibo", "zhihu", "baidu", "bilibili"],
    "max_items": 150
  }'
```

### Dashboard 场景能力

当前 Dashboard 已支持以下闭环能力：

- 输入关键词（公司、产品、品牌、事件）
- 勾选多渠道平台进行采集
- 支持“品牌舆情 / 客诉投诉 / 竞品对比 / 深度报告”快捷平台组合
- 自动做情感、趋势、风险分析
- 自动生成词云数据
- 自动输出舆情/客诉分析报告和参考建议
- 可选接入 AI 接口增强报告建议
- 支持导出 Word / PDF 分析报告
- 支持创建监控对象并按阈值定时监控
- 支持多关键词、多平台监控方案管理

### 监控对象能力

系统设置页现已支持：

- 创建监控对象
- 创建监控分组（品牌组、产品组、竞品组等）
- 配置多个关键词
- 配置多个采集平台
- 为监控对象绑定分组和标签
- 设置监控间隔和每平台采集量
- 支持最高 500 条/平台的高采样监控配置
- 设置负面占比、风险分、采集量阈值
- 手动立即执行监控对象
- 自动生成预警与分析报告

### 分组总览大屏

Dashboard 已新增分组总览视图，可直接查看：

- 品牌组 / 产品组 / 竞品组的热度对比
- 分组风险分与负面占比排行
- 每个分组的高频关键词
- 重点分组的最新摘要与风险提示

### 竞品对比专页

Dashboard 现已支持竞品对比视图，可直接：

- 选择某个品牌组或产品组作为对比基准
- 横向查看与竞品组的热度差、风险分差、负面占比差
- 识别共同高频词，判断竞争焦点是否重合
- 在导出报告中附带分组对比与竞品摘要

### 报告模板增强

导出的 Word / PDF 报告现已包含：

- 封面标题
- 执行摘要
- 核心指标
- 关键发现
- 处置建议
- AI 研判与公关口径
- 高频热词与平台采集附录

## 📁 项目结构

```
osint_cn/
├── osint_cn/               # 核心模块
│   ├── api.py              # Flask API 接口
│   ├── analysis.py         # 数据分析模块
│   ├── collection.py       # 数据采集模块
│   ├── config.py           # 配置管理
│   └── logging_config.py   # 日志配置
├── storage/                # 存储层
│   ├── database.py         # 数据库连接
│   └── db_manager.py       # 数据库管理器
├── processing.py           # 文本处理模块
├── core_module.py          # 核心协调模块
├── tests/                  # 测试用例
├── scripts/                # 脚本
│   └── init_db.sh          # 数据库初始化
├── config/                 # 配置文件
├── docker-compose.yml      # Docker 编排
├── Dockerfile              # Docker 构建
├── requirements.txt        # Python 依赖
└── .env.example            # 环境变量模板
```

## ⚙️ 配置说明

### 环境变量

复制 `.env.example` 为 `.env` 并配置：

```bash
# 应用配置
DEBUG=true
SECRET_KEY=your_secret_key
LOG_LEVEL=INFO

# PostgreSQL
POSTGRES_USER=user
POSTGRES_PASSWORD=your_password
POSTGRES_DB=osint_db

# 平台 Cookie（可选，用于采集）
WEIBO_COOKIE=your_weibo_cookie
ZHIHU_COOKIE=your_zhihu_cookie

# 第三方 API（可选）
# OPENAI_API_KEY=your_key
# AI_API_BASE=https://api.openai.com/v1
# AI_MODEL=gpt-4o-mini
```

说明：

- OPENAI_API_KEY 或 AI_API_KEY：兼容 OpenAI 风格接口的密钥
- AI_API_BASE：如果你使用第三方兼容网关，可替换基础地址
- AI_MODEL：用于报告建议生成的模型名称
- 未配置 AI Key 时，系统仍可运行，只是不启用 AI 增强建议

### 数据库

系统使用多种数据库：

| 数据库 | 用途 |
|--------|------|
| PostgreSQL | 结构化数据存储（采集数据、任务记录） |
| MongoDB | 非结构化数据（原始数据、处理结果） |
| Redis | 缓存、队列 |
| Elasticsearch | 全文搜索 |
| Neo4j | 关系图谱 |

## 🧪 测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_core.py -v

# 带覆盖率
pytest --cov=osint_cn
```

## 📝 使用示例

### Python SDK 使用

```python
from core_module import OSINTCore

# 创建核心实例
core = OSINTCore()

# 采集数据
result = core.collect('weibo', '人工智能', limit=50)
print(f"采集到 {result.data['count']} 条数据")

# 分析数据
analysis = core.analyze(result.data['items'])
print(f"风险等级: {analysis.data['risk']['data']['risk_level']}")

# 运行完整流水线
pipeline_result = core.run_pipeline('weibo', '机器学习', limit=100)
```

### 跨平台比较

```python
# 比较多平台数据
comparison = core.compare_platforms(
    keyword='人工智能',
    platforms=['weibo', 'zhihu', 'baidu'],
    limit=50
)

for platform, data in comparison['platforms'].items():
    print(f"{platform}: {data['count']} 条, 情感得分: {data['sentiment']}")
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

## ⚠️ 免责声明

本项目仅供学习和研究使用。使用本工具采集数据时，请遵守相关平台的服务条款和当地法律法规。开发者不对滥用本工具造成的任何后果负责。