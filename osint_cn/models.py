"""
Pydantic 数据模型

定义 API 请求和响应的数据结构，提供自动验证和序列化
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, field_validator, ConfigDict


# ============ 枚举类型 ============

class Platform(str, Enum):
    """支持的平台"""
    WEIBO = "weibo"
    ZHIHU = "zhihu"
    BAIDU = "baidu"
    DOUYIN = "douyin"
    KUAISHOU = "kuaishou"
    WECHAT = "wechat"
    XIAOHONGSHU = "xiaohongshu"
    BILIBILI = "bilibili"
    TIEBA = "tieba"
    TOUTIAO = "toutiao"


class SentimentType(str, Enum):
    """情感类型"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class RiskLevel(str, Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ============ 基础模型 ============

class BaseResponse(BaseModel):
    """基础响应模型"""
    success: bool = True
    message: str = "操作成功"
    timestamp: datetime = Field(default_factory=datetime.now)
    
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )


class PaginationParams(BaseModel):
    """分页参数"""
    page: int = Field(default=1, ge=1, description="页码，从1开始")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量，最大100")
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseResponse):
    """分页响应模型"""
    total: int = Field(description="总记录数")
    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页数量")
    total_pages: int = Field(description="总页数")
    
    @classmethod
    def create(cls, data: List[Any], total: int, page: int, page_size: int, **kwargs):
        """创建分页响应"""
        total_pages = (total + page_size - 1) // page_size
        return cls(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            **kwargs
        )


# ============ 文本处理相关 ============

class TextAnalysisRequest(BaseModel):
    """文本分析请求"""
    text: str = Field(..., min_length=1, max_length=50000, description="待分析文本")
    
    @field_validator('text')
    @classmethod
    def validate_text(cls, v: str) -> str:
        return v.strip()


class SentimentRequest(TextAnalysisRequest):
    """情感分析请求"""
    pass


class SentimentResult(BaseModel):
    """情感分析结果"""
    sentiment: SentimentType = Field(description="情感倾向")
    score: float = Field(ge=-1, le=1, description="情感分数，-1到1之间")
    confidence: float = Field(ge=0, le=1, description="置信度")
    positive_words: List[str] = Field(default_factory=list, description="积极词汇")
    negative_words: List[str] = Field(default_factory=list, description="消极词汇")


class SentimentResponse(BaseResponse):
    """情感分析响应"""
    data: SentimentResult


class KeywordRequest(TextAnalysisRequest):
    """关键词提取请求"""
    top_n: int = Field(default=10, ge=1, le=50, description="返回关键词数量")


class Keyword(BaseModel):
    """关键词"""
    word: str = Field(description="关键词")
    weight: float = Field(ge=0, le=1, description="权重")
    frequency: int = Field(ge=0, description="出现频次")


class KeywordResponse(BaseResponse):
    """关键词提取响应"""
    data: List[Keyword]


class SegmentRequest(TextAnalysisRequest):
    """分词请求"""
    mode: str = Field(default="accurate", pattern="^(accurate|all|search)$", description="分词模式")


class SegmentResponse(BaseResponse):
    """分词响应"""
    data: List[str] = Field(description="分词结果")


class EntityRequest(TextAnalysisRequest):
    """实体识别请求"""
    entity_types: Optional[List[str]] = Field(default=None, description="要识别的实体类型")


class Entity(BaseModel):
    """命名实体"""
    text: str = Field(description="实体文本")
    type: str = Field(description="实体类型")
    start: int = Field(ge=0, description="起始位置")
    end: int = Field(ge=0, description="结束位置")


class EntityResponse(BaseResponse):
    """实体识别响应"""
    data: List[Entity]


# ============ 数据采集相关 ============

class CollectRequest(BaseModel):
    """数据采集请求"""
    platform: Platform = Field(description="目标平台")
    keyword: str = Field(..., min_length=1, max_length=100, description="搜索关键词")
    max_items: int = Field(default=100, ge=1, le=1000, description="最大采集数量")
    
    @field_validator('keyword')
    @classmethod
    def validate_keyword(cls, v: str) -> str:
        return v.strip()


