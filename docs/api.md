# OSINT CN API 文档

## 概述

OSINT CN 提供 RESTful API 接口，支持数据采集、文本处理和智能分析功能。

**Base URL**: `http://localhost:5001`

**Content-Type**: `application/json`

---

## 基础接口

### 首页

**GET /**

返回系统首页，包含 API 文档和系统状态。

**响应**: HTML 页面

---

### 健康检查

**GET /health**

检查服务运行状态。

**响应**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00.000000",
  "version": "1.0.0",
  "uptime_seconds": 3600.5
}
```

---

### 获取支持的平台

**GET /api/platforms**

获取支持采集的平台列表。

**响应**:
```json
{
  "status": "success",
  "platforms": ["weibo", "douyin", "zhihu", "baidu"],
  "description": {
    "weibo": "微博 - 社交媒体平台",
    "zhihu": "知乎 - 问答社区",
    "douyin": "抖音 - 短视频平台",
    "baidu": "百度 - 搜索引擎"
  }
}
```

---

## 数据采集接口

### 采集数据

**POST /api/collect**

从指定平台采集数据。

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| platform | string | ✓ | 平台名称 (weibo/zhihu/baidu/douyin) |
| keyword | string | ✓ | 搜索关键词 |
| limit | integer | ✗ | 采集数量限制，默认 100 |
| config | object | ✗ | 采集器配置（如 cookie） |

**请求示例**:
```json
{
  "platform": "weibo",
  "keyword": "人工智能",
  "limit": 50,
  "config": {
    "cookie": "your_weibo_cookie"
  }
}
```

**响应**:
```json
{
  "status": "success",
  "message": "Collected 50 items from weibo",
  "count": 50,
  "data": [
    {
      "platform": "weibo",
      "content": "微博内容...",
      "author": "用户名",
      "author_id": "123456",
      "url": "https://weibo.com/...",
      "publish_time": "2024-01-01T12:00:00",
      "likes": 100,
      "comments": 20,
      "shares": 5,
      "metadata": {}
    }
  ]
}
```

---

## 文本处理接口

### 情感分析

**POST /api/sentiment**

分析文本情感倾向。

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| text | string | ✓* | 单条文本 |
| texts | array | ✓* | 多条文本列表 |

*注：text 和 texts 二选一*

**单条文本请求**:
```json
{
  "text": "这个产品真的很棒，非常满意！"
}
```

**单条文本响应**:
```json
{
  "status": "success",
  "result": {
    "sentiment": "positive",
    "score": 0.7,
    "confidence": 0.143
  }
}
```

**多条文本请求**:
```json
{
  "texts": [
    "这个产品真的很棒",
    "太差了，非常失望"
  ]
}
```

**多条文本响应**:
```json
{
  "status": "success",
  "count": 2,
  "results": [
    {"text": "这个产品真的很棒", "sentiment": "positive", "score": 0.7, "confidence": 0.2},
    {"text": "太差了，非常失望", "sentiment": "negative", "score": -0.7, "confidence": 0.25}
  ]
}
```

**情感标签说明**:
- `positive`: 正面情感 (score > 0.2)
- `negative`: 负面情感 (score < -0.2)
- `neutral`: 中性情感

---

### 关键词提取

**POST /api/keywords**

从文本中提取关键词。

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| text | string | ✓ | 待处理文本 |
| top_k | integer | ✗ | 返回关键词数量，默认 10 |
| method | string | ✗ | 算法：tfidf（默认）或 textrank |

**请求示例**:
```json
{
  "text": "人工智能正在改变各行各业，机器学习和深度学习技术得到广泛应用",
  "top_k": 5,
  "method": "tfidf"
}
```

**响应**:
```json
{
  "status": "success",
  "keywords": [
    {"keyword": "学习", "weight": 0.6419, "frequency": 2},
    {"keyword": "人工智能", "weight": 0.5254, "frequency": 1},
    {"keyword": "深度", "weight": 0.3865, "frequency": 1}
  ]
}
```

---

### 文本处理

**POST /api/process-text**

综合文本处理接口。

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| text | string | ✓ | 待处理文本 |
| operations | array | ✗ | 处理操作列表 |

**支持的操作**:
- `segment`: 中文分词
- `clean`: 文本清理（移除 HTML、URL、@提及）
- `entities`: 命名实体识别

**请求示例**:
```json
{
  "text": "张三在北京的阿里巴巴公司工作",
  "operations": ["segment", "clean", "entities"]
}
```

**响应**:
```json
{
  "status": "success",
  "result": {
    "original": "张三在北京的阿里巴巴公司工作",
    "cleaned": "张三在北京的阿里巴巴公司工作",
    "segments": ["张三", "在", "北京", "的", "阿里巴巴", "公司", "工作"],
    "segments_without_stopwords": ["张三", "北京", "阿里巴巴", "公司", "工作"],
    "entities": {
      "person": ["张三"],
      "location": ["北京"],
      "organization": ["阿里巴巴"],
      "time": [],
      "number": []
    }
  }
}
```

---

## 数据分析接口

### 综合分析

**POST /api/analyze**

对数据集进行综合分析。

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| data | array | ✓ | 数据列表，每项包含 content 字段 |

**请求示例**:
```json
{
  "data": [
    {"content": "这个产品真的很棒", "author": "用户A", "likes": 100},
    {"content": "太差了，非常失望", "author": "用户B", "likes": 50}
  ]
}
```

**响应**:
```json
{
  "status": "success",
  "analysis": {
    "sentiment": {
      "analysis_type": "sentiment",
      "data": {
        "statistics": {
          "positive_count": 1,
          "negative_count": 1,
          "neutral_count": 0,
          "average_score": 0.0
        }
      }
    },
    "trend": {...},
    "risk": {...},
    "relationship": {...},
    "summary": {
      "total_items": 2,
      "analysis_time": "2024-01-01T12:00:00"
    }
  }
}
```

---

### 批量情感分析

**POST /api/analyze/sentiment**

对多条文本进行情感分析统计。

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| texts | array | ✓ | 文本列表 |

**响应**:
```json
{
  "status": "success",
  "result": {
    "analysis_type": "sentiment",
    "data": {
      "statistics": {
        "positive_count": 10,
        "negative_count": 3,
        "neutral_count": 7,
        "average_score": 0.25,
        "distribution": {
          "positive_ratio": 0.5,
          "negative_ratio": 0.15,
          "neutral_ratio": 0.35
        }
      },
      "samples": [...]
    }
  }
}
```

---

### 趋势分析

**POST /api/analyze/trend**

分析数据的时间趋势。

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| data | array | ✓ | 数据列表，需包含时间字段 |
| time_field | string | ✗ | 时间字段名，默认 publish_time |
| interval | string | ✗ | 时间间隔：hour/day/week，默认 day |

**响应**:
```json
{
  "status": "success",
  "result": {
    "analysis_type": "trend",
    "data": {
      "time_series": [
        {"time": "2024-01-01", "count": 10, "likes": 500, "engagement": 1200},
        {"time": "2024-01-02", "count": 15, "likes": 800, "engagement": 1800}
      ],
      "growth_rate": 0.5,
      "peak_time": "2024-01-02",
      "peak_count": 15
    }
  }
}
```

---

### 风险评估

**POST /api/analyze/risk**

评估数据中的风险因素。

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| data | array | ✓ | 数据列表 |
| context | object | ✗ | 上下文信息（行业、主体等） |

**响应**:
```json
{
  "status": "success",
  "result": {
    "analysis_type": "risk_assessment",
    "data": {
      "risk_level": "medium",
      "risk_score": 45,
      "risk_factors": [
        "发现中等风险关键词: 投诉, 维权",
        "负面情绪占比: 35%"
      ],
      "recommendations": [
        "建议持续关注舆情发展",
        "定期进行风险评估"
      ]
    }
  }
}
```

**风险等级**:
- `low`: 低风险 (score < 30)
- `medium`: 中等风险 (score 30-50)
- `high`: 高风险 (score 50-70)
- `critical`: 严重风险 (score >= 70)

---

## 报告接口

### 生成系统报告

**GET /api/report**

生成系统状态和功能报告。

**响应**:
```json
{
  "status": "success",
  "report": {
    "report_time": "2024-01-01T12:00:00",
    "system_status": "healthy",
    "available_platforms": ["weibo", "zhihu", "baidu", "douyin"],
    "features": {
      "collection": ["微博", "知乎", "抖音", "百度"],
      "processing": ["中文分词", "情感分析", "关键词提取", "命名实体识别"],
      "analysis": ["情感统计", "关系网络", "趋势分析", "风险评估"]
    }
  }
}
```

---

## 错误处理

所有接口在出错时返回统一的错误格式：

```json
{
  "error": "错误消息",
  "status": "error"
}
```

**HTTP 状态码**:
- `400`: 请求参数错误
- `404`: 资源不存在
- `500`: 服务器内部错误

---

## 使用示例

### cURL

```bash
# 健康检查
curl http://localhost:5001/health

# 情感分析
curl -X POST http://localhost:5001/api/sentiment \
  -H "Content-Type: application/json" \
  -d '{"text": "这个产品真的很棒！"}'

# 数据采集
curl -X POST http://localhost:5001/api/collect \
  -H "Content-Type: application/json" \
  -d '{"platform": "baidu", "keyword": "人工智能", "limit": 10}'
```

### Python

```python
import requests

BASE_URL = "http://localhost:5001"

# 情感分析
response = requests.post(
    f"{BASE_URL}/api/sentiment",
    json={"text": "这个产品真的很棒！"}
)
result = response.json()
print(result['result']['sentiment'])  # positive

# 关键词提取
response = requests.post(
    f"{BASE_URL}/api/keywords",
    json={"text": "人工智能和机器学习正在改变世界", "top_k": 5}
)
keywords = response.json()['keywords']
for kw in keywords:
    print(f"{kw['keyword']}: {kw['weight']}")
```

### JavaScript

```javascript
// 情感分析
fetch('http://localhost:5001/api/sentiment', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({text: '这个产品真的很棒！'})
})
.then(res => res.json())
.then(data => console.log(data.result.sentiment));
```