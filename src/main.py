# main.py
import tweepy
import os
import time
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass

# 環境変数読み込み
from dotenv import load_dotenv
load_dotenv()

@dataclass
class RateLimitInfo:
    remaining: int = 15
    reset: int = 0
    last_updated: float = 0.0

class XListManager:
    def __init__(self):
        # API認証情報の初期化
        self.auth = tweepy.OAuth1UserHandler(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        
        # APIクライアントの初期化
        self.client = tweepy.Client(
            bearer_token=os.getenv("BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        
        # 動的レートリミット管理用のデータ構造
        self.rate_limits = {
            'users': RateLimitInfo(),        # /2/users/*
            'tweets': RateLimitInfo(),      # /2/tweets/*
            'lists': RateLimitInfo(),       # /2/lists/*
            'default': RateLimitInfo()      # その他エンドポイント
        }
        
        # 初期設定
        self.my_id = self._safe_get_me()
        self.my_followers = self._get_my_followers_count()

    def _safe_get_me(self) -> Optional[str]:
        """安全に自身のユーザーIDを取得"""
        try:
            return self.client.get_me().data.id
        except tweepy.TweepyException as e:
            print(f"ユーザー情報取得エラー: {str(e)}")
            return None

    def _get_headers(self) -> dict:
        """直近のレスポンスヘッダーを取得"""
        return self.client.get_last_response().headers if self.client.get_last_response() else {}

    def _update_rate_limits(self, endpoint_type: str):
        """レートリミット情報を更新"""
        headers = self._get_headers()
        now = time.time()
        
        self.rate_limits[endpoint_type].remaining = int(headers.get('x-rate-limit-remaining', 1))
        self.rate_limits[endpoint_type].reset = int(headers.get('x-rate-limit-reset', now + 900))
        self.rate_limits[endpoint_type].last_updated = now

    def _calculate_wait_time(self, endpoint_type: str) -> float:
        """動的待機時間計算アルゴリズム"""
        rl = self.rate_limits[endpoint_type]
        now = time.time()
        
        if rl.remaining > 0:
            time_per_request = (rl.reset - now) / rl.remaining
            return max(time_per_request, 1.0)  # 最低1秒は確保
        
        # レートリミット到達時の安全マージン付き待機時間
        return max(rl.reset - now + 5.0, 0.0)

    def _dynamic_wait(self, endpoint_type: str):
        """インテリジェント待機処理"""
        wait_time = self._calculate_wait_time(endpoint_type)
        
        if wait_time > 0:
            print(f"[Rate Limit] {endpoint_type} | 待機: {wait_time:.2f}s | リセット: {datetime.fromtimestamp(rl.reset).strftime('%H:%M:%S')}")
            time.sleep(wait_time)

    def _execute_with_retry(self, func, endpoint_type: str, max_retries=3, **kwargs):
        """リトライ付きAPI実行ラッパー"""
        for attempt in range(max_retries):
            try:
                self._dynamic_wait(endpoint_type)
                result = func(**kwargs)
                self._update_rate_limits(endpoint_type)
                return result
            except tweepy.TooManyRequests as e:
                reset_time = int(e.response.headers.get('x-rate-limit-reset', time.time() + 900))
                wait_time = max(reset_time - time.time() + 5.0, 0.0)
                print(f"レートリミット到達: {wait_time:.1f}秒待機 (試行 {attempt+1}/{max_retries})")
                time.sleep(wait_time)
            except tweepy.TweepyException as e:
                print(f"APIエラー: {str(e)}")
                break
        return None

    def _get_my_followers_count(self) -> int:
        """自身のフォロワー数取得（レートリミット対応版）"""
        response = self._execute_with_retry(
            self.client.get_me,
            'users',
            user_fields=["public_metrics"]
        )
        return response.data.public_metrics["followers_count"] if response else 0

    def _is_singer(self, user: tweepy.User) -> bool:
        """歌い手判定ロジック"""
        keywords = ["歌い手", "singer", "ボーカル", "音楽活動"]
        return any(k in user.description.lower() for k in keywords) if user.description else False

    def _check_follower_range(self, user: tweepy.User) -> bool:
        """フォロワー数範囲チェック"""
        return (self.my_followers - 500) <= user.public_metrics["followers_count"] <= (self.my_followers + 500)

    def _check_posting_frequency(self, user_id: str) -> bool:
        """投稿頻度分析（動的レートリミット対応）"""
        response = self._execute_with_retry(
            self.client.get_users_tweets,
            'tweets',
            user_id=user_id,
            max_results=50,
            tweet_fields=["created_at"]
        )
        
        if not response or not response.data:
            return False
            
        dates = set()
        for tweet in response.data:
            if tweet.created_at > datetime.utcnow() - timedelta(days=7):
                dates.add(tweet.created_at.date())
        
        return len(dates) >= 5

    def _check_retweet_ratio(self, user_id: str) -> bool:
        """リポスト頻度分析（動的レートリミット対応）"""
        response = self._execute_with_retry(
            self.client.get_users_tweets,
            'tweets',
            user_id=user_id,
            max_results=100,
            exclude="replies"
        )
        
        if not response or not response.data:
            return False
            
        retweet_count = sum(
            1 for t in response.data 
            if t.referenced_tweets and t.referenced_tweets[0].type == "retweeted"
        )
        return retweet_count / len(response.data) > 0.25

    def _check_like_ratio(self, user: tweepy.User) -> bool:
        """いいね率チェック"""
        total_likes = user.public_metrics["like_count"]
        followers = user.public_metrics["followers_count"]
        return (total_likes / followers) >= 0.01 if followers > 0 else False

    def find_target_users(self) -> List[str]:
        """条件に合致するユーザー検索（改良版）"""
        if not self.my_id:
            return []
            
        response = self._execute_with_retry(
            self.client.get_users_followers,
            'users',
            id=self.my_id,
            max_results=1000,
            user_fields=["public_metrics", "description"]
        )
        
        if not response:
            return []
            
        target_users = []
        for user in response.data:
            if user.id == self.my_id:
                continue
            
            checks = [
                self._is_singer(user),
                self._check_follower_range(user),
                self._check_posting_frequency(user.id),
                self._check_follower_ratio(user),
                self._check_retweet_ratio(user.id),
                self._check_like_ratio(user)
            ]
            
            if all(checks):
                target_users.append(user.id)
        
        return target_users

    def create_list(self, list_name: str) -> Dict:
        """リスト作成（レートリミット対応版）"""
        response = self._execute_with_retry(
            self.client.create_list,
            'lists',
            name=list_name,
            description="自動生成リスト",
            private=True
        )
        
        if response and response.data:
            return {"status": "success", "list_id": response.data.id}
        return {"status": "error", "message": "リスト作成失敗"}

    def add_to_list(self, list_id: str, user_ids: List[str]) -> Dict:
        """リストへの一括追加（最適化版）"""
        results = {"success": 0, "failed": 0}
        
        for user_id in user_ids:
            response = self._execute_with_retry(
                self.client.add_list_member,
                'lists',
                list_id=list_id,
                user_id=user_id
            )
            
            if response and response.data.get("is_member"):
                results["success"]