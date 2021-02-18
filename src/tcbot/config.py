import os
import json


class Config:
    def __init__(self, file_name: str):
        conf_dic = {}
        with open(file_name) as f:
            conf_dic = json.load(f)

        if "bot_token" not in conf_dic:
            raise ValueError("bot_token is not in config file")
        self.bot_token = conf_dic["bot_token"]

        if "consumer_key" not in conf_dic:
            raise ValueError("consumer_key is not in config file")
        self.consumer_key = conf_dic["consumer_key"]

        if "consumer_secret" not in conf_dic:
            raise ValueError("consumer_secret is not in config file")
        self.consumer_secret = conf_dic["consumer_secret"]

        if "access_token" not in conf_dic:
            raise ValueError("access_token is not in config file")
        self.access_token = conf_dic["access_token"]

        if "access_secret" not in conf_dic:
            raise ValueError("access_secret is not in config file")
        self.access_secret = conf_dic["access_secret"]

        expected_keys = [
            "bot_token",
            "consumer_key",
            "consumer_secret",
            "access_token",
            "access_secret",
        ]
        for k in conf_dic.keys():
            if k not in expected_keys:
                raise ValueError(f"Invalid parameter is included (param: {k})")
