from pathlib import Path

import pytest

from tcbot.exception import TCBotError
from tcbot.config import Config

cpath = Path(__file__).parent


class TestConfig:
    def test_initialize_valid_json_file(self):
        Config(cpath / "config/valid_json_file.json")

    def test_initialize_invalid_file_path(self):
        with pytest.raises(
            TCBotError,
            match=r"^Failed to open file\. file_name: "
            + str(cpath / "config/_not_exist_file_name")
            + r"$",
        ):
            Config(cpath / "config/_not_exist_file_name")

    def test_initialize_invalid_json_file(self):
        with pytest.raises(TCBotError, match=r"Failed to parse config file."):
            Config(cpath / "config/invalid_json_file.json")

    def test_initialize_with_no_bot_token_param(self):
        with pytest.raises(TCBotError, match=r"^bot_token is not in config file\.$"):
            Config(cpath / "config/with_no_bot_token_param.json")

    def test_initialize_with_no_consumer_key_param(self):
        with pytest.raises(TCBotError, match=r"^consumer_key is not in config file\.$"):
            Config(cpath / "config/with_no_consumer_key_param.json")

    def test_initialize_with_no_consumer_secret_param(self):
        with pytest.raises(
            TCBotError, match=r"^consumer_secret is not in config file\.$"
        ):
            Config(cpath / "config/with_no_consumer_secret_param.json")

    def test_initialize_with_no_access_token_param(self):
        with pytest.raises(TCBotError, match=r"^access_token is not in config file\.$"):
            Config(cpath / "config/with_no_access_token_param.json")

    def test_initialize_with_no_access_secret_param(self):
        with pytest.raises(
            TCBotError, match=r"^access_secret is not in config file\.$"
        ):
            Config(cpath / "config/with_no_access_secret_param.json")

    def test_initialize_with_no_db_url_param(self):
        with pytest.raises(TCBotError, match=r"^db_url is not in config file\.$"):
            Config(cpath / "config/with_no_db_url_param.json")

    def test_initialize_with_invalid_param(self):
        with pytest.raises(
            TCBotError, match=r"Invalid parameter is included. param: .+$"
        ):
            Config(cpath / "config/with_invalid_param.json")
