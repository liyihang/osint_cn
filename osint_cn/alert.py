"""
风险预警系统
规则引擎、阈值监控、多渠道通知推送
"""

import logging
import re
import smtplib
import threading
import time
import json
import hashlib
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from enum import Enum
from typing import Dict, List, Optional, Callable, Any, Set, Pattern
from queue import Queue
import requests

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """预警级别"""
    INFO = 1        # 信息
    WARNING = 2     # 警告
    DANGER = 3      # 危险
    CRITICAL = 4    # 严重


class AlertStatus(Enum):
    """预警状态"""
    ACTIVE = "active"       # 活跃
    ACKNOWLEDGED = "acknowledged"  # 已确认
    RESOLVED = "resolved"   # 已解决
    EXPIRED = "expired"     # 已过期


class RuleType(Enum):
    """规则类型"""
    KEYWORD = "keyword"         # 关键词匹配
    REGEX = "regex"             # 正则匹配
    THRESHOLD = "threshold"     # 阈值触发
    SENTIMENT = "sentiment"     # 情感阈值
    FREQUENCY = "frequency"     # 频率监控
    COMPOSITE = "composite"     # 复合规则


@dataclass
class Alert:
    """预警"""
    alert_id: str
    rule_id: str
    level: AlertLevel
    title: str
    description: str
    source: str
    content: str
    matched_keywords: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: AlertStatus = AlertStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.now)
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            'alert_id': self.alert_id,
            'rule_id': self.rule_id,
            'level': self.level.name,
            'level_value': self.level.value,
            'title': self.title,
            'description': self.description,
            'source': self.source,
            'content': self.content[:500],
            'matched_keywords': self.matched_keywords,
            'metadata': self.metadata,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'acknowledged_by': self.acknowledged_by
        }


@dataclass
class AlertRule:
    """预警规则"""
    rule_id: str
    name: str
    type: RuleType
    level: AlertLevel
    enabled: bool = True
    description: str = ""
    
    # 规则配置
    keywords: List[str] = field(default_factory=list)       # 关键词列表
    regex_pattern: Optional[str] = None                      # 正则表达式
    threshold_field: Optional[str] = None                    # 阈值字段
    threshold_value: float = 0.0                             # 阈值
    threshold_operator: str = ">"                            # 比较操作符
    sentiment_threshold: float = -0.5                        # 情感阈值
    frequency_count: int = 10                                # 频率计数
    frequency_window_minutes: int = 60                       # 频率窗口（分钟）
    
    # 通知配置
    notify_channels: List[str] = field(default_factory=list)  # 通知渠道
    cooldown_minutes: int = 30                                 # 冷却时间
    
    # 统计
    trigger_count: int = 0
    last_triggered: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    # 编译后的正则
    _compiled_regex: Optional[Pattern] = None
    
    def __post_init__(self):
        if self.regex_pattern:
            try:
                self._compiled_regex = re.compile(self.regex_pattern, re.IGNORECASE)
            except:
                logger.error(f"无效的正则表达式: {self.regex_pattern}")
    
    def to_dict(self) -> Dict:
        return {
            'rule_id': self.rule_id,
            'name': self.name,
            'type': self.type.value,
            'level': self.level.name,
            'enabled': self.enabled,
            'description': self.description,
            'keywords': self.keywords,
            'regex_pattern': self.regex_pattern,
            'threshold_field': self.threshold_field,
            'threshold_value': self.threshold_value,
            'threshold_operator': self.threshold_operator,
            'sentiment_threshold': self.sentiment_threshold,
            'frequency_count': self.frequency_count,
            'frequency_window_minutes': self.frequency_window_minutes,
            'notify_channels': self.notify_channels,
            'cooldown_minutes': self.cooldown_minutes,
            'trigger_count': self.trigger_count,
            'last_triggered': self.last_triggered.isoformat() if self.last_triggered else None,
            'created_at': self.created_at.isoformat()
        }


