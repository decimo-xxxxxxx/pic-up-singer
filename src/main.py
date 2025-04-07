# main.py
import tweepy
import os
from dotenv import load_dotenv
import time

# 環境変数の読み込み（X_ プレフィックスに変更）
load_dotenv()
X_API_KEY = os.getenv("X_API_KEY")
X_API_SECRET = os.getenv("X_API_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_SECRET = os.getenv("X_ACCESS_SECRET")
BEARER_TOKEN = os.getenv("BEARER_TOKEN")

class XListManager:
    def __init__(self):
        # OAuth 1.0a 認証（Xに名称変更）
        self.auth = tweepy.OAuth1UserHandler(
            consumer_key=X_API_KEY,
            consumer_secret=X_API_SECRET,
            access_token=X_ACCESS_TOKEN,
            access_token_secret=X_ACCESS_SECRET
        )
        
        # X APIクライアント初期化
        self.client = tweepy.Client(
            bearer_token=BEARER_TOKEN,
            consumer_key=X_API_KEY,
            consumer_secret=X_API_SECRET,
            access_token=X_ACCESS_TOKEN,
            access_token_secret=X_ACCESS_SECRET
        )
        
        # レートリミット管理用
        self.last_request = time.time()
        self.request_interval = 1.1  # X APIのレートリミット対策

    def _rate_limit_check(self):
        """X APIのレートリミットを遵守するための待機処理"""
        elapsed = time.time() - self.last_request
        if elapsed < self.request_interval:
            time.sleep(self.request_interval - elapsed)
        self.last_request = time.time()

    def create_list(self, list_name: str, description: str = "") -> dict:
        """Xリストを作成"""
        self._rate_limit_check()
        try:
            response = self.client.create_list(
                name=list_name,
                description=description,
                private=True
            )
            return {
                "status": "success",
                "list_id": response.data["id"]
            }
        except tweepy.TweepyException as e:
            return {
                "status": "error",
                "message": f"Xリスト作成失敗: {str(e)}"
            }

    def add_to_list(self, list_id: str, user_id: str) -> dict:
        """Xリストにユーザーを追加"""
        self._rate_limit_check()
        try:
            response = self.client.add_list_member(
                list_id=list_id,
                user_id=user_id
            )
            return {
                "status": "success" if response.data["is_member"] else "error",
                "message": "追加成功" if response.data["is_member"] else "追加失敗"
            }
        except tweepy.TweepyException as e:
            return {
                "status": "error",
                "message": f"Xリスト追加失敗: {str(e)}"
            }

if __name__ == "__main__":
    # 使用例
    manager = XListManager()
    
    # リスト作成
    list_result = manager.create_list(
        "歌い手リスト", 
        "自動収集した歌い手アカウントのリスト"
    )
    
    if list_result["status"] == "success":
        print(f"リスト作成成功 ID: {list_result['list_id']}")
        
        # ユーザー追加例（実際のユーザーIDに置き換えてください）
        user_result = manager.add_to_list(
            list_result["list_id"], 
            "1234567890"  # 追加するユーザーID
        )
        print(user_result["message"])
    else:
        print(f"エラー: {list_result['message']}")