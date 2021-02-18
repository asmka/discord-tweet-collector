from typing import List, Dict

import discord
import pytest

from tcbot.botcli import BotClient

from evalcli import eval_send_messages


class MockMonitorDB:
    def __init__(self):
        self.monitors: List[Dict] = []

    def add(self, channel_id, tw_user_id, match_ptn):
        self.monitors.append(
            {"channel_id": channel_id, "tw_user_id": tw_user_id, "match_ptn": match_ptn}
        )


class TestBotClient:
    def test_initialize_invalid_consumer_key(self, config):
        with pytest.raises(ValueError, match=r"Failed to authenticate twitter api\."):
            BotClient(
                "INVALID_CONSUMER_KEY",
                config.consumer_secret,
                config.access_token,
                config.access_secret,
            )

    def test_initialize_invalid_consumer_secret(self, config):
        with pytest.raises(ValueError, match=r"Failed to authenticate twitter api\."):
            BotClient(
                config.consumer_key,
                "INVALID_CONSUMER_SECRET",
                config.access_token,
                config.access_secret,
            )

    def test_initialize_invalid_access_token(self, config):
        with pytest.raises(ValueError, match=r"Failed to authenticate twitter api\."):
            BotClient(
                config.consumer_key,
                config.consumer_secret,
                "INVALID_ACCESS_TOKEN",
                config.access_secret,
            )

    def test_initialize_invalid_access_secret(self, config):
        with pytest.raises(ValueError, match=r"Failed to authenticate twitter api\."):
            BotClient(
                config.consumer_key,
                config.consumer_secret,
                config.access_token,
                "INVALID_ACCESS_SECRET",
            )

    def test_invalid_main_command(self, config):
        assert eval_send_messages(config, ["!tcc add"], [], 5)

    def test_add_command_exist_account(self, config):
        monitor_db = MockMonitorDB()
        assert eval_send_messages(
            config,
            ["!tc add tt4bot"],
            [r"^\[INFO\] アカウントの登録に成功しました．アカウント名: tt4bot, 正規表現: None$"],
            5,
        )

    def test_add_command_not_exist_account(self, config):
        assert eval_send_messages(
            config,
            ["!tc add NON_EXSITING_ACCOUNT_202102211456"],
            [r"^\[ERROR\] 存在しないアカウントです．アカウント名: NON_EXSITING_ACCOUNT_202102211456$"],
            5,
        )

    def test_add_command_already_added_account(self, config):
        assert eval_send_messages(
            config,
            ["!tc add tt4bot", "!tc add tt4bot"],
            [
                r"^\[INFO\] アカウントの登録に成功しました．アカウント名: tt4bot, 正規表現: None$",
                r"^\[ERROR\] 既に登録されているアカウントです．アカウント名: tt4bot$",
            ],
            5,
        )