class RuleEngine:
    """规则引擎"""
    
    def __init__(self):
        self.rules: Dict[str, AlertRule] = {}
        self.frequency_tracker: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._lock = threading.Lock()
    
    def add_rule(self, rule: AlertRule) -> str:
        """添加规则"""
        with self._lock:
            self.rules[rule.rule_id] = rule
        logger.info(f"添加预警规则: {rule.rule_id} - {rule.name}")
        return rule.rule_id
    
    def remove_rule(self, rule_id: str) -> bool:
        """删除规则"""
        with self._lock:
            if rule_id in self.rules:
                del self.rules[rule_id]
                return True
        return False
    
    def enable_rule(self, rule_id: str) -> bool:
        """启用规则"""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = True
            return True
        return False
    
    def disable_rule(self, rule_id: str) -> bool:
        """禁用规则"""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = False
            return True
        return False
    
    def evaluate(
        self,
        content: str,
        source: str = "unknown",
        metadata: Optional[Dict] = None
    ) -> List[Alert]:
        """评估内容，返回触发的预警"""
        metadata = metadata or {}
        alerts = []
        
        for rule_id, rule in self.rules.items():
            if not rule.enabled:
                continue
            
            # 检查冷却时间
            if rule.last_triggered:
                cooldown_end = rule.last_triggered + timedelta(minutes=rule.cooldown_minutes)
                if datetime.now() < cooldown_end:
                    continue
            
            alert = self._evaluate_rule(rule, content, source, metadata)
            if alert:
                alerts.append(alert)
                rule.trigger_count += 1
                rule.last_triggered = datetime.now()
        
        return alerts
    
    def _evaluate_rule(
        self,
        rule: AlertRule,
        content: str,
        source: str,
        metadata: Dict
    ) -> Optional[Alert]:
        """评估单条规则"""
        
        if rule.type == RuleType.KEYWORD:
            return self._evaluate_keyword_rule(rule, content, source, metadata)
        
        elif rule.type == RuleType.REGEX:
            return self._evaluate_regex_rule(rule, content, source, metadata)
        
        elif rule.type == RuleType.THRESHOLD:
            return self._evaluate_threshold_rule(rule, content, source, metadata)
        
        elif rule.type == RuleType.SENTIMENT:
            return self._evaluate_sentiment_rule(rule, content, source, metadata)
        
        elif rule.type == RuleType.FREQUENCY:
            return self._evaluate_frequency_rule(rule, content, source, metadata)
        
        return None
    
    def _evaluate_keyword_rule(
        self,
        rule: AlertRule,
        content: str,
        source: str,
        metadata: Dict
    ) -> Optional[Alert]:
        """评估关键词规则"""
        matched = []
        content_lower = content.lower()
        
        for keyword in rule.keywords:
            if keyword.lower() in content_lower:
                matched.append(keyword)
        
        if matched:
            return self._create_alert(
                rule=rule,
                content=content,
                source=source,
                matched_keywords=matched,
                metadata=metadata,
                description=f"内容包含敏感关键词: {', '.join(matched)}"
            )
        
        return None
    
    def _evaluate_regex_rule(
        self,
        rule: AlertRule,
        content: str,
        source: str,
        metadata: Dict
    ) -> Optional[Alert]:
        """评估正则规则"""
        if not rule._compiled_regex:
            return None
        
        matches = rule._compiled_regex.findall(content)
        
        if matches:
            return self._create_alert(
                rule=rule,
                content=content,
                source=source,
                matched_keywords=matches[:10],
                metadata=metadata,
                description=f"内容匹配模式: {rule.regex_pattern}"
            )
        
        return None
    
    def _evaluate_threshold_rule(
        self,
        rule: AlertRule,
        content: str,
        source: str,
        metadata: Dict
    ) -> Optional[Alert]:
        """评估阈值规则"""
        if not rule.threshold_field or rule.threshold_field not in metadata:
            return None
        
        value = metadata[rule.threshold_field]
        
        try:
            value = float(value)
        except:
            return None
        
        triggered = False
        if rule.threshold_operator == ">":
            triggered = value > rule.threshold_value
        elif rule.threshold_operator == ">=":
            triggered = value >= rule.threshold_value
        elif rule.threshold_operator == "<":
            triggered = value < rule.threshold_value
        elif rule.threshold_operator == "<=":
            triggered = value <= rule.threshold_value
        elif rule.threshold_operator == "==":
            triggered = value == rule.threshold_value
        
        if triggered:
            return self._create_alert(
                rule=rule,
                content=content,
                source=source,
                metadata=metadata,
                description=f"{rule.threshold_field} = {value} {rule.threshold_operator} {rule.threshold_value}"
            )
        
        return None
    
    def _evaluate_sentiment_rule(
        self,
        rule: AlertRule,
        content: str,
        source: str,
        metadata: Dict
    ) -> Optional[Alert]:
        """评估情感规则"""
        sentiment_score = metadata.get('sentiment_score')
        
        if sentiment_score is None:
            # 如果没有情感分数，进行分析
            from osint_cn.opinion import SentimentAnalyzer
            analyzer = SentimentAnalyzer()
            result = analyzer.analyze(content)
            sentiment_score = result.score
        
        if sentiment_score <= rule.sentiment_threshold:
            return self._create_alert(
                rule=rule,
                content=content,
                source=source,
                metadata={**metadata, 'sentiment_score': sentiment_score},
                description=f"情感分数 {sentiment_score:.2f} 低于阈值 {rule.sentiment_threshold}"
            )
        
        return None
    
    def _evaluate_frequency_rule(
        self,
        rule: AlertRule,
        content: str,
        source: str,
        metadata: Dict
    ) -> Optional[Alert]:
        """评估频率规则"""
        tracker_key = f"{rule.rule_id}:{source}"
        now = datetime.now()
        window_start = now - timedelta(minutes=rule.frequency_window_minutes)
        
        # 添加当前事件
        self.frequency_tracker[tracker_key].append(now)
        
        # 统计窗口内事件数
        count = sum(1 for t in self.frequency_tracker[tracker_key] if t >= window_start)
        
        if count >= rule.frequency_count:
            return self._create_alert(
                rule=rule,
                content=content,
                source=source,
                metadata={**metadata, 'frequency_count': count},
                description=f"在 {rule.frequency_window_minutes} 分钟内出现 {count} 次，超过阈值 {rule.frequency_count}"
            )
        
        return None
    
    def _create_alert(
        self,
        rule: AlertRule,
        content: str,
        source: str,
        metadata: Dict,
        description: str,
        matched_keywords: List[str] = None
    ) -> Alert:
        """创建预警"""
        alert_id = f"alert_{rule.rule_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hashlib.md5(content[:50].encode()).hexdigest()[:6]}"
        
        return Alert(
            alert_id=alert_id,
            rule_id=rule.rule_id,
            level=rule.level,
            title=f"[{rule.level.name}] {rule.name}",
            description=description,
            source=source,
            content=content,
            matched_keywords=matched_keywords or [],
            metadata=metadata
        )
    
    def get_rule(self, rule_id: str) -> Optional[Dict]:
        """获取规则"""
        if rule_id in self.rules:
            return self.rules[rule_id].to_dict()
        return None
    
    def list_rules(self) -> List[Dict]:
        """列出所有规则"""
        return [rule.to_dict() for rule in self.rules.values()]
    
    def get_stats(self) -> Dict:
        """获取统计"""
        enabled_count = sum(1 for r in self.rules.values() if r.enabled)
        total_triggers = sum(r.trigger_count for r in self.rules.values())
        
        by_level = defaultdict(int)
        for rule in self.rules.values():
            by_level[rule.level.name] += 1
        
        return {
            'total_rules': len(self.rules),
            'enabled_rules': enabled_count,
            'total_triggers': total_triggers,
            'rules_by_level': dict(by_level)
        }


