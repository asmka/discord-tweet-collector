import os
import json

from .exception import TCBotError


class Config:
    def __init__(self, file_name: str):
        conf_dic = {}
        try:
            with open(file_name) as f:
                conf_dic = json.load(f)
        except FileNotFoundError as exc:
            raise TCBotError(f"Failed to open file. file_name: {file_name}") from exc
        except json.JSONDecodeError as exc:
            raise TCBotError(f"Failed to parse config file.") from exc

        if "bot_token" not in conf_dic:
            raise TCBotError("bot_token is not in config file.")
        self.bot_token = conf_dic["bot_token"]

        if "consumer_key" not in conf_dic:
            raise TCBotError("consumer_key is not in config file.")
        self.consumer_key = conf_dic["consumer_key"]

        if "consumer_secret" not in conf_dic:
            raise TCBotError("consumer_secret is not in config file.")
        self.consumer_secret = conf_dic["consumer_secret"]

        if "access_token" not in conf_dic:
            raise TCBotError("access_token is not in config file.")
        self.access_token = conf_dic["access_token"]

        if "access_secret" not in conf_dic:
            raise TCBotError("access_secret is not in config file.")
        self.access_secret = conf_dic["access_secret"]

        if "db_url" not in conf_dic:
            raise TCBotError("db_url is not in config file.")
        self.db_url = conf_dic["db_url"]

        expected_keys = [
            "bot_token",
            "consumer_key",
            "consumer_secret",
            "access_token",
            "access_secret",
            "db_url",
        ]
        for k in conf_dic.keys():
            if k not in expected_keys:
                raise TCBotError(f"Invalid parameter is included. param: {k}")