class CollectedItem(BaseModel):
    """采集到的数据项"""
    id: str = Field(description="数据ID")
    platform: Platform = Field(description="来源平台")
    content: str = Field(description="内容")
    author: str = Field(description="作者")
    publish_time: Optional[datetime] = Field(default=None, description="发布时间")
    url: Optional[str] = Field(default=None, description="原文链接")
    likes: int = Field(default=0, ge=0, description="点赞数")
    comments: int = Field(default=0, ge=0, description="评论数")
    shares: int = Field(default=0, ge=0, description="分享数")
    extra: Dict[str, Any] = Field(default_factory=dict, description="额外信息")


class CollectResponse(BaseResponse):
    """采集响应"""
    task_id: str = Field(description="任务ID")
    platform: Platform = Field(description="目标平台")
    keyword: str = Field(description="搜索关键词")
    items_collected: int = Field(ge=0, description="已采集数量")
    data: List[CollectedItem] = Field(default_factory=list, description="采集数据")


# ============ 分析相关 ============

class AnalyzeRequest(BaseModel):
    """综合分析请求"""
    data_ids: Optional[List[str]] = Field(default=None, description="要分析的数据ID列表")
    platform: Optional[Platform] = Field(default=None, description="过滤平台")
    keyword: Optional[str] = Field(default=None, description="过滤关键词")
    start_time: Optional[datetime] = Field(default=None, description="开始时间")
    end_time: Optional[datetime] = Field(default=None, description="结束时间")
    analysis_types: List[str] = Field(
        default=["sentiment", "keywords", "trend"],
        description="分析类型"
    )


class TrendPoint(BaseModel):
    """趋势数据点"""
    time: datetime = Field(description="时间点")
    value: float = Field(description="数值")
    label: Optional[str] = Field(default=None, description="标签")


class TrendAnalysis(BaseModel):
    """趋势分析结果"""
    trend_direction: str = Field(description="趋势方向: rising/falling/stable")
    growth_rate: float = Field(description="增长率")
    peak_time: Optional[datetime] = Field(default=None, description="峰值时间")
    data_points: List[TrendPoint] = Field(default_factory=list, description="数据点")


class RelationNode(BaseModel):
    """关系节点"""
    id: str = Field(description="节点ID")
    name: str = Field(description="节点名称")
    type: str = Field(description="节点类型")
    weight: float = Field(default=1.0, description="权重")


class RelationEdge(BaseModel):
    """关系边"""
    source: str = Field(description="源节点ID")
    target: str = Field(description="目标节点ID")
    relation: str = Field(description="关系类型")
    weight: float = Field(default=1.0, description="权重")


class RelationAnalysis(BaseModel):
    """关系分析结果"""
    nodes: List[RelationNode] = Field(default_factory=list, description="节点列表")
    edges: List[RelationEdge] = Field(default_factory=list, description="边列表")
    key_entities: List[str] = Field(default_factory=list, description="关键实体")


class RiskIndicator(BaseModel):
    """风险指标"""
    name: str = Field(description="指标名称")
    score: float = Field(ge=0, le=1, description="风险分数")
    description: str = Field(description="描述")
    evidence: List[str] = Field(default_factory=list, description="证据")


class RiskAnalysis(BaseModel):
    """风险分析结果"""
    overall_risk: RiskLevel = Field(description="总体风险等级")
    risk_score: float = Field(ge=0, le=1, description="风险分数")
    indicators: List[RiskIndicator] = Field(default_factory=list, description="风险指标")
    suggestions: List[str] = Field(default_factory=list, description="建议措施")


class AnalyzeResponse(BaseResponse):
    """综合分析响应"""
    sentiment: Optional[SentimentResult] = Field(default=None, description="情感分析")
    keywords: Optional[List[Keyword]] = Field(default=None, description="关键词")
    trend: Optional[TrendAnalysis] = Field(default=None, description="趋势分析")
    relations: Optional[RelationAnalysis] = Field(default=None, description="关系分析")
    risk: Optional[RiskAnalysis] = Field(default=None, description="风险分析")


