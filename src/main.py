# core.py
import tweepy
from dotenv import load_dotenv
import os

class XCoreClient:
    def __init__(self):
        load_dotenv()
        self.client = tweepy.Client(
            bearer_token=os.getenv("BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
    
    def get_my_profile(self):
        return self.client.get_me()
    
    def create_list(self, name, description="", private=True):
        return self.client.create_list(
            name=name,
            description=description,
            private=private
        )

    def add_to_list(self, list_id, user_id):
        return self.client.add_list_member(
            list_id=list_id,
            user_id=user_id
        )