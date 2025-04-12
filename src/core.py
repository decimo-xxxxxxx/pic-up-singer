# core.py
import tweepy
from dotenv import load_dotenv
import os
import sys
import time
import json
from typing import Optional

class XCoreClient:
    def __init__(self):
        try:
            # 環境変数のロードと検証
            load_dotenv()
            self._validate_env_vars()
            
            # APIクライアントの初期化
            self.client = tweepy.Client(
                bearer_token=os.getenv("BEARER_TOKEN"),
                consumer_key=os.getenv("X_API_KEY"),
                consumer_secret=os.getenv("X_API_SECRET"),
                access_token=os.getenv("X_ACCESS_TOKEN"),
                access_token_secret=os.getenv("X_ACCESS_SECRET")
            )
            
            # 初期接続テスト
            self._test_connection()
            
        except Exception as e:
            self._handle_initialization_error(e)

    def _validate_env_vars(self):
        """必須環境変数の検証"""
        required_vars = [
            'BEARER_TOKEN',
            'X_API_KEY',
            'X_API_SECRET',
            'X_ACCESS_TOKEN',
            'X_ACCESS_SECRET'
        ]
        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            raise ValueError(f"Missing environment variables: {', '.join(missing)}")

    def _test_connection(self):
        """初期接続テスト"""
        try:
            self.get_my_profile()
        except tweepy.TweepyException as e:
            raise ConnectionError(f"X API connection failed: {str(e)}")

    def _handle_initialization_error(self, error):
        """初期化エラー処理"""
        error_info = {
            "timestamp": datetime.now().isoformat(),
            "error": str(error),
            "type": type(error).__name__,
            "env_loaded": os.getenv("BEARER_TOKEN") is not None
        }
        print(json.dumps({"status": "INIT_FAILED", "details": error_info}, indent=2))
        sys.exit(1)

    def get_my_profile(self):
        """プロフィール取得（エラーハンドリング強化版）"""
        try:
            return self.client.get_me()
        except tweepy.TweepyException as e:
            print(f"プロフィール取得エラー: {str(e)}")
            return None

    def create_list(self, name: str, description: str = "", private: bool = True) -> Optional[Dict]:
        """リスト作成（リトライ機構付き）"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return self.client.create_list(
                    name=name,
                    description=description,
                    private=private
                )
            except tweepy.TooManyRequests as e:
                wait = self._calculate_wait_time(e, attempt)
                print(f"レートリミット到達: {wait}秒待機 (試行 {attempt+1}/{max_retries})")
                time.sleep(wait)
            except tweepy.TweepyException as e:
                print(f"リスト作成エラー: {str(e)}")
                break
        return None

    def add_to_list(self, list_id: str, user_id: str) -> Optional[Dict]:
        """リスト追加（リトライ機構付き）"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return self.client.add_list_member(
                    list_id=list_id,
                    user_id=user_id
                )
            except tweepy.TooManyRequests as e:
                wait = self._calculate_wait_time(e, attempt)
                print(f"レートリミット到達: {wait}秒待機 (試行 {attempt+1}/{max_retries})")
                time.sleep(wait)
            except tweepy.TweepyException as e:
                print(f"リスト追加エラー: {str(e)}")
                break
        return None

    def _calculate_wait_time(self, error: tweepy.TweepyException, attempt: int) -> float:
        """待機時間計算（指数バックオフ）"""
        base_wait = 5.0
        max_wait = 60.0
        reset_time = getattr(error.response, 'headers', {}).get('x-rate-limit-reset')
        
        if reset_time:
            return min(float(reset_time) - time.time() + 2.0, max_wait)
        return min(base_wait * (2 ** attempt), max_wait)

# テスト用エントリーポイント
if __name__ == "__main__":
    try:
        client = XCoreClient()
        print("初期化成功")
        
        # テスト実行
        profile = client.get_my_profile()
        if profile:
            print(f"ユーザー名: {profile.data.name}")
            
        test_list = client.create_list("テストリスト")
        if test_list:
            print(f"リスト作成成功 ID: {test_list.data.id}")
            
    except Exception as e:
        print(f"致命的なエラー: {str(e)}")
        sys.exit(1)