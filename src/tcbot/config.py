import os
import json

from .exception import TCBotError


class Config:
    def __init__(self, file_name: str = None):
        if file_name is None:
            self._construct_from_env()
        else:
            self._construct_from_file(file_name)

    def _construct_from_env(self):
        # raise TCBotError("Not implemented")

        BOT_TOKEN_ENV = "BOT_TOKEN"
        CONSUMER_KEY_ENV = "CONSUMER_KEY"
        CONSUMER_SECRET_ENV = "CONSUMER_SECRET"
        ACCESS_TOKEN_ENV = "ACCESS_TOKEN"
        ACCESS_SECRET_ENV = "ACCESS_SECRET"
        DB_URL_ENV = "DB_URL"
        DB_TABLE_ENV = "DB_TABLE"

        EXPECTED_ENVS = (
            BOT_TOKEN_ENV,
            CONSUMER_KEY_ENV,
            CONSUMER_SECRET_ENV,
            ACCESS_TOKEN_ENV,
            ACCESS_SECRET_ENV,
            DB_URL_ENV,
            DB_TABLE_ENV,
        )

        # Check required env exist
        envs = {}
        for env_name in EXPECTED_ENVS:
            env_val = os.getenv(env_name)
            if env_val is None:
                raise TCBotError(f"{env_name} environment is not set.")
            envs[env_name] = env_val

        self.bot_token = envs[BOT_TOKEN_ENV]
        self.consumer_key = envs[CONSUMER_KEY_ENV]
        self.consumer_secret = envs[CONSUMER_SECRET_ENV]
        self.access_token = envs[ACCESS_TOKEN_ENV]
        self.access_secret = envs[ACCESS_SECRET_ENV]
        self.db_url = envs[DB_URL_ENV]
        self.db_table = envs[DB_TABLE_ENV]

    def _construct_from_file(self, file_name):
        conf_dic = {}
        try:
            with open(file_name) as f:
                conf_dic = json.load(f)
        except FileNotFoundError as exc:
            raise TCBotError(f"Failed to open file. file_name: {file_name}") from exc
        except json.JSONDecodeError as exc:
            raise TCBotError(f"Failed to parse config file.") from exc

        BOT_TOKEN_PARAM = "bot_token"
        CONSUMER_KEY_PARAM = "consumer_key"
        CONSUMER_SECRET_PARAM = "consumer_secret"
        ACCESS_TOKEN_PARAM = "access_token"
        ACCESS_SECRET_PARAM = "access_secret"
        DB_URL_PARAM = "db_url"
        DB_TABLE_PARAM = "db_table"

        EXPECTED_PARAMS = (
            BOT_TOKEN_PARAM,
            CONSUMER_KEY_PARAM,
            CONSUMER_SECRET_PARAM,
            ACCESS_TOKEN_PARAM,
            ACCESS_SECRET_PARAM,
            DB_URL_PARAM,
            DB_TABLE_PARAM,
        )

        # Check required parameter exist
        for param in EXPECTED_PARAMS:
            if param not in conf_dic:
                raise TCBotError(f"{param} is not in config file.")

        # Check invalid parameter exist
        for key in conf_dic.keys():
            if key not in EXPECTED_PARAMS:
                raise TCBotError(f"Invalid parameter is included. param: {key}")

        self.bot_token = conf_dic[BOT_TOKEN_PARAM]
        self.consumer_key = conf_dic[CONSUMER_KEY_PARAM]
        self.consumer_secret = conf_dic[CONSUMER_SECRET_PARAM]
        self.access_token = conf_dic[ACCESS_TOKEN_PARAM]
        self.access_secret = conf_dic[ACCESS_SECRET_PARAM]
        self.db_url = conf_dic[DB_URL_PARAM]
        self.db_table = conf_dic[DB_TABLE_PARAM]