# ============ 任务相关 ============

class TaskCreateRequest(BaseModel):
    """创建任务请求"""
    name: str = Field(..., min_length=1, max_length=100, description="任务名称")
    task_type: str = Field(..., description="任务类型")
    schedule: Optional[str] = Field(default=None, description="调度表达式(cron格式)")
    config: Dict[str, Any] = Field(default_factory=dict, description="任务配置")


class TaskInfo(BaseModel):
    """任务信息"""
    id: str = Field(description="任务ID")
    name: str = Field(description="任务名称")
    task_type: str = Field(description="任务类型")
    status: TaskStatus = Field(description="任务状态")
    schedule: Optional[str] = Field(default=None, description="调度表达式")
    created_at: datetime = Field(description="创建时间")
    started_at: Optional[datetime] = Field(default=None, description="开始时间")
    finished_at: Optional[datetime] = Field(default=None, description="完成时间")
    progress: float = Field(default=0, ge=0, le=100, description="进度百分比")
    result: Optional[Dict[str, Any]] = Field(default=None, description="执行结果")
    error: Optional[str] = Field(default=None, description="错误信息")


class TaskResponse(BaseResponse):
    """任务响应"""
    data: TaskInfo


class TaskListResponse(PaginatedResponse):
    """任务列表响应"""
    data: List[TaskInfo]


# ============ 健康检查 ============

class ServiceHealth(BaseModel):
    """服务健康状态"""
    name: str = Field(description="服务名称")
    status: str = Field(description="状态: healthy/unhealthy/unknown")
    latency_ms: Optional[float] = Field(default=None, description="延迟(毫秒)")
    message: Optional[str] = Field(default=None, description="详细信息")


class HealthResponse(BaseResponse):
    """健康检查响应"""
    status: str = Field(description="总体状态")
    version: str = Field(description="应用版本")
    uptime: float = Field(description="运行时间(秒)")
    services: List[ServiceHealth] = Field(default_factory=list, description="服务状态")


# ============ 错误响应 ============

class ErrorDetail(BaseModel):
    """错误详情"""
    field: Optional[str] = Field(default=None, description="字段名")
    message: str = Field(description="错误信息")
    code: Optional[str] = Field(default=None, description="错误代码")


class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = False
    error: str = Field(description="错误类型")
    message: str = Field(description="错误信息")
    details: List[ErrorDetail] = Field(default_factory=list, description="详细错误")
    timestamp: datetime = Field(default_factory=datetime.now)
    request_id: Optional[str] = Field(default=None, description="请求ID")
    
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )


# ============ 平台配置 ============

class PlatformInfo(BaseModel):
    """平台信息"""
    id: Platform = Field(description="平台ID")
    name: str = Field(description="平台名称")
    description: str = Field(description="平台描述")
    enabled: bool = Field(default=True, description="是否启用")
    requires_auth: bool = Field(default=False, description="是否需要认证")
    rate_limit: int = Field(default=60, description="每分钟请求限制")


class PlatformListResponse(BaseResponse):
    """平台列表响应"""
    data: List[PlatformInfo]


# ============ 报告相关 ============

class ReportRequest(BaseModel):
    """报告生成请求"""
    title: str = Field(..., min_length=1, max_length=200, description="报告标题")
    report_type: str = Field(default="comprehensive", description="报告类型")
    data_source: Dict[str, Any] = Field(description="数据来源配置")
    format: str = Field(default="json", pattern="^(json|html|pdf|markdown)$", description="输出格式")


class ReportInfo(BaseModel):
    """报告信息"""
    id: str = Field(description="报告ID")
    title: str = Field(description="报告标题")
    report_type: str = Field(description="报告类型")
    status: TaskStatus = Field(description="生成状态")
    created_at: datetime = Field(description="创建时间")
    file_path: Optional[str] = Field(default=None, description="文件路径")
    file_size: Optional[int] = Field(default=None, description="文件大小(字节)")


class ReportResponse(BaseResponse):
    """报告响应"""
    data: ReportInfo
