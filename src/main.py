import tweepy
from dotenv import load_dotenv
import os
import logging

logging.basicConfig(level=logging.INFO)

class XCoreClient:
    def __init__(self):
        load_dotenv()
        self._validate_env_vars()
        self._initialize_client()
    
    def _validate_env_vars(self):
        """環境変数の検証"""
        required_envs = [
            'BEARER_TOKEN',
            'X_API_KEY',
            'X_API_SECRET',
            'X_ACCESS_TOKEN',
            'X_ACCESS_SECRET'
        ]
        
        missing = [env for env in required_envs if not os.getenv(env)]
        if missing:
            raise ValueError(f'Missing environment variables: {", ".join(missing)}')

    def _initialize_client(self):
        """APIクライアントの初期化"""
        try:
            self.client = tweepy.Client(
                bearer_token=os.getenv("BEARER_TOKEN"),
                consumer_key=os.getenv("X_API_KEY"),
                consumer_secret=os.getenv("X_API_SECRET"),
                access_token=os.getenv("X_ACCESS_TOKEN"),
                access_token_secret=os.getenv("X_ACCESS_SECRET")
            )
            logging.info("X API client initialized successfully")
        except Exception as e:
            logging.error(f"Client initialization failed: {str(e)}")
            raise

    def get_my_profile(self):
        """自身のプロフィール取得"""
        try:
            return self.client.get_me()
        except tweepy.TweepyException as e:
            logging.error(f"Profile fetch failed: {str(e)}")
            raise
    
    def create_list(self, name, description="", private=True):
        """リスト作成"""
        try:
            return self.client.create_list(
                name=name,
                description=description,
                private=private
            )
        except tweepy.TweepyException as e:
            logging.error(f"List creation failed: {str(e)}")
            raise
    
    def add_to_list(self, list_id, user_id):
        """リストへのユーザー追加"""
        try:
            return self.client.add_list_member(
                list_id=list_id,
                user_id=user_id
            )
        except tweepy.TweepyException as e:
            logging.error(f"Add member failed: {str(e)}")
            raise

if __name__ == "__main__":
    try:
        client = XCoreClient()
        print("Initialization successful!")
    except Exception as e:
        print(f"Initialization failed: {str(e)}")