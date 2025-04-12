import tweepy
import os
import time
import random
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from typing import List, Dict, Optional, Set

load_dotenv()

class EnhancedLogger:
    def __init__(self):
        self.steps = {
            'initialize': "APIクライアント初期化",
            'fetch_followers': "フォロワー取得",
            'fetch_following': "フォロー中取得",
            'filter_users': "ユーザーフィルタリング",
            'list_management': "リスト管理",
            'add_users': "ユーザー追加"
        }
        self.start_time = time.time()
        self.rate_limit_data = {}

    def log(self, stage: str, message: str, level: str = "info"):
        icons = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "success": "✅"}
        elapsed = time.time() - self.start_time
        print(f"[{elapsed:05.1f}s] {icons.get(level, '')} {self.steps[stage]}: {message}")

    def update_rate_limit(self, endpoint: str, headers: Dict):
        remaining = int(headers.get('x-rate-limit-remaining', 1))
        reset = int(headers.get('x-rate-limit-reset', time.time() + 900))
        self.rate_limit_data[endpoint] = {
            'remaining': remaining,
            'reset_time': datetime.fromtimestamp(reset, tz=timezone.utc)
        }

class SmartListManager:
    def __init__(self):
        self.logger = EnhancedLogger()
        self.client = self._initialize_client()
        self.user_info = self._get_user_info()
        self.following_ids: Set[str] = set()
        self.request_interval = 60  # 基本間隔（秒）

    def _initialize_client(self):
        self.logger.log('initialize', 'クライアントを初期化中...')
        return tweepy.Client(
            bearer_token=os.getenv("BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=True
        )

    def _get_user_info(self):
        response = self.client.get_me(user_fields=["public_metrics"])
        if not response.data:
            self.logger.log('initialize', 'ユーザー情報取得失敗', 'error')
            exit(1)
            
        self.logger.log('initialize', f"ユーザー @{response.data.username} で接続成功")
        return {
            'id': response.data.id,
            'followers_count': response.data.public_metrics['followers_count']
        }

    def _fetch_paginated(self, endpoint, **kwargs):
        users = []
        pagination_token = None
        
        while True:
            try:
                response = endpoint(
                    id=self.user_info['id'],
                    pagination_token=pagination_token,
                    **kwargs
                )
                users.extend(response.data)
                
                self.logger.update_rate_limit(kwargs['endpoint'], response.response.headers)
                
                if 'next_token' not in response.meta:
                    break
                    
                pagination_token = response.meta['next_token']
                self._safe_sleep('pagination', 2)
                
            except tweepy.TweepyException as e:
                self.logger.log('fetch_followers' if 'followers' in str(endpoint) else 'fetch_following',
                              f"エラー: {str(e)[:50]}", 'error')
                break
        
        return users

    def _safe_sleep(self, context: str, base_delay: int):
        jitter = random.uniform(0.5, 1.5)
        delay = base_delay * jitter
        self.logger.log(context, f"待機中: {delay:.1f}s")
        time.sleep(delay)

    def get_non_following_users(self) -> List[tweepy.User]:
        self.logger.log('fetch_followers', 'フォロワー取得開始')
        followers = self._fetch_paginated(
            self.client.get_users_followers,
            endpoint='/2/users/:id/followers',
            max_results=1000,
            user_fields=["description", "public_metrics"]
        )
        
        self.logger.log('fetch_following', 'フォロー中取得開始')
        following = self._fetch_paginated(
            self.client.get_users_following,
            endpoint='/2/users/:id/following',
            max_results=1000
        )
        self.following_ids = {user.id for user in following}
        
        non_following = [user for user in followers if user.id not in self.following_ids]
        self.logger.log('filter_users', f"非フォローユーザー数: {len(non_following)}")
        return non_following

    def _is_vocalist(self, user: tweepy.User) -> bool:
        keywords = {"歌い手", "vocal", "cover", "artist", "シンガー", "音楽"}
        platforms = {"youtube.com", "spotify.com", "soundcloud.com"}
        desc = (user.description or "").lower()
        return any(kw in desc for kw in keywords) or any(p in desc for p in platforms)

    def _check_conditions(self, user: tweepy.User) -> bool:
        metrics = user.public_metrics
        target_range = (
            self.user_info['followers_count'] - 500,
            self.user_info['followers_count'] + 500
        )
        
        # 基本条件
        if not (target_range[0] <= metrics['followers_count'] <= target_range[1]):
            return False
        if metrics['followers_count'] <= metrics['following_count']:
            return False
            
        # アクティビティチェック
        tweets = self._get_recent_tweets(user.id)
        if not tweets:
            return False
            
        latest_tweet = max(tweets, key=lambda x: x.created_at)
        if (datetime.now(timezone.utc) - latest_tweet.created_at) > timedelta(hours=24):
            return False
            
        # エンゲージメント分析
        total_likes = sum(t.public_metrics['like_count'] for t in tweets)
        engagement = total_likes / (len(tweets) * metrics['followers_count'])
        if engagement < 0.01:
            return False
            
        # リツイート率
        retweets = [t for t in tweets if t.text.startswith("RT @")]
        if len(retweets)/len(tweets) < 0.3:
            return False
            
        return True

    def _get_recent_tweets(self, user_id: str) -> List[tweepy.Tweet]:
        try:
            response = self.client.get_users_tweets(
                id=user_id,
                max_results=100,
                exclude=["retweets", "replies"],
                tweet_fields=["public_metrics", "created_at"]
            )
            self._safe_sleep('tweet_fetch', 2)
            return response.data or []
        except tweepy.TweepyException as e:
            self.logger.log('filter_users', f"ツイート取得エラー: {str(e)[:50]}", 'error')
            return []

    def process_list(self, list_name: str = "歌い手リスト", max_users: int = 50):
        try:
            # リスト作成
            self.logger.log('list_management', 'リスト作成/取得中')
            list_id = self.client.create_list(
                name=list_name,
                description="自動収集歌い手リスト",
                private=True
            ).data['id']
            
            # ユーザー選定
            candidates = self.get_non_following_users()
            eligible = [u for u in candidates if self._is_vocalist(u) and self._check_conditions(u)]
            
            # ユーザー追加
            self.logger.log('add_users', f"追加対象 {len(eligible)} 人中 {max_users} 人を追加")
            added_count = 0
            for user in eligible[:max_users]:
                try:
                    self.client.add_list_member(
                        id=list_id,
                        user_id=user.id
                    )
                    added_count += 1
                    self.logger.log('add_users', f"追加成功: @{user.username}")
                    self._safe_sleep('add_user', 120)  # 2分間隔
                except tweepy.TweepyException as e:
                    self.logger.log('add_users', f"追加失敗: {str(e)[:50]}", 'error')
            
            self.logger.log('list_management', f"完了: {added_count} ユーザー追加", 'success')
            
        except tweepy.TweepyException as e:
            self.logger.log('list_management', f"致命的エラー: {str(e)}", 'error')

if __name__ == "__main__":
    manager = SmartListManager()
    manager.process_list(max_users=30)