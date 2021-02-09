import asyncio
import threading
import json

import pytest
import discord

from twbot.botcli import BotClient


class TestConfig:
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

        if "test_channel_id" not in conf_dic:
            raise ValueError("test_channel_id is not in config file")
        self.test_channel_id = conf_dic["test_channel_id"]

        expected_keys = [
            "bot_token",
            "consumer_key",
            "consumer_secret",
            "access_token",
            "access_secret",
            "test_channel_id",
        ]
        for k in conf_dic.keys():
            if k not in expected_keys:
                raise ValueError(f"Invalid parameter is included (param: {k})")


@pytest.fixture()
def config(pytestconfig):
    file_name = pytestconfig.getoption("conf")
    return TestConfig(file_name)


@pytest.fixture()
def bot_cli(config):
    bot_cli = BotClient(
        config.consumer_key,
        config.consumer_secret,
        config.access_token,
        config.access_secret,
    )
    return bot_cli


def run_bot(loop, client, token):
    future = asyncio.run_coroutine_threadsafe(
        client.start(token),
        loop,
    )
    future.result()


def send_message(loop, client, channel_id, message):
    while not client.is_ready():
        pass

    future = asyncio.run_coroutine_threadsafe(client.fetch_channel(channel_id), loop)
    channel = future.result()

    future = asyncio.run_coroutine_threadsafe(
        channel.send(message),
        loop,
    )
    future.result()


def test_recieve_invalid_main_command(self, config, bot_cli):
    loop = asyncio.get_event_loop()

    t1 = threading.Thread(
        target=run_bot,
        args=(
            loop,
            bot_cli,
            config.bot_token,
        ),
    )
    t2 = threading.Thread(
        target=send_message,
        args=(
            loop,
            bot_cli,
            config.test_channel_id,
            "!twx add",
        ),
    )
    t1.start()
    t2.start()

    loop.run_forever()


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

    def test_recieve_invalid_main_command(self, config, bot_cli):
        loop = asyncio.get_event_loop()

        t1 = threading.Thread(
            target=run_bot,
            args=(
                loop,
                bot_cli,
                config.bot_token,
            ),
        )
        t2 = threading.Thread(
            target=send_message,
            args=(
                loop,
                bot_cli,
                config.test_channel_id,
                "!twx add",
            ),
        )
        t1.start()
        t2.start()

        loop.run_forever()
        # await asyncio.sleep(5)
        # bot_cli.close()
