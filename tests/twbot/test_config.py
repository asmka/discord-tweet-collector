from pathlib import Path

import pytest

from twbot.config import Config

cpath = Path(__file__).parent


class TestConfig:
    def test_initialize_valid_json_file(self):
        Config(cpath / "config/valid_json_file.json")

    def test_initialize_invalid_file_path(self):
        with pytest.raises(FileNotFoundError):
            Config(cpath / "config/_not_exist_file_name")

    def test_initialize_invalid_json_file(self):
        with pytest.raises(ValueError):
            Config(cpath / "config/invalid_json_file.json")

    def test_initialize_with_no_bot_token_param(self):
        with pytest.raises(ValueError, match=r"bot_token is not in config file"):
            Config(cpath / "config/with_no_bot_token_param.json")

    def test_initialize_with_no_consumer_key_param(self):
        with pytest.raises(ValueError, match=r"consumer_key is not in config file"):
            Config(cpath / "config/with_no_consumer_key_param.json")

    def test_initialize_with_no_consumer_secret_param(self):
        with pytest.raises(ValueError, match=r"consumer_secret is not in config file"):
            Config(cpath / "config/with_no_consumer_secret_param.json")

    def test_initialize_with_no_access_token_param(self):
        with pytest.raises(ValueError, match=r"access_token is not in config file"):
            Config(cpath / "config/with_no_access_token_param.json")

    def test_initialize_with_no_access_secret_param(self):
        with pytest.raises(ValueError, match=r"access_secret is not in config file"):
            Config(cpath / "config/with_no_access_secret_param.json")

    def test_initialize_with_invalid_param(self):
        with pytest.raises(ValueError, match=r"Invalid parameter is included \(param: .+\)"):
            Config(cpath / "config/with_invalid_param.json")
