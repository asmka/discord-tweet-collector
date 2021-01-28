class Config:
    def __init__(self, dic):
        if "bot_token" not in dic:
            raise ValueError("bot_token is not in dic")
        if "consumer_key" not in dic:
            raise ValueError("consumer_key is not in dic")
        if "consumer_secret" not in dic:
            raise ValueError("consumer_secret is not in dic")
        if "access_token" not in dic:
            raise ValueError("access_token is not in dic")
        if "access_secret" not in dic:
            raise ValueError("access_secret is not in dic")

        self.bot_token = dic["bot_token"]
        self.consumer_key = dic["consumer_key"]
        self.consumer_secret = dic["consumer_secret"]
        self.access_token = dic["access_token"]
        self.access_secret = dic["access_secret"]
