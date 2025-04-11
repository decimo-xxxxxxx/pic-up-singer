# main.py
import tweepy
import os
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
from typing import List, Dict

# 環境変数の読み込み
load_dotenv()

class XListManager:
    def __init__(self):
        # API認証情報
        self.auth = tweepy.OAuth1UserHandler(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        
        # APIクライアント初期化
        self.client = tweepy.Client(
            bearer_token=os.getenv("BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        
        # レートリミット管理
        self.request_interval = 3.5  # 秒
        self.last_request = time.time()
        self.my_followers = self._get_my_followers_count()

    def _rate_limit_check(self):
        """APIレートリミット管理"""
        elapsed = time.time() - self.last_request
        if elapsed < self.request_interval:
            time.sleep(self.request_interval - elapsed)
        self.last_request = time.time()

    def _get_my_followers_count(self) -> int:
        """自身のフォロワー数取得"""
        self._rate_limit_check()
        return self.client.get_me().data.public_metrics["followers_count"]

    def _is_singer(self, user: tweepy.User) -> bool:
        """歌い手判定"""
        keywords = ["歌い手", "singer", "ボーカル", "音楽活動", "vocalist"]
        return any(k in user.description.lower() for k in keywords) if user.description else False

    def _check_follower_range(self, user: tweepy.User) -> bool:
        """フォロワー数範囲チェック"""
        return (self.my_followers - 500) <= user.public_metrics["followers_count"] <= (self.my_followers + 500)

    def _check_posting_frequency(self, user_id: str) -> bool:
        """毎日投稿チェック"""
        self._rate_limit_check()
        tweets = self.client.get_users_tweets(
            user_id,
            max_results=50,
            tweet_fields=["created_at"]
        )
        
        if not tweets.data:
            return False
            
        dates = set()
        for tweet in tweets.data:
            if tweet.created_at > datetime.utcnow() - timedelta(days=7):
                dates.add(tweet.created_at.date())
        
        return len(dates) >= 5  # 週5日以上投稿

    def _check_follower_ratio(self, user: tweepy.User) -> bool:
        """フォロワー/フォロー比率"""
        return user.public_metrics["followers_count"] > user.public_metrics["following_count"]

    def _check_retweet_ratio(self, user_id: str) -> bool:
        """リポスト頻度チェック"""
        self._rate_limit_check()
        tweets = self.client.get_users_tweets(
            user_id,
            max_results=100,
            exclude="replies"
        )
        
        if not tweets.data:
            return False
            
        retweet_count = 0
        for tweet in tweets.data:
            if tweet.referenced_tweets:
                for ref in tweet.referenced_tweets:
                    if ref.type == "retweeted":
                        retweet_count += 1
        
        return (retweet_count / len(tweets.data)) > 0.25  # 25%以上

    def _check_like_ratio(self, user: tweepy.User) -> bool:
        """いいね率チェック"""
        total_likes = user.public_metrics["like_count"]
        followers = user.public_metrics["followers_count"]
        return (total_likes / followers) >= 0.01 if followers > 0 else False

    def find_target_users(self) -> List[str]:
        """条件に合致するユーザーを検索"""
        self._rate_limit_check()
        my_id = self.client.get_me().data.id
        candidates = self.client.get_users_followers(
            id=my_id,
            max_results=1000,
            user_fields=["public_metrics", "description"]
        )
        
        target_users = []
        for user in candidates.data:
            if user.id == my_id:
                continue  # 自分自身を除外
            
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
        """リスト作成"""
        self._rate_limit_check()
        try:
            response = self.client.create_list(
                name=list_name,
                description="自動生成リスト",
                private=True
            )
            return {"status": "success", "list_id": response.data.id}
        except tweepy.TweepyException as e:
            return {"status": "error", "message": str(e)}

    def add_to_list(self, list_id: str, user_ids: List[str]):
        """リストにユーザー一括追加"""
        results = []
        for user_id in user_ids:
            self._rate_limit_check()
            try:
                response = self.client.add_list_member(
                    list_id=list_id,
                    user_id=user_id
                )
                results.append({
                    "user_id": user_id,
                    "status": "success" if response.data["is_member"] else "error"
                })
            except tweepy.TweepyException as e:
                results.append({
                    "user_id": user_id,
                    "status": "error",
                    "message": str(e)
                })
        return results

if __name__ == "__main__":
    manager = XListManager()
    
    try:
        print("対象ユーザー検索を開始します...")
        target_users = manager.find_target_users()
        
        if not target_users:
            print("条件に合致するユーザーが見つかりませんでした")
            exit()
            
        print(f"対象ユーザー {len(target_users)}人を発見")
        
        list_result = manager.create_list("自動収集歌い手リスト")
        if list_result["status"] != "success":
            print(f"リスト作成エラー: {list_result['message']}")
            exit()
            
        print(f"リストを作成しました ID: {list_result['list_id']}")
        
        print("ユーザーをリストに追加中...")
        results = manager.add_to_list(list_result["list_id"], target_users)
        
        success = sum(1 for r in results if r["status"] == "success")
        print(f"追加完了: 成功 {success}件 / 失敗 {len(results)-success}件")
        
    except tweepy.TooManyRequests as e:
        print(f"レートリミットに達しました。{e.reset_time}まで待機してください")
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {str(e)}")