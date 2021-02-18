import json

import pytest


class ConfigForTest:
    def __init__(self, file_name: str):
        conf_dic = {}
        with open(file_name) as f:
            conf_dic = json.load(f)

        if "test_bot_token" not in conf_dic:
            raise ValueError("test_bot_token is not in config file")
        self.test_bot_token = conf_dic["test_bot_token"]

        if "eval_bot_token" not in conf_dic:
            raise ValueError("eval_bot_token is not in config file")
        self.eval_bot_token = conf_dic["eval_bot_token"]

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

        if "test_channel_id" not in conf_dic:
            raise ValueError("test_channel_id is not in config file")
        self.test_channel_id = conf_dic["test_channel_id"]

        if "db_url" not in conf_dic:
            raise ValueError("db_url is not in config file")
        self.db_url = conf_dic["db_url"]

        expected_keys = [
            "test_bot_token",
            "eval_bot_token",
            "consumer_key",
            "consumer_secret",
            "access_token",
            "access_secret",
            "test_channel_id",
            "db_url",
        ]
        for k in conf_dic.keys():
            if k not in expected_keys:
                raise ValueError(f"Invalid parameter is included (param: {k})")


def pytest_addoption(parser):
    parser.addoption("--conf", action="store", help="Config file to run test")


@pytest.fixture(scope="session")
def config(pytestconfig):
    file_name = pytestconfig.getoption("conf")
    yield ConfigForTest(file_name)
