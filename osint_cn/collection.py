import requests
import json
import time
import random
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Generator
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class CollectedItem:
    """采集数据项"""
    platform: str
    content: str
    author: str = ""
    author_id: str = ""
    url: str = ""
    publish_time: Optional[datetime] = None
    likes: int = 0
    comments: int = 0
    shares: int = 0
    metadata: Dict = field(default_factory=dict)
    collected_at: datetime = field(default_factory=datetime.now)


class BaseCollector(ABC):
    """数据采集基类"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.rate_limit = self.config.get('rate_limit', 1.0)  # 请求间隔（秒）
        self.max_retries = self.config.get('max_retries', 3)
    
    @property
    @abstractmethod
    def platform_name(self) -> str:
        """平台名称"""
        pass
    
    @abstractmethod
    def collect(self, keyword: str, limit: int = 100) -> List[CollectedItem]:
        """采集数据"""
        pass
    
    @abstractmethod
    def collect_user_info(self, user_id: str) -> Dict:
        """采集用户信息"""
        pass
    
    def _request(self, url: str, method: str = 'GET', **kwargs) -> Optional[requests.Response]:
        """发送请求（带重试和限速）"""
        for attempt in range(self.max_retries):
            try:
                time.sleep(self.rate_limit + random.uniform(0, 0.5))
                response = self.session.request(method, url, timeout=30, **kwargs)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    logger.error(f"All retries failed for {url}")
                    return None
        return None
    
    def _parse_time(self, time_str: str) -> Optional[datetime]:
        """解析时间字符串"""
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%Y-%m-%d',
            '%Y/%m/%d %H:%M:%S',
        ]
        for fmt in formats:
            try:
                return datetime.strptime(time_str, fmt)
            except ValueError:
                continue
        return None


class WeiboCollector(BaseCollector):
    """微博数据采集器"""
    
    platform_name = "weibo"
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.base_url = "https://m.weibo.cn"
        self.cookie = self.config.get('cookie', '')
        if self.cookie:
            self.session.headers['Cookie'] = self.cookie
    
    def collect(self, keyword: str, limit: int = 100) -> List[CollectedItem]:
        """搜索采集微博"""
        items = []
        page = 1
        
        while len(items) < limit:
            url = f"{self.base_url}/api/container/getIndex"
            params = {
                'containerid': f'100103type=1&q={keyword}',
                'page_type': 'searchall',
                'page': page
            }
            
            response = self._request(url, params=params)
            if not response:
                break
            
            try:
                data = response.json()
                cards = data.get('data', {}).get('cards', [])
                
                if not cards:
                    break
                
                for card in cards:
                    if card.get('card_type') == 9:
                        mblog = card.get('mblog', {})
                        item = self._parse_mblog(mblog)
                        if item:
                            items.append(item)
                            if len(items) >= limit:
                                break
                
                page += 1
                
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Failed to parse weibo response: {e}")
                break
        
        logger.info(f"Collected {len(items)} items from Weibo for keyword: {keyword}")
        return items
    
    def _parse_mblog(self, mblog: Dict) -> Optional[CollectedItem]:
        """解析微博数据"""
        try:
            user = mblog.get('user', {})
            return CollectedItem(
                platform=self.platform_name,
                content=mblog.get('text', ''),
                author=user.get('screen_name', ''),
                author_id=str(user.get('id', '')),
                url=f"https://weibo.com/{user.get('id')}/{mblog.get('bid')}",
                publish_time=self._parse_time(mblog.get('created_at', '')),
                likes=mblog.get('attitudes_count', 0),
                comments=mblog.get('comments_count', 0),
                shares=mblog.get('reposts_count', 0),
                metadata={
                    'mid': mblog.get('mid'),
                    'source': mblog.get('source', ''),
                    'pics': [pic.get('url') for pic in mblog.get('pics', [])],
                    'is_retweet': 'retweeted_status' in mblog
                }
            )
        except Exception as e:
            logger.error(f"Failed to parse mblog: {e}")
            return None
    
    def collect_user_info(self, user_id: str) -> Dict:
        """采集用户信息"""
        url = f"{self.base_url}/api/container/getIndex"
        params = {'type': 'uid', 'value': user_id}
        
        response = self._request(url, params=params)
        if not response:
            return {}
        
        try:
            data = response.json()
            user_info = data.get('data', {}).get('userInfo', {})
            return {
                'id': user_info.get('id'),
                'name': user_info.get('screen_name'),
                'avatar': user_info.get('avatar_hd'),
                'description': user_info.get('description'),
                'followers': user_info.get('followers_count'),
                'following': user_info.get('follow_count'),
                'posts': user_info.get('statuses_count'),
                'verified': user_info.get('verified'),
                'verified_reason': user_info.get('verified_reason'),
            }
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            return {}
    
    def collect_user_posts(self, user_id: str, limit: int = 50) -> List[CollectedItem]:
        """采集用户发布的微博"""
        items = []
        page = 1
        
        while len(items) < limit:
            url = f"{self.base_url}/api/container/getIndex"
            params = {
                'type': 'uid',
                'value': user_id,
                'containerid': f'107603{user_id}',
                'page': page
            }
            
            response = self._request(url, params=params)
            if not response:
                break
            
            try:
                data = response.json()
                cards = data.get('data', {}).get('cards', [])
                
                if not cards:
                    break
                
                for card in cards:
                    if card.get('card_type') == 9:
                        item = self._parse_mblog(card.get('mblog', {}))
                        if item:
                            items.append(item)
                
                page += 1
                
            except Exception as e:
                logger.error(f"Failed to collect user posts: {e}")
                break
        
        return items[:limit]


class DouyinCollector(BaseCollector):
    """抖音数据采集器"""
    
    platform_name = "douyin"
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.base_url = "https://www.douyin.com"
        self.search_api = "https://www.douyin.com/aweme/v1/web/general/search"
        self.session.headers.update({
            'Referer': 'https://www.douyin.com/',
            'Accept': 'application/json, text/plain, */*'
        })
    
    def collect(self, keyword: str, limit: int = 100) -> List[CollectedItem]:
        """搜索采集抖音视频"""
        items = []
        offset = 0
        page_size = 20

        while len(items) < limit:
            params = {
                'keyword': keyword,
                'offset': offset,
                'count': min(page_size, max(1, limit - len(items))),
                'search_channel': 'aweme_general',
                'sort_type': 0,
                'publish_time': 0,
            }

            response = self._request(self.search_api, params=params)
            if not response:
                break

            try:
                payload = response.json()
                data_list = payload.get('data', [])
                if not data_list:
                    break

                appended = 0
                for entry in data_list:
                    aweme = entry.get('aweme_info') or entry.get('aweme') or {}
                    if not aweme:
                        continue
                    item = self._parse_aweme(aweme)
                    if item:
                        items.append(item)
                        appended += 1
                        if len(items) >= limit:
                            break

                if appended == 0:
                    break

                has_more = payload.get('has_more', 0)
                if not has_more:
                    break
                offset += page_size

            except Exception as e:
                logger.error(f"Failed to parse douyin response: {e}")
                break

        logger.info(f"Collected {len(items)} items from Douyin for keyword: {keyword}")
        return items[:limit]

    def _parse_aweme(self, aweme: Dict) -> Optional[CollectedItem]:
        try:
            author = aweme.get('author', {}) or {}
            stats = aweme.get('statistics', {}) or {}
            aweme_id = str(aweme.get('aweme_id', ''))
            return CollectedItem(
                platform=self.platform_name,
                content=aweme.get('desc', ''),
                author=author.get('nickname', ''),
                author_id=author.get('sec_uid', '') or str(author.get('uid', '')),
                url=f"https://www.douyin.com/video/{aweme_id}" if aweme_id else '',
                publish_time=datetime.fromtimestamp(aweme.get('create_time', 0)) if aweme.get('create_time') else None,
                likes=stats.get('digg_count', 0),
                comments=stats.get('comment_count', 0),
                shares=stats.get('share_count', 0),
                metadata={
                    'aweme_id': aweme_id,
                    'duration': aweme.get('duration', 0),
                    'author_unique_id': author.get('unique_id', ''),
                }
            )
        except Exception as e:
            logger.error(f"Failed to parse douyin aweme: {e}")
            return None
    
    def collect_user_info(self, user_id: str) -> Dict:
        """采集用户信息"""
        logger.info(f"Collecting Douyin user info for: {user_id}")
        return {
            'platform': self.platform_name,
            'user_id': user_id,
            'note': 'Requires API access or browser automation'
        }


class ZhihuCollector(BaseCollector):
    """知乎数据采集器"""
    
    platform_name = "zhihu"
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.base_url = "https://www.zhihu.com/api/v4"
        self.cookie = self.config.get('cookie', '')
        if self.cookie:
            self.session.headers['Cookie'] = self.cookie
    
    def collect(self, keyword: str, limit: int = 100) -> List[CollectedItem]:
        """搜索采集知乎内容"""
        items = []
        offset = 0
        
        while len(items) < limit:
            url = f"{self.base_url}/search_v3"
            params = {
                't': 'general',
                'q': keyword,
                'offset': offset,
                'limit': 20,
                'correction': 1,
                'search_source': 'Normal'
            }
            
            response = self._request(url, params=params)
            if not response:
                break
            
            try:
                data = response.json()
                results = data.get('data', [])
                
                if not results:
                    break
                
                for result in results:
                    item = self._parse_search_result(result)
                    if item:
                        items.append(item)
                
                offset += 20
                
                if data.get('paging', {}).get('is_end'):
                    break
                    
            except Exception as e:
                logger.error(f"Failed to parse zhihu response: {e}")
                break
        
        logger.info(f"Collected {len(items)} items from Zhihu for keyword: {keyword}")
        return items[:limit]
    
    def _parse_search_result(self, result: Dict) -> Optional[CollectedItem]:
        """解析知乎搜索结果"""
        try:
            obj = result.get('object', {})
            obj_type = result.get('type', '')
            
            author = obj.get('author', {})
            
            return CollectedItem(
                platform=self.platform_name,
                content=obj.get('content', obj.get('excerpt', '')),
                author=author.get('name', ''),
                author_id=author.get('url_token', ''),
                url=obj.get('url', ''),
                publish_time=None,
                likes=obj.get('voteup_count', 0),
                comments=obj.get('comment_count', 0),
                metadata={
                    'type': obj_type,
                    'title': obj.get('title', ''),
                    'question_id': obj.get('question', {}).get('id') if obj_type == 'answer' else None,
                }
            )
        except Exception as e:
            logger.error(f"Failed to parse zhihu result: {e}")
            return None
    
    def collect_user_info(self, user_id: str) -> Dict:
        """采集知乎用户信息"""
        url = f"{self.base_url}/members/{user_id}"
        params = {
            'include': 'follower_count,following_count,answer_count,articles_count,description'
        }
        
        response = self._request(url, params=params)
        if not response:
            return {}
        
        try:
            data = response.json()
            return {
                'id': data.get('id'),
                'name': data.get('name'),
                'url_token': data.get('url_token'),
                'headline': data.get('headline'),
                'description': data.get('description'),
                'followers': data.get('follower_count'),
                'following': data.get('following_count'),
                'answers': data.get('answer_count'),
                'articles': data.get('articles_count'),
            }
        except Exception as e:
            logger.error(f"Failed to get zhihu user info: {e}")
            return {}


class KuaishouCollector(BaseCollector):
    """快手数据采集器（基于 Web GraphQL）"""

    platform_name = "kuaishou"

    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.base_url = "https://www.kuaishou.com"
        self.graphql_url = "https://www.kuaishou.com/graphql"
        self.session.headers.update({
            'Referer': 'https://www.kuaishou.com/search/video',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })

    def collect(self, keyword: str, limit: int = 100) -> List[CollectedItem]:
        items = []
        pcursor = ""

        query = """
        query SearchFeed($keyword: String, $pcursor: String) {
          visionSearchPhoto(keyword: $keyword, pcursor: $pcursor, page: "search") {
            result {
              pcursor
              list {
                ... on VisionSearchPhoto {
                  photo {
                    photoId
                    caption
                    duration
                    likeCount
                    commentCount
                    viewCount
                    realLikeCount
                    uploadTime
                  }
                  author {
                    id
                    name
                  }
                }
              }
            }
          }
        }
        """

        while len(items) < limit:
            payload = {
                'operationName': 'SearchFeed',
                'variables': {
                    'keyword': keyword,
                    'pcursor': pcursor
                },
                'query': query
            }

            response = self._request(self.graphql_url, method='POST', json=payload)
            if not response:
                break

            try:
                body = response.json()
                result = body.get('data', {}).get('visionSearchPhoto', {}).get('result', {})
                rows = result.get('list', [])
                if not rows:
                    break

                appended = 0
                for row in rows:
                    item = self._parse_row(row)
                    if item:
                        items.append(item)
                        appended += 1
                        if len(items) >= limit:
                            break

                if appended == 0:
                    break

                pcursor = result.get('pcursor', '')
                if not pcursor:
                    break

            except Exception as e:
                logger.error(f"Failed to parse kuaishou response: {e}")
                break

        logger.info(f"Collected {len(items)} items from Kuaishou for keyword: {keyword}")
        return items[:limit]

    def _parse_row(self, row: Dict) -> Optional[CollectedItem]:
        try:
            photo = row.get('photo', {}) or {}
            author = row.get('author', {}) or {}
            photo_id = str(photo.get('photoId', ''))
            return CollectedItem(
                platform=self.platform_name,
                content=photo.get('caption', ''),
                author=author.get('name', ''),
                author_id=str(author.get('id', '')),
                url=f"https://www.kuaishou.com/short-video/{photo_id}" if photo_id else '',
                publish_time=datetime.fromtimestamp(photo.get('uploadTime', 0)) if photo.get('uploadTime') else None,
                likes=photo.get('realLikeCount', photo.get('likeCount', 0)) or 0,
                comments=photo.get('commentCount', 0) or 0,
                metadata={
                    'photo_id': photo_id,
                    'duration': photo.get('duration', 0),
                    'view_count': photo.get('viewCount', 0),
                }
            )
        except Exception as e:
            logger.error(f"Failed to parse kuaishou row: {e}")
            return None

    def collect_user_info(self, user_id: str) -> Dict:
        return {
            'platform': self.platform_name,
            'user_id': user_id,
            'note': 'Kuaishou Web endpoint typically requires login context for full profile detail.'
        }


class BaiduCollector(BaseCollector):
    """百度搜索数据采集器"""
    
    platform_name = "baidu"
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.base_url = "https://www.baidu.com"
    
    def collect(self, keyword: str, limit: int = 100) -> List[CollectedItem]:
        """搜索采集百度结果"""
        from bs4 import BeautifulSoup
        
        items = []
        page = 0
        
        while len(items) < limit:
            url = f"{self.base_url}/s"
            params = {'wd': keyword, 'pn': page * 10}
            
            response = self._request(url, params=params)
            if not response:
                break
            
            try:
                soup = BeautifulSoup(response.text, 'lxml')
                results = soup.select('.result.c-container')
                
                if not results:
                    break
                
                for result in results:
                    item = self._parse_result(result)
                    if item:
                        items.append(item)
                
                page += 1
                
            except Exception as e:
                logger.error(f"Failed to parse baidu response: {e}")
                break
        
        return items[:limit]
    
    def _parse_result(self, element) -> Optional[CollectedItem]:
        """解析百度搜索结果"""
        try:
            title_elem = element.select_one('h3 a')
            content_elem = element.select_one('.c-abstract, .content-right_2s-H4')
            
            return CollectedItem(
                platform=self.platform_name,
                content=content_elem.get_text(strip=True) if content_elem else '',
                url=title_elem.get('href', '') if title_elem else '',
                metadata={
                    'title': title_elem.get_text(strip=True) if title_elem else '',
                }
            )
        except Exception as e:
            logger.error(f"Failed to parse baidu result: {e}")
            return None
    
    def collect_user_info(self, user_id: str) -> Dict:
        """百度不支持用户采集"""
        return {}


class WeChatCollector(BaseCollector):
    """微信公众号数据采集器
    
    注意：微信公众号数据采集需要：
    1. 通过搜狗微信搜索（公开数据）
    2. 通过微信公众平台API（需要认证）
    3. 通过第三方数据服务
    """
    
    platform_name = "wechat"
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
        # 使用搜狗微信搜索作为数据源
        self.base_url = "https://weixin.sogou.com"
        self.session.headers.update({
            'Referer': 'https://weixin.sogou.com/'
        })
    
    def collect(self, keyword: str, limit: int = 100) -> List[CollectedItem]:
        """搜索采集微信公众号文章"""
        from bs4 import BeautifulSoup
        
        items = []
        page = 1
        
        while len(items) < limit:
            url = f"{self.base_url}/weixin"
            params = {
                'query': keyword,
                'type': 2,  # 搜索文章
                'page': page
            }
            
            response = self._request(url, params=params)
            if not response:
                break
            
            try:
                soup = BeautifulSoup(response.text, 'lxml')
                articles = soup.select('.news-list li')
                
                if not articles:
                    break
                
                for article in articles:
                    item = self._parse_article(article)
                    if item:
                        items.append(item)
                        if len(items) >= limit:
                            break
                
                page += 1
                
            except Exception as e:
                logger.error(f"Failed to parse wechat response: {e}")
                break
        
        logger.info(f"Collected {len(items)} items from WeChat for keyword: {keyword}")
        return items
    
    def _parse_article(self, element) -> Optional[CollectedItem]:
        """解析文章元素"""
        try:
            title_elem = element.select_one('.txt-box h3 a')
            content_elem = element.select_one('.txt-box p')
            account_elem = element.select_one('.s-p a')
            time_elem = element.select_one('.s-p .s2')
            
            return CollectedItem(
                platform=self.platform_name,
                content=content_elem.get_text(strip=True) if content_elem else '',
                author=account_elem.get_text(strip=True) if account_elem else '',
                url=title_elem.get('href', '') if title_elem else '',
                metadata={
                    'title': title_elem.get_text(strip=True) if title_elem else '',
                    'time_str': time_elem.get_text(strip=True) if time_elem else '',
                }
            )
        except Exception as e:
            logger.error(f"Failed to parse wechat article: {e}")
            return None
    
    def collect_user_info(self, user_id: str) -> Dict:
        """采集公众号信息"""
        from bs4 import BeautifulSoup
        
        url = f"{self.base_url}/weixin"
        params = {
            'query': user_id,
            'type': 1,  # 搜索公众号
        }
        
        response = self._request(url, params=params)
        if not response:
            return {}
        
        try:
            soup = BeautifulSoup(response.text, 'lxml')
            account = soup.select_one('.news-box .news-list li')
            
            if not account:
                return {}
            
            name_elem = account.select_one('.txt-box h3')
            id_elem = account.select_one('.txt-box h4 span')
            desc_elem = account.select_one('.txt-box p.s-p')
            
            return {
                'platform': self.platform_name,
                'name': name_elem.get_text(strip=True) if name_elem else '',
                'wechat_id': id_elem.get_text(strip=True) if id_elem else '',
                'description': desc_elem.get_text(strip=True) if desc_elem else '',
            }
        except Exception as e:
            logger.error(f"Failed to get wechat account info: {e}")
            return {}


class XiaohongshuCollector(BaseCollector):
    """小红书数据采集器
    
    注意：小红书反爬机制较强，实际使用建议：
    1. 使用浏览器自动化
    2. 申请官方API
    3. 使用第三方数据服务
    """
    
    platform_name = "xiaohongshu"
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.base_url = "https://www.xiaohongshu.com"
        self.cookie = self.config.get('cookie', '')
        if self.cookie:
            self.session.headers['Cookie'] = self.cookie
    
    def collect(self, keyword: str, limit: int = 100) -> List[CollectedItem]:
        """搜索采集小红书笔记"""
        items = []
        
        # 小红书需要复杂的签名机制
        # 这里提供基础框架，实际使用需要：
        # 1. 分析签名算法（X-s, X-t 等参数）
        # 2. 使用 Selenium/Playwright 模拟浏览器
        # 3. 接入第三方数据服务
        
        logger.info(f"Xiaohongshu collection for '{keyword}' - requires browser automation or API access")
        
        # 返回基础结构
        return items
    
    def collect_user_info(self, user_id: str) -> Dict:
        """采集用户信息"""
        logger.info(f"Collecting Xiaohongshu user info for: {user_id}")
        return {
            'platform': self.platform_name,
            'user_id': user_id,
            'note': 'Requires browser automation or API access'
        }
    
    def _parse_note(self, note_data: Dict) -> Optional[CollectedItem]:
        """解析笔记数据（用于扩展实现）"""
        try:
            return CollectedItem(
                platform=self.platform_name,
                content=note_data.get('desc', ''),
                author=note_data.get('user', {}).get('nickname', ''),
                author_id=note_data.get('user', {}).get('user_id', ''),
                url=f"https://www.xiaohongshu.com/explore/{note_data.get('id', '')}",
                likes=note_data.get('likes', 0),
                comments=note_data.get('comments', 0),
                shares=note_data.get('shares', 0),
                metadata={
                    'title': note_data.get('title', ''),
                    'type': note_data.get('type', ''),  # 'normal' or 'video'
                    'images': note_data.get('images', []),
                }
            )
        except Exception as e:
            logger.error(f"Failed to parse xiaohongshu note: {e}")
            return None


class BilibiliCollector(BaseCollector):
    """B站数据采集器"""
    
    platform_name = "bilibili"
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.base_url = "https://api.bilibili.com"
        self.session.headers.update({
            'Referer': 'https://www.bilibili.com/'
        })
    
    def collect(self, keyword: str, limit: int = 100) -> List[CollectedItem]:
        """搜索采集B站视频"""
        items = []
        page = 1
        page_size = 50
        
        while len(items) < limit:
            url = f"{self.base_url}/x/web-interface/search/type"
            params = {
                'search_type': 'video',
                'keyword': keyword,
                'page': page,
                'page_size': page_size,
                'order': 'default'
            }
            
            response = self._request(url, params=params)
            if not response:
                break
            
            try:
                data = response.json()
                
                if data.get('code') != 0:
                    logger.error(f"Bilibili API error: {data.get('message')}")
                    break
                
                results = data.get('data', {}).get('result', [])
                
                if not results:
                    break
                
                for video in results:
                    item = self._parse_video(video)
                    if item:
                        items.append(item)
                        if len(items) >= limit:
                            break
                
                page += 1
                
            except Exception as e:
                logger.error(f"Failed to parse bilibili response: {e}")
                break
        
        logger.info(f"Collected {len(items)} items from Bilibili for keyword: {keyword}")
        return items
    
    def _parse_video(self, video: Dict) -> Optional[CollectedItem]:
        """解析视频数据"""
        try:
            return CollectedItem(
                platform=self.platform_name,
                content=video.get('description', ''),
                author=video.get('author', ''),
                author_id=str(video.get('mid', '')),
                url=f"https://www.bilibili.com/video/{video.get('bvid', '')}",
                publish_time=datetime.fromtimestamp(video.get('pubdate', 0)) if video.get('pubdate') else None,
                likes=video.get('like', 0),
                comments=video.get('review', 0),
                metadata={
                    'title': video.get('title', '').replace('<em class="keyword">', '').replace('</em>', ''),
                    'bvid': video.get('bvid', ''),
                    'aid': video.get('aid', ''),
                    'play': video.get('play', 0),
                    'danmaku': video.get('video_review', 0),
                    'duration': video.get('duration', ''),
                    'pic': video.get('pic', ''),
                    'tag': video.get('tag', ''),
                }
            )
        except Exception as e:
            logger.error(f"Failed to parse bilibili video: {e}")
            return None
    
    def collect_user_info(self, user_id: str) -> Dict:
        """采集UP主信息"""
        url = f"{self.base_url}/x/space/acc/info"
        params = {'mid': user_id}
        
        response = self._request(url, params=params)
        if not response:
            return {}
        
        try:
            data = response.json()
            
            if data.get('code') != 0:
                return {}
            
            user_data = data.get('data', {})
            return {
                'id': user_data.get('mid'),
                'name': user_data.get('name'),
                'avatar': user_data.get('face'),
                'sign': user_data.get('sign'),
                'level': user_data.get('level'),
                'sex': user_data.get('sex'),
                'birthday': user_data.get('birthday'),
                'official': user_data.get('official', {}),
            }
        except Exception as e:
            logger.error(f"Failed to get bilibili user info: {e}")
            return {}
    
    def collect_user_videos(self, user_id: str, limit: int = 50) -> List[CollectedItem]:
        """采集UP主视频列表"""
        items = []
        page = 1
        page_size = 30
        
        while len(items) < limit:
            url = f"{self.base_url}/x/space/arc/search"
            params = {
                'mid': user_id,
                'pn': page,
                'ps': page_size,
                'order': 'pubdate'
            }
            
            response = self._request(url, params=params)
            if not response:
                break
            
            try:
                data = response.json()
                
                if data.get('code') != 0:
                    break
                
                videos = data.get('data', {}).get('list', {}).get('vlist', [])
                
                if not videos:
                    break
                
                for video in videos:
                    item = CollectedItem(
                        platform=self.platform_name,
                        content=video.get('description', ''),
                        author=video.get('author', ''),
                        author_id=str(video.get('mid', '')),
                        url=f"https://www.bilibili.com/video/{video.get('bvid', '')}",
                        publish_time=datetime.fromtimestamp(video.get('created', 0)) if video.get('created') else None,
                        metadata={
                            'title': video.get('title', ''),
                            'bvid': video.get('bvid', ''),
                            'aid': video.get('aid', ''),
                            'play': video.get('play', 0),
                            'comment': video.get('comment', 0),
                            'pic': video.get('pic', ''),
                        }
                    )
                    items.append(item)
                
                page += 1
                
            except Exception as e:
                logger.error(f"Failed to collect user videos: {e}")
                break
        
        return items[:limit]


class TiebaCollector(BaseCollector):
    """百度贴吧数据采集器"""
    
    platform_name = "tieba"
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.base_url = "https://tieba.baidu.com"
    
    def collect(self, keyword: str, limit: int = 100) -> List[CollectedItem]:
        """搜索采集贴吧帖子"""
        from bs4 import BeautifulSoup
        
        items = []
        page = 0
        
        while len(items) < limit:
            url = f"{self.base_url}/f/search/res"
            params = {
                'qw': keyword,
                'pn': page,
                'rn': 20,
                'sm': 1
            }
            
            response = self._request(url, params=params)
            if not response:
                break
            
            try:
                soup = BeautifulSoup(response.text, 'lxml')
                posts = soup.select('.s_post')
                
                if not posts:
                    break
                
                for post in posts:
                    item = self._parse_post(post)
                    if item:
                        items.append(item)
                        if len(items) >= limit:
                            break
                
                page += 1
                
            except Exception as e:
                logger.error(f"Failed to parse tieba response: {e}")
                break
        
        logger.info(f"Collected {len(items)} items from Tieba for keyword: {keyword}")
        return items
    
    def _parse_post(self, element) -> Optional[CollectedItem]:
        """解析帖子元素"""
        try:
            title_elem = element.select_one('.p_title a')
            content_elem = element.select_one('.p_content')
            author_elem = element.select_one('.p_violet')
            forum_elem = element.select_one('.p_forum a')
            time_elem = element.select_one('.p_date')
            
            return CollectedItem(
                platform=self.platform_name,
                content=content_elem.get_text(strip=True) if content_elem else '',
                author=author_elem.get_text(strip=True) if author_elem else '',
                url=f"https://tieba.baidu.com{title_elem.get('href', '')}" if title_elem else '',
                publish_time=self._parse_time(time_elem.get_text(strip=True)) if time_elem else None,
                metadata={
                    'title': title_elem.get_text(strip=True) if title_elem else '',
                    'forum': forum_elem.get_text(strip=True) if forum_elem else '',
                }
            )
        except Exception as e:
            logger.error(f"Failed to parse tieba post: {e}")
            return None
    
    def collect_forum(self, forum_name: str, limit: int = 100) -> List[CollectedItem]:
        """采集贴吧帖子"""
        from bs4 import BeautifulSoup
        
        items = []
        page = 0
        
        while len(items) < limit:
            url = f"{self.base_url}/f"
            params = {
                'kw': forum_name,
                'pn': page * 50
            }
            
            response = self._request(url, params=params)
            if not response:
                break
            
            try:
                soup = BeautifulSoup(response.text, 'lxml')
                threads = soup.select('.j_thread_list')
                
                if not threads:
                    break
                
                for thread in threads:
                    title_elem = thread.select_one('.threadlist_title a')
                    author_elem = thread.select_one('.threadlist_author .tb_icon_author_no')
                    reply_elem = thread.select_one('.threadlist_rep_num')
                    
                    if title_elem:
                        item = CollectedItem(
                            platform=self.platform_name,
                            content='',
                            author=author_elem.get_text(strip=True) if author_elem else '',
                            url=f"https://tieba.baidu.com{title_elem.get('href', '')}",
                            comments=int(reply_elem.get_text(strip=True)) if reply_elem else 0,
                            metadata={
                                'title': title_elem.get_text(strip=True),
                                'forum': forum_name,
                            }
                        )
                        items.append(item)
                
                page += 1
                
            except Exception as e:
                logger.error(f"Failed to collect forum: {e}")
                break
        
        return items[:limit]
    
    def collect_user_info(self, user_id: str) -> Dict:
        """采集用户信息"""
        from bs4 import BeautifulSoup
        
        url = f"{self.base_url}/home/main"
        params = {'un': user_id}
        
        response = self._request(url, params=params)
        if not response:
            return {}
        
        try:
            soup = BeautifulSoup(response.text, 'lxml')
            
            name_elem = soup.select_one('.userinfo_username')
            
            return {
                'platform': self.platform_name,
                'name': name_elem.get_text(strip=True) if name_elem else user_id,
            }
        except Exception as e:
            logger.error(f"Failed to get tieba user info: {e}")
            return {}


class ToutiaoCollector(BaseCollector):
    """今日头条数据采集器
    
    注意：头条有复杂的反爬机制，实际使用建议：
    1. 使用头条号API
    2. 使用浏览器自动化
    """
    
    platform_name = "toutiao"
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.base_url = "https://www.toutiao.com"
        self.api_url = "https://www.toutiao.com/api/search/content"
    
    def collect(self, keyword: str, limit: int = 100) -> List[CollectedItem]:
        """搜索采集头条内容"""
        items = []
        offset = 0
        
        while len(items) < limit:
            params = {
                'keyword': keyword,
                'offset': offset,
                'count': 20,
                'from': 'search_tab',
                'pd': 'synthesis',
            }
            
            response = self._request(self.api_url, params=params)
            if not response:
                break
            
            try:
                data = response.json()
                
                if data.get('err_no') != 0:
                    # 头条可能需要额外的签名参数
                    logger.warning("Toutiao API may require additional parameters")
                    break
                
                results = data.get('data', [])
                
                if not results:
                    break
                
                for item_data in results:
                    item = self._parse_content(item_data)
                    if item:
                        items.append(item)
                        if len(items) >= limit:
                            break
                
                offset += 20
                
            except Exception as e:
                logger.error(f"Failed to parse toutiao response: {e}")
                break
        
        logger.info(f"Collected {len(items)} items from Toutiao for keyword: {keyword}")
        return items
    
    def _parse_content(self, content: Dict) -> Optional[CollectedItem]:
        """解析内容数据"""
        try:
            return CollectedItem(
                platform=self.platform_name,
                content=content.get('abstract', ''),
                author=content.get('source', ''),
                author_id=content.get('user_id', ''),
                url=f"https://www.toutiao.com/article/{content.get('item_id', '')}",
                publish_time=datetime.fromtimestamp(content.get('publish_time', 0)) if content.get('publish_time') else None,
                likes=content.get('like_count', 0),
                comments=content.get('comment_count', 0),
                metadata={
                    'title': content.get('title', ''),
                    'item_id': content.get('item_id', ''),
                    'group_id': content.get('group_id', ''),
                    'read_count': content.get('read_count', 0),
                    'image_list': content.get('image_list', []),
                }
            )
        except Exception as e:
            logger.error(f"Failed to parse toutiao content: {e}")
            return None
    
    def collect_user_info(self, user_id: str) -> Dict:
        """采集头条号信息"""
        logger.info(f"Collecting Toutiao user info for: {user_id}")
        return {
            'platform': self.platform_name,
            'user_id': user_id,
            'note': 'Requires browser automation or API access'
        }


class CollectorFactory:
    """采集器工厂"""
    
    _collectors = {
        'weibo': WeiboCollector,
        'douyin': DouyinCollector,
        'kuaishou': KuaishouCollector,
        'zhihu': ZhihuCollector,
        'baidu': BaiduCollector,
        'wechat': WeChatCollector,
        'xiaohongshu': XiaohongshuCollector,
        'bilibili': BilibiliCollector,
        'tieba': TiebaCollector,
        'toutiao': ToutiaoCollector,
    }
    
    @classmethod
    def create(cls, platform: str, config: Dict = None) -> BaseCollector:
        """创建采集器实例"""
        collector_class = cls._collectors.get(platform.lower())
        if not collector_class:
            raise ValueError(f"Unknown platform: {platform}. Available: {list(cls._collectors.keys())}")
        return collector_class(config)
    
    @classmethod
    def register(cls, platform: str, collector_class: type):
        """注册新的采集器"""
        cls._collectors[platform.lower()] = collector_class
    
    @classmethod
    def available_platforms(cls) -> List[str]:
        """获取可用平台列表"""
        return list(cls._collectors.keys())
    
    @classmethod
    def get_platform_info(cls) -> List[Dict]:
        """获取所有平台的详细信息"""
        platforms_info = {
            'weibo': {'name': '微博', 'description': '新浪微博内容采集', 'requires_auth': False},
            'douyin': {'name': '抖音', 'description': '抖音网页搜索采集（公开接口）', 'requires_auth': False},
            'kuaishou': {'name': '快手', 'description': '快手网页 GraphQL 采集', 'requires_auth': False},
            'zhihu': {'name': '知乎', 'description': '知乎问答内容采集', 'requires_auth': False},
            'baidu': {'name': '百度', 'description': '百度搜索结果采集', 'requires_auth': False},
            'wechat': {'name': '微信公众号', 'description': '微信公众号文章采集', 'requires_auth': False},
            'xiaohongshu': {'name': '小红书', 'description': '小红书笔记采集', 'requires_auth': True},
            'bilibili': {'name': 'B站', 'description': 'B站视频内容采集', 'requires_auth': False},
            'tieba': {'name': '百度贴吧', 'description': '百度贴吧帖子采集', 'requires_auth': False},
            'toutiao': {'name': '今日头条', 'description': '今日头条内容采集', 'requires_auth': True},
        }
        
        result = []
        for platform_id, collector_class in cls._collectors.items():
            info = platforms_info.get(platform_id, {})
            result.append({
                'id': platform_id,
                'name': info.get('name', platform_id),
                'description': info.get('description', ''),
                'requires_auth': info.get('requires_auth', False),
                'enabled': True,
            })
        
        return result