class NotificationChannel(ABC):
    """通知渠道基类"""
    
    @abstractmethod
    def send(self, alert: Alert) -> bool:
        """发送通知"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """获取渠道名称"""
        pass


class EmailNotificationChannel(NotificationChannel):
    """邮件通知渠道"""
    
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_addr: str,
        to_addrs: List[str],
        use_ssl: bool = True
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_addr = from_addr
        self.to_addrs = to_addrs
        self.use_ssl = use_ssl
    
    def get_name(self) -> str:
        return "email"
    
    def send(self, alert: Alert) -> bool:
        """发送邮件通知"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = alert.title
            msg['From'] = self.from_addr
            msg['To'] = ', '.join(self.to_addrs)
            
            # 纯文本内容
            text_content = f"""
预警通知

级别: {alert.level.name}
规则: {alert.rule_id}
来源: {alert.source}
时间: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}

描述:
{alert.description}

内容:
{alert.content[:1000]}

匹配关键词: {', '.join(alert.matched_keywords)}
            """
            
            # HTML内容
            html_content = f"""
<html>
<body style="font-family: Arial, sans-serif;">
    <div style="background-color: {'#dc3545' if alert.level.value >= 3 else '#ffc107'}; color: white; padding: 15px;">
        <h2>{alert.title}</h2>
    </div>
    <div style="padding: 20px;">
        <p><strong>级别:</strong> {alert.level.name}</p>
        <p><strong>规则:</strong> {alert.rule_id}</p>
        <p><strong>来源:</strong> {alert.source}</p>
        <p><strong>时间:</strong> {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
        <hr>
        <p><strong>描述:</strong></p>
        <p>{alert.description}</p>
        <hr>
        <p><strong>内容:</strong></p>
        <p style="background-color: #f5f5f5; padding: 10px; border-radius: 5px;">
            {alert.content[:1000]}
        </p>
        <p><strong>匹配关键词:</strong> {', '.join(alert.matched_keywords)}</p>
    </div>
</body>
</html>
            """
            
            msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))
            
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                server.starttls()
            
            server.login(self.username, self.password)
            server.sendmail(self.from_addr, self.to_addrs, msg.as_string())
            server.quit()
            
            logger.info(f"邮件通知发送成功: {alert.alert_id}")
            return True
            
        except Exception as e:
            logger.error(f"邮件通知发送失败: {e}")
            return False


