import json

import pytest

from tcbot.exception import TCBotError


class ConfigForTest:
    def __init__(self, file_name: str):
        conf_dic = {}
        with open(file_name) as f:
            conf_dic = json.load(f)

        TEST_BOT_TOKEN_PARAM = "test_bot_token"
        EVAL_BOT_TOKEN_PARAM = "eval_bot_token"
        TEST_CHANNEL_ID = "test_channel_id"
        CONSUMER_KEY_PARAM = "consumer_key"
        CONSUMER_SECRET_PARAM = "consumer_secret"
        ACCESS_TOKEN_PARAM = "access_token"
        ACCESS_SECRET_PARAM = "access_secret"
        DB_URL_PARAM = "db_url"
        DB_TABLE_PARAM = "db_table"

        EXPECTED_PARAMS = (
            TEST_BOT_TOKEN_PARAM,
            EVAL_BOT_TOKEN_PARAM,
            TEST_CHANNEL_ID,
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

        self.test_bot_token = conf_dic[TEST_BOT_TOKEN_PARAM]
        self.eval_bot_token = conf_dic[EVAL_BOT_TOKEN_PARAM]
        self.test_channel_id = conf_dic[TEST_CHANNEL_ID]
        self.consumer_key = conf_dic[CONSUMER_KEY_PARAM]
        self.consumer_secret = conf_dic[CONSUMER_SECRET_PARAM]
        self.access_token = conf_dic[ACCESS_TOKEN_PARAM]
        self.access_secret = conf_dic[ACCESS_SECRET_PARAM]
        self.db_url = conf_dic[DB_URL_PARAM]
        self.db_table = conf_dic[DB_TABLE_PARAM]

        # Check invalid parameter exist
        for key in conf_dic.keys():
            if key not in EXPECTED_PARAMS:
                raise TCBotError(f"Invalid parameter is included. param: {key}")


def pytest_addoption(parser):
    parser.addoption("--conf", action="store", help="Config file to run test")


@pytest.fixture(scope="session")
def config(pytestconfig):
    file_name = pytestconfig.getoption("conf")
    yield ConfigForTest(file_name)
