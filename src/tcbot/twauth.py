import tweepy

from .exception import TCBotError


class TwitterAuth:
    def __init__(
        self,
        consumer_key: str,
        consumer_secret: str,
        access_token: str,
        access_secret: str,
    ):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.access_token = access_token
        self.access_secret = access_secret

        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_secret)
        api = tweepy.API(auth)
        try:
            api.verify_credentials()
        except tweepy.TweepError as exc:
            raise TCBotError("Failed to authenticate twitter api.") from exc

        self.api = api
        self.auth = auth