class WebhookNotificationChannel(NotificationChannel):
    """Webhook通知渠道"""
    
    def __init__(
        self,
        webhook_url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 10
    ):
        self.webhook_url = webhook_url
        self.headers = headers or {'Content-Type': 'application/json'}
        self.timeout = timeout
    
    def get_name(self) -> str:
        return "webhook"
    
    def send(self, alert: Alert) -> bool:
        """发送Webhook通知"""
        try:
            payload = alert.to_dict()
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers=self.headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                logger.info(f"Webhook通知发送成功: {alert.alert_id}")
                return True
            else:
                logger.error(f"Webhook通知失败: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Webhook通知发送失败: {e}")
            return False


class DingTalkNotificationChannel(NotificationChannel):
    """钉钉通知渠道"""
    
    def __init__(self, webhook_url: str, secret: Optional[str] = None):
        self.webhook_url = webhook_url
        self.secret = secret
    
    def get_name(self) -> str:
        return "dingtalk"
    
    def _get_sign_url(self) -> str:
        """获取签名URL"""
        if not self.secret:
            return self.webhook_url
        
        import hmac
        import base64
        import urllib.parse
        
        timestamp = str(round(time.time() * 1000))
        secret_enc = self.secret.encode('utf-8')
        string_to_sign = f'{timestamp}\n{self.secret}'
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod='sha256').digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        
        return f"{self.webhook_url}&timestamp={timestamp}&sign={sign}"
    
    def send(self, alert: Alert) -> bool:
        """发送钉钉通知"""
        try:
            level_emoji = {
                AlertLevel.INFO: "ℹ️",
                AlertLevel.WARNING: "⚠️",
                AlertLevel.DANGER: "🚨",
                AlertLevel.CRITICAL: "🔴"
            }
            
            emoji = level_emoji.get(alert.level, "📢")
            
            message = {
                "msgtype": "markdown",
                "markdown": {
                    "title": alert.title,
                    "text": f"""### {emoji} {alert.title}

**级别:** {alert.level.name}

**来源:** {alert.source}

**时间:** {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}

---

**描述:**
> {alert.description}

**内容预览:**
> {alert.content[:500]}

**关键词:** {', '.join(alert.matched_keywords) if alert.matched_keywords else '无'}
"""
                }
            }
            
            url = self._get_sign_url()
            response = requests.post(
                url,
                json=message,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            result = response.json()
            if result.get('errcode') == 0:
                logger.info(f"钉钉通知发送成功: {alert.alert_id}")
                return True
            else:
                logger.error(f"钉钉通知失败: {result}")
                return False
                
        except Exception as e:
            logger.error(f"钉钉通知发送失败: {e}")
            return False


class WeChatWorkNotificationChannel(NotificationChannel):
    """企业微信通知渠道"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    def get_name(self) -> str:
        return "wechat_work"
    
    def send(self, alert: Alert) -> bool:
        """发送企业微信通知"""
        try:
            message = {
                "msgtype": "markdown",
                "markdown": {
                    "content": f"""## <font color="{'warning' if alert.level.value < 3 else 'warning'}">{alert.title}</font>
> **级别:** {alert.level.name}
> **来源:** {alert.source}
> **时间:** {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}

**描述:** {alert.description}

**内容:** {alert.content[:300]}...

**关键词:** {', '.join(alert.matched_keywords[:5]) if alert.matched_keywords else '无'}"""
                }
            }
            
            response = requests.post(
                self.webhook_url,
                json=message,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            result = response.json()
            if result.get('errcode') == 0:
                logger.info(f"企业微信通知发送成功: {alert.alert_id}")
                return True
            else:
                logger.error(f"企业微信通知失败: {result}")
                return False
                
        except Exception as e:
            logger.error(f"企业微信通知发送失败: {e}")
            return False


class AlertManager:
    """预警管理器"""
    
    def __init__(self):
        self.rule_engine = RuleEngine()
        self.channels: Dict[str, NotificationChannel] = {}
        self.alerts: Dict[str, Alert] = {}
        self.alert_history: deque = deque(maxlen=10000)
        
        self.running = False
        self._alert_queue: Queue = Queue()
        self._processor_thread: Optional[threading.Thread] = None
        
        # 初始化默认规则
        self._init_default_rules()
    
    def _init_default_rules(self):
        """初始化默认规则"""
        # 敏感词规则
        sensitive_rule = AlertRule(
            rule_id="default_sensitive",
            name="敏感词监控",
            type=RuleType.KEYWORD,
            level=AlertLevel.WARNING,
            keywords=['爆料', '内幕', '曝光', '丑闻', '造假', '欺骗', '诈骗', '投诉'],
            description="监控敏感关键词"
        )
        self.rule_engine.add_rule(sensitive_rule)
        
        # 负面情感规则
        sentiment_rule = AlertRule(
            rule_id="default_negative_sentiment",
            name="负面情感预警",
            type=RuleType.SENTIMENT,
            level=AlertLevel.WARNING,
            sentiment_threshold=-0.6,
            description="监控高度负面情感内容"
        )
        self.rule_engine.add_rule(sentiment_rule)
        
        # 高频规则
        frequency_rule = AlertRule(
            rule_id="default_frequency",
            name="异常频率预警",
            type=RuleType.FREQUENCY,
            level=AlertLevel.DANGER,
            frequency_count=50,
            frequency_window_minutes=10,
            description="监控短时间内的异常高频内容"
        )
        self.rule_engine.add_rule(frequency_rule)
    
    def add_channel(self, channel: NotificationChannel):
        """添加通知渠道"""
        self.channels[channel.get_name()] = channel
        logger.info(f"添加通知渠道: {channel.get_name()}")
    
    def remove_channel(self, channel_name: str) -> bool:
        """移除通知渠道"""
        if channel_name in self.channels:
            del self.channels[channel_name]
            return True
        return False
    
    def start(self):
        """启动预警系统"""
        if self.running:
            return
        
        self.running = True
        self._processor_thread = threading.Thread(target=self._process_alerts, daemon=True)
        self._processor_thread.start()
        logger.info("预警系统已启动")
    
    def stop(self):
        """停止预警系统"""
        self.running = False
        if self._processor_thread:
            self._processor_thread.join(timeout=5)
        logger.info("预警系统已停止")
    
    def _process_alerts(self):
        """处理预警队列"""
        while self.running:
            try:
                alert = self._alert_queue.get(timeout=1)
                self._send_notifications(alert)
            except:
                continue
    
    def _send_notifications(self, alert: Alert):
        """发送通知"""
        # 获取规则的通知渠道
        rule = self.rule_engine.rules.get(alert.rule_id)
        channels_to_notify = rule.notify_channels if rule else list(self.channels.keys())
        
        # 如果没有指定渠道，使用所有可用渠道
        if not channels_to_notify:
            channels_to_notify = list(self.channels.keys())
        
        for channel_name in channels_to_notify:
            if channel_name in self.channels:
                try:
                    self.channels[channel_name].send(alert)
                except Exception as e:
                    logger.error(f"通知发送失败 [{channel_name}]: {e}")
    
    def process_content(
        self,
        content: str,
        source: str = "unknown",
        metadata: Optional[Dict] = None
    ) -> List[Alert]:
        """处理内容并生成预警"""
        alerts = self.rule_engine.evaluate(content, source, metadata)
        
        for alert in alerts:
            self.alerts[alert.alert_id] = alert
            self.alert_history.append(alert)
            
            # 放入通知队列
            self._alert_queue.put(alert)
        
        return alerts
    
    def acknowledge_alert(self, alert_id: str, user: str = "system") -> bool:
        """确认预警"""
        if alert_id in self.alerts:
            alert = self.alerts[alert_id]
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_at = datetime.now()
            alert.acknowledged_by = user
            return True
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """解决预警"""
        if alert_id in self.alerts:
            alert = self.alerts[alert_id]
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.now()
            return True
        return False
    
    def get_active_alerts(self, level: Optional[AlertLevel] = None) -> List[Dict]:
        """获取活跃预警"""
        alerts = [
            a for a in self.alerts.values()
            if a.status == AlertStatus.ACTIVE
        ]
        
        if level:
            alerts = [a for a in alerts if a.level == level]
        
        return sorted(
            [a.to_dict() for a in alerts],
            key=lambda x: x['created_at'],
            reverse=True
        )
    
    def get_alert_history(
        self,
        limit: int = 100,
        level: Optional[AlertLevel] = None
    ) -> List[Dict]:
        """获取预警历史"""
        alerts = list(self.alert_history)
        
        if level:
            alerts = [a for a in alerts if a.level == level]
        
        return sorted(
            [a.to_dict() for a in alerts[-limit:]],
            key=lambda x: x['created_at'],
            reverse=True
        )
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        status_counts = defaultdict(int)
        level_counts = defaultdict(int)
        
        for alert in self.alerts.values():
            status_counts[alert.status.value] += 1
            level_counts[alert.level.name] += 1
        
        return {
            'total_alerts': len(self.alerts),
            'active_alerts': status_counts.get('active', 0),
            'acknowledged_alerts': status_counts.get('acknowledged', 0),
            'resolved_alerts': status_counts.get('resolved', 0),
            'by_level': dict(level_counts),
            'rule_stats': self.rule_engine.get_stats(),
            'channels': list(self.channels.keys())
        }
    
    def create_custom_rule(
        self,
        name: str,
        rule_type: str,
        level: str,
        config: Dict
    ) -> str:
        """创建自定义规则"""
        rule_id = f"custom_{hashlib.md5(name.encode()).hexdigest()[:8]}"
        
        rule = AlertRule(
            rule_id=rule_id,
            name=name,
            type=RuleType(rule_type),
            level=AlertLevel[level.upper()],
            **config
        )
        
        return self.rule_engine.add_rule(rule)


# 全局实例
_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """获取预警管理器实例"""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager
