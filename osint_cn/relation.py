"""
信息关系挖掘模块
实体识别、关系图谱构建、社交网络分析
"""

import logging
import re
import hashlib
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any
import math

import jieba
import jieba.posseg as pseg

logger = logging.getLogger(__name__)


class EntityType(Enum):
    """实体类型"""
    PERSON = "person"           # 人物
    ORGANIZATION = "organization"  # 组织机构
    LOCATION = "location"       # 地点
    EVENT = "event"             # 事件
    PRODUCT = "product"         # 产品
    BRAND = "brand"             # 品牌
    TIME = "time"               # 时间
    MONEY = "money"             # 金额
    URL = "url"                 # 链接
    HASHTAG = "hashtag"         # 话题标签
    MENTION = "mention"         # @提及


class RelationType(Enum):
    """关系类型"""
    MENTION = "mention"         # 提及
    REPLY = "reply"             # 回复
    REPOST = "repost"          # 转发
    FOLLOW = "follow"          # 关注
    COOCCURRENCE = "cooccurrence"  # 共现
    SIMILAR = "similar"        # 相似
    BELONG_TO = "belong_to"    # 属于
    LOCATED_IN = "located_in"  # 位于
    WORK_FOR = "work_for"      # 就职于
    PARTICIPATE = "participate"  # 参与


@dataclass
class Entity:
    """实体"""
    entity_id: str
    name: str
    type: EntityType
    aliases: Set[str] = field(default_factory=set)
    attributes: Dict[str, Any] = field(default_factory=dict)
    mention_count: int = 0
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    sources: Set[str] = field(default_factory=set)
    
    def to_dict(self) -> Dict:
        return {
            'entity_id': self.entity_id,
            'name': self.name,
            'type': self.type.value,
            'aliases': list(self.aliases),
            'attributes': self.attributes,
            'mention_count': self.mention_count,
            'first_seen': self.first_seen.isoformat(),
            'last_seen': self.last_seen.isoformat(),
            'sources': list(self.sources)
        }
    
    def merge(self, other: 'Entity'):
        """合并实体"""
        self.aliases.update(other.aliases)
        self.aliases.add(other.name)
        self.attributes.update(other.attributes)
        self.mention_count += other.mention_count
        self.first_seen = min(self.first_seen, other.first_seen)
        self.last_seen = max(self.last_seen, other.last_seen)
        self.sources.update(other.sources)


@dataclass
class Relation:
    """关系"""
    relation_id: str
    source_id: str
    target_id: str
    type: RelationType
    weight: float = 1.0
    attributes: Dict[str, Any] = field(default_factory=dict)
    evidence: List[str] = field(default_factory=list)  # 关系证据（原文片段）
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            'relation_id': self.relation_id,
            'source_id': self.source_id,
            'target_id': self.target_id,
            'type': self.type.value,
            'weight': round(self.weight, 4),
            'attributes': self.attributes,
            'evidence': self.evidence[:5],
            'created_at': self.created_at.isoformat()
        }


@dataclass
class SocialNode:
    """社交网络节点"""
    user_id: str
    username: str
    platform: str
    followers_count: int = 0
    following_count: int = 0
    posts_count: int = 0
    influence_score: float = 0.0
    community_id: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            'user_id': self.user_id,
            'username': self.username,
            'platform': self.platform,
            'followers_count': self.followers_count,
            'following_count': self.following_count,
            'posts_count': self.posts_count,
            'influence_score': round(self.influence_score, 4),
            'community_id': self.community_id,
            'attributes': self.attributes
        }


class EntityRecognizer:
    """实体识别器"""
    
    # 中文人名词性
    PERSON_POS = {'nr', 'nrt', 'nrfg'}
    # 机构词性
    ORG_POS = {'nt', 'nto', 'nts', 'nth'}
    # 地点词性
    LOC_POS = {'ns', 'nsf'}
    
    # 正则模式
    PATTERNS = {
        EntityType.URL: re.compile(
            r'https?://[^\s<>"{}|\\^`\[\]]+',
            re.IGNORECASE
        ),
        EntityType.HASHTAG: re.compile(r'#([^#\s]+)#?'),
        EntityType.MENTION: re.compile(r'@([^\s@:：,，。！!?？]+)'),
        EntityType.MONEY: re.compile(
            r'[¥$€£]?\s*\d+(?:[,，]\d{3})*(?:\.\d+)?\s*(?:万|亿|千|百|元|块|美元|人民币|RMB|USD)?'
        ),
        EntityType.TIME: re.compile(
            r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日号]?|\d{1,2}[月:：]\d{1,2}[日号时]?|\d+(?:点|时|分|秒)'
        )
    }
    
    # 常见组织后缀
    ORG_SUFFIXES = {
        '公司', '集团', '有限', '股份', '企业', '工厂', '银行', '医院',
        '大学', '学院', '中学', '小学', '学校', '研究院', '研究所',
        '政府', '部门', '局', '厅', '处', '委员会', '协会', '联盟'
    }
    
    # 常见品牌
    BRANDS = {
        '华为', '小米', '苹果', 'Apple', 'iPhone', '三星', 'Samsung',
        '腾讯', '阿里', '百度', '字节', '京东', '美团', '滴滴',
        '微信', '抖音', '微博', '淘宝', '支付宝', 'QQ'
    }
    
    def __init__(self):
        self.custom_entities: Dict[str, EntityType] = {}
        self.entity_cache: Dict[str, Entity] = {}
    
    def add_custom_entity(self, name: str, entity_type: EntityType):
        """添加自定义实体"""
        self.custom_entities[name] = entity_type
    
    def recognize(self, text: str, source: str = "unknown") -> List[Entity]:
        """识别文本中的实体"""
        entities = []
        found_names = set()
        
        # 1. 正则匹配
        for entity_type, pattern in self.PATTERNS.items():
            for match in pattern.finditer(text):
                name = match.group(1) if match.lastindex else match.group(0)
                name = name.strip()
                if name and name not in found_names:
                    entity = self._create_entity(name, entity_type, source)
                    entities.append(entity)
                    found_names.add(name)
        
        # 2. 自定义实体匹配
        for name, entity_type in self.custom_entities.items():
            if name in text and name not in found_names:
                entity = self._create_entity(name, entity_type, source)
                entities.append(entity)
                found_names.add(name)
        
        # 3. 品牌识别
        for brand in self.BRANDS:
            if brand in text and brand not in found_names:
                entity = self._create_entity(brand, EntityType.BRAND, source)
                entities.append(entity)
                found_names.add(brand)
        
        # 4. jieba词性标注识别
        words = pseg.cut(text)
        current_org = []
        
        for word, flag in words:
            word = word.strip()
            if not word:
                continue
            
            # 人名
            if flag in self.PERSON_POS and len(word) >= 2:
                if word not in found_names:
                    entity = self._create_entity(word, EntityType.PERSON, source)
                    entities.append(entity)
                    found_names.add(word)
            
            # 地点
            elif flag in self.LOC_POS and len(word) >= 2:
                if word not in found_names:
                    entity = self._create_entity(word, EntityType.LOCATION, source)
                    entities.append(entity)
                    found_names.add(word)
            
            # 机构（组合识别）
            elif flag in self.ORG_POS or any(word.endswith(s) for s in self.ORG_SUFFIXES):
                if word not in found_names:
                    entity = self._create_entity(word, EntityType.ORGANIZATION, source)
                    entities.append(entity)
                    found_names.add(word)
        
        return entities
    
    def _create_entity(self, name: str, entity_type: EntityType, source: str) -> Entity:
        """创建或更新实体"""
        entity_id = f"{entity_type.value}_{hashlib.md5(name.encode()).hexdigest()[:8]}"
        
        if entity_id in self.entity_cache:
            entity = self.entity_cache[entity_id]
            entity.mention_count += 1
            entity.last_seen = datetime.now()
            entity.sources.add(source)
        else:
            entity = Entity(
                entity_id=entity_id,
                name=name,
                type=entity_type,
                mention_count=1,
                sources={source}
            )
            self.entity_cache[entity_id] = entity
        
        return entity
    
    def get_entity_stats(self) -> Dict:
        """获取实体统计"""
        type_counts = Counter(e.type.value for e in self.entity_cache.values())
        top_entities = sorted(
            self.entity_cache.values(),
            key=lambda x: x.mention_count,
            reverse=True
        )[:20]
        
        return {
            'total_entities': len(self.entity_cache),
            'by_type': dict(type_counts),
            'top_entities': [e.to_dict() for e in top_entities]
        }


class RelationExtractor:
    """关系抽取器"""
    
    def __init__(self, entity_recognizer: EntityRecognizer):
        self.recognizer = entity_recognizer
        self.relations: Dict[str, Relation] = {}
    
    def extract_cooccurrence(
        self,
        text: str,
        window_size: int = 50,
        source: str = "unknown"
    ) -> List[Relation]:
        """提取共现关系"""
        entities = self.recognizer.recognize(text, source)
        relations = []
        
        # 基于位置的共现分析
        entity_positions = []
        for entity in entities:
            pos = text.find(entity.name)
            if pos >= 0:
                entity_positions.append((pos, entity))
        
        # 排序
        entity_positions.sort(key=lambda x: x[0])
        
        # 窗口内共现
        for i, (pos1, entity1) in enumerate(entity_positions):
            for j, (pos2, entity2) in enumerate(entity_positions[i+1:], i+1):
                if pos2 - pos1 <= window_size:
                    # 计算权重（距离越近权重越高）
                    distance = pos2 - pos1
                    weight = 1.0 - (distance / window_size)
                    
                    relation = self._create_relation(
                        entity1, entity2,
                        RelationType.COOCCURRENCE,
                        weight,
                        text[pos1:pos2 + len(entity2.name)]
                    )
                    relations.append(relation)
        
        return relations
    
    def extract_mention_relation(
        self,
        author: str,
        text: str,
        source: str = "unknown"
    ) -> List[Relation]:
        """提取@提及关系"""
        relations = []
        
        # 创建作者实体
        author_entity = self.recognizer._create_entity(author, EntityType.PERSON, source)
        
        # 找出所有@提及
        mentions = re.findall(r'@([^\s@:：,，。！!?？]+)', text)
        
        for mention in mentions:
            mention = mention.strip()
            if mention and mention != author:
                mentioned_entity = self.recognizer._create_entity(
                    mention, EntityType.PERSON, source
                )
                
                relation = self._create_relation(
                    author_entity, mentioned_entity,
                    RelationType.MENTION,
                    1.0,
                    text
                )
                relations.append(relation)
        
        return relations
    
    def extract_reply_relation(
        self,
        author: str,
        reply_to: str,
        text: str,
        source: str = "unknown"
    ) -> Relation:
        """提取回复关系"""
        author_entity = self.recognizer._create_entity(author, EntityType.PERSON, source)
        target_entity = self.recognizer._create_entity(reply_to, EntityType.PERSON, source)
        
        return self._create_relation(
            author_entity, target_entity,
            RelationType.REPLY,
            1.0,
            text
        )
    
    def _create_relation(
        self,
        source_entity: Entity,
        target_entity: Entity,
        rel_type: RelationType,
        weight: float,
        evidence: str
    ) -> Relation:
        """创建或更新关系"""
        relation_id = f"{source_entity.entity_id}_{rel_type.value}_{target_entity.entity_id}"
        
        if relation_id in self.relations:
            relation = self.relations[relation_id]
            relation.weight += weight
            if evidence and len(relation.evidence) < 10:
                relation.evidence.append(evidence[:200])
        else:
            relation = Relation(
                relation_id=relation_id,
                source_id=source_entity.entity_id,
                target_id=target_entity.entity_id,
                type=rel_type,
                weight=weight,
                evidence=[evidence[:200]] if evidence else []
            )
            self.relations[relation_id] = relation
        
        return relation
    
    def get_entity_relations(self, entity_id: str) -> List[Dict]:
        """获取实体的所有关系"""
        results = []
        for relation in self.relations.values():
            if relation.source_id == entity_id or relation.target_id == entity_id:
                results.append(relation.to_dict())
        return results
    
    def get_relation_stats(self) -> Dict:
        """获取关系统计"""
        type_counts = Counter(r.type.value for r in self.relations.values())
        
        return {
            'total_relations': len(self.relations),
            'by_type': dict(type_counts),
            'avg_weight': round(
                sum(r.weight for r in self.relations.values()) / max(len(self.relations), 1),
                4
            )
        }


class KnowledgeGraph:
    """知识图谱"""
    
    def __init__(self):
        self.entities: Dict[str, Entity] = {}
        self.relations: Dict[str, Relation] = {}
        self.entity_recognizer = EntityRecognizer()
        self.relation_extractor = RelationExtractor(self.entity_recognizer)
    
    def add_document(
        self,
        text: str,
        source: str = "unknown",
        author: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """添加文档到图谱"""
        # 实体识别
        entities = self.entity_recognizer.recognize(text, source)
        for entity in entities:
            self.entities[entity.entity_id] = entity
        
        # 关系抽取 - 共现
        cooccurrence_relations = self.relation_extractor.extract_cooccurrence(text, source=source)
        for relation in cooccurrence_relations:
            self.relations[relation.relation_id] = relation
        
        # 关系抽取 - 提及
        if author:
            mention_relations = self.relation_extractor.extract_mention_relation(author, text, source)
            for relation in mention_relations:
                self.relations[relation.relation_id] = relation
        
        return {
            'entities_found': len(entities),
            'relations_found': len(cooccurrence_relations),
            'entity_ids': [e.entity_id for e in entities]
        }
    
    def query_entity(self, name: str) -> Optional[Dict]:
        """查询实体"""
        for entity in self.entities.values():
            if entity.name == name or name in entity.aliases:
                relations = self.relation_extractor.get_entity_relations(entity.entity_id)
                return {
                    'entity': entity.to_dict(),
                    'relations': relations
                }
        return None
    
    def get_subgraph(
        self,
        entity_id: str,
        depth: int = 2,
        max_nodes: int = 100
    ) -> Dict:
        """获取子图"""
        if entity_id not in self.entities:
            return {'nodes': [], 'edges': []}
        
        visited_entities = set()
        visited_relations = set()
        queue = [(entity_id, 0)]
        
        nodes = []
        edges = []
        
        while queue and len(nodes) < max_nodes:
            current_id, current_depth = queue.pop(0)
            
            if current_id in visited_entities:
                continue
            
            visited_entities.add(current_id)
            
            if current_id in self.entities:
                entity = self.entities[current_id]
                nodes.append({
                    'id': entity.entity_id,
                    'label': entity.name,
                    'type': entity.type.value,
                    'size': min(entity.mention_count * 2, 50)
                })
            
            if current_depth < depth:
                # 查找相关关系
                for rel_id, relation in self.relations.items():
                    if rel_id in visited_relations:
                        continue
                    
                    next_id = None
                    if relation.source_id == current_id:
                        next_id = relation.target_id
                    elif relation.target_id == current_id:
                        next_id = relation.source_id
                    
                    if next_id and next_id not in visited_entities:
                        visited_relations.add(rel_id)
                        edges.append({
                            'source': relation.source_id,
                            'target': relation.target_id,
                            'type': relation.type.value,
                            'weight': relation.weight
                        })
                        queue.append((next_id, current_depth + 1))
        
        return {'nodes': nodes, 'edges': edges}
    
    def find_path(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5
    ) -> Optional[List[Dict]]:
        """查找两个实体之间的路径"""
        if source_id not in self.entities or target_id not in self.entities:
            return None
        
        # BFS查找路径
        queue = [(source_id, [source_id])]
        visited = {source_id}
        
        while queue:
            current_id, path = queue.pop(0)
            
            if len(path) > max_depth:
                continue
            
            if current_id == target_id:
                # 构建路径详情
                path_details = []
                for i, entity_id in enumerate(path):
                    if entity_id in self.entities:
                        path_details.append({
                            'step': i,
                            'entity': self.entities[entity_id].to_dict()
                        })
                return path_details
            
            # 扩展
            for relation in self.relations.values():
                next_id = None
                if relation.source_id == current_id:
                    next_id = relation.target_id
                elif relation.target_id == current_id:
                    next_id = relation.source_id
                
                if next_id and next_id not in visited:
                    visited.add(next_id)
                    queue.append((next_id, path + [next_id]))
        
        return None
    
    def get_stats(self) -> Dict:
        """获取图谱统计"""
        return {
            'total_entities': len(self.entities),
            'total_relations': len(self.relations),
            'entity_stats': self.entity_recognizer.get_entity_stats(),
            'relation_stats': self.relation_extractor.get_relation_stats()
        }
    
    def export_for_neo4j(self) -> Dict:
        """导出为Neo4j格式"""
        nodes = []
        relationships = []
        
        for entity in self.entities.values():
            nodes.append({
                'id': entity.entity_id,
                'labels': [entity.type.value.upper()],
                'properties': {
                    'name': entity.name,
                    'mention_count': entity.mention_count,
                    'aliases': list(entity.aliases)
                }
            })
        
        for relation in self.relations.values():
            relationships.append({
                'source': relation.source_id,
                'target': relation.target_id,
                'type': relation.type.value.upper(),
                'properties': {
                    'weight': relation.weight
                }
            })
        
        return {'nodes': nodes, 'relationships': relationships}


class SocialNetworkAnalyzer:
    """社交网络分析器"""
    
    def __init__(self):
        self.nodes: Dict[str, SocialNode] = {}
        self.edges: Dict[str, Dict[str, float]] = defaultdict(dict)  # source -> {target: weight}
    
    def add_user(
        self,
        user_id: str,
        username: str,
        platform: str,
        followers: int = 0,
        following: int = 0,
        posts: int = 0
    ) -> SocialNode:
        """添加用户节点"""
        if user_id not in self.nodes:
            self.nodes[user_id] = SocialNode(
                user_id=user_id,
                username=username,
                platform=platform,
                followers_count=followers,
                following_count=following,
                posts_count=posts
            )
        return self.nodes[user_id]
    
    def add_interaction(
        self,
        source_id: str,
        target_id: str,
        weight: float = 1.0
    ):
        """添加互动关系"""
        if source_id in self.nodes and target_id in self.nodes:
            if target_id in self.edges[source_id]:
                self.edges[source_id][target_id] += weight
            else:
                self.edges[source_id][target_id] = weight
    
    def calculate_pagerank(
        self,
        damping: float = 0.85,
        iterations: int = 100
    ) -> Dict[str, float]:
        """计算PageRank影响力"""
        n = len(self.nodes)
        if n == 0:
            return {}
        
        # 初始化
        ranks = {uid: 1.0 / n for uid in self.nodes}
        
        for _ in range(iterations):
            new_ranks = {}
            
            for uid in self.nodes:
                # 来自其他节点的贡献
                incoming_rank = 0.0
                for source_id, targets in self.edges.items():
                    if uid in targets:
                        out_degree = len(targets)
                        if out_degree > 0:
                            incoming_rank += ranks[source_id] / out_degree
                
                new_ranks[uid] = (1 - damping) / n + damping * incoming_rank
            
            ranks = new_ranks
        
        # 更新节点影响力分数
        for uid, rank in ranks.items():
            self.nodes[uid].influence_score = rank
        
        return ranks
    
    def detect_communities(self, min_community_size: int = 3) -> Dict[str, List[str]]:
        """社区检测（基于标签传播）"""
        # 初始化：每个节点是自己的社区
        labels = {uid: uid for uid in self.nodes}
        
        # 迭代传播
        for _ in range(50):
            changed = False
            
            for uid in self.nodes:
                # 获取邻居的标签
                neighbor_labels = []
                
                # 出边
                for target_id, weight in self.edges.get(uid, {}).items():
                    neighbor_labels.extend([labels[target_id]] * int(weight))
                
                # 入边
                for source_id, targets in self.edges.items():
                    if uid in targets:
                        weight = targets[uid]
                        neighbor_labels.extend([labels[source_id]] * int(weight))
                
                if neighbor_labels:
                    # 选择最常见的标签
                    most_common = Counter(neighbor_labels).most_common(1)[0][0]
                    if labels[uid] != most_common:
                        labels[uid] = most_common
                        changed = True
            
            if not changed:
                break
        
        # 整理社区
        communities = defaultdict(list)
        for uid, label in labels.items():
            communities[label].append(uid)
            self.nodes[uid].community_id = label
        
        # 过滤小社区
        return {
            cid: members for cid, members in communities.items()
            if len(members) >= min_community_size
        }
    
    def find_key_connectors(self, top_n: int = 10) -> List[Dict]:
        """找出关键连接者（中介中心性）"""
        betweenness = {uid: 0.0 for uid in self.nodes}
        
        # 简化的中介中心性计算
        for source in self.nodes:
            for target in self.nodes:
                if source == target:
                    continue
                
                # BFS找最短路径
                visited = {source}
                queue = [(source, [source])]
                paths = []
                
                while queue:
                    current, path = queue.pop(0)
                    
                    if current == target:
                        paths.append(path)
                        continue
                    
                    for next_id in self.edges.get(current, {}):
                        if next_id not in visited:
                            visited.add(next_id)
                            queue.append((next_id, path + [next_id]))
                
                # 更新中介分数
                if paths:
                    for path in paths:
                        for node in path[1:-1]:  # 排除起点和终点
                            betweenness[node] += 1.0 / len(paths)
        
        # 排序
        sorted_nodes = sorted(
            betweenness.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n]
        
        return [{
            'user_id': uid,
            'username': self.nodes[uid].username,
            'betweenness': round(score, 4),
            'influence_score': self.nodes[uid].influence_score
        } for uid, score in sorted_nodes if uid in self.nodes]
    
    def get_user_network(self, user_id: str, depth: int = 2) -> Dict:
        """获取用户的社交网络"""
        if user_id not in self.nodes:
            return {'nodes': [], 'edges': []}
        
        visited = set()
        queue = [(user_id, 0)]
        nodes = []
        edges = []
        
        while queue:
            current_id, current_depth = queue.pop(0)
            
            if current_id in visited or current_depth > depth:
                continue
            
            visited.add(current_id)
            
            if current_id in self.nodes:
                node = self.nodes[current_id]
                nodes.append(node.to_dict())
                
                # 添加边和下一层节点
                for target_id, weight in self.edges.get(current_id, {}).items():
                    edges.append({
                        'source': current_id,
                        'target': target_id,
                        'weight': weight
                    })
                    if target_id not in visited:
                        queue.append((target_id, current_depth + 1))
        
        return {'nodes': nodes, 'edges': edges}
    
    def get_stats(self) -> Dict:
        """获取网络统计"""
        if not self.nodes:
            return {'total_users': 0}
        
        total_edges = sum(len(targets) for targets in self.edges.values())
        platforms = Counter(n.platform for n in self.nodes.values())
        
        return {
            'total_users': len(self.nodes),
            'total_edges': total_edges,
            'avg_connections': round(total_edges / max(len(self.nodes), 1), 2),
            'platforms': dict(platforms),
            'communities': len(set(n.community_id for n in self.nodes.values() if n.community_id))
        }


# 全局实例
_knowledge_graph: Optional[KnowledgeGraph] = None
_social_network: Optional[SocialNetworkAnalyzer] = None


def get_knowledge_graph() -> KnowledgeGraph:
    """获取知识图谱实例"""
    global _knowledge_graph
    if _knowledge_graph is None:
        _knowledge_graph = KnowledgeGraph()
    return _knowledge_graph


def get_social_network() -> SocialNetworkAnalyzer:
    """获取社交网络分析器实例"""
    global _social_network
    if _social_network is None:
        _social_network = SocialNetworkAnalyzer()
    return _social_network
