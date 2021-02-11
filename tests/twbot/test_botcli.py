import asyncio
import threading
import concurrent.futures
import time
import re
import json

import pytest
import discord

from twbot.botcli import BotClient


class LocalConfig:
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

        expected_keys = [
            "test_bot_token",
            "eval_bot_token",
            "consumer_key",
            "consumer_secret",
            "access_token",
            "access_secret",
            "test_channel_id",
        ]
        for k in conf_dic.keys():
            if k not in expected_keys:
                raise ValueError(f"Invalid parameter is included (param: {k})")


class EvalClient(discord.Client):
    def __init__(self, eval_ptn):
        super().__init__()
        self.eval_ptn = eval_ptn
        self.is_called_on_ready = False
        self.is_passed = False

    async def on_ready(self):
        #print(f"[DEBUG] on_ready ({threading.current_thread().getName()})")
        self.is_called_on_ready = True

    async def on_message(self, message):
        #print(f"[DEBUG] on_message ({threading.current_thread().getName()})")
        if re.search(self.eval_ptn, message.content):
            self.is_passed = True


def run_bot(client: discord.Client, token: str, loop):
    #print(f"[DEBUG] Called run_bot ({threading.current_thread().getName()})")
    future = asyncio.run_coroutine_threadsafe(client.start(token), loop)
    future.result()


def stop_bot(client: discord.Client, loop):
    #print(f"[DEBUG] Called stop_bot ({threading.current_thread().getName()})")
    future = asyncio.run_coroutine_threadsafe(client.close(), loop)
    future.result()


def send_message(client: discord.Client, channel_id: int, message: str, loop):
    #print(f"[DEBUG] Called send_message ({threading.current_thread().getName()})")
    while not client.is_called_on_ready:
        pass
    channel = client.get_channel(int(channel_id))
    future = asyncio.run_coroutine_threadsafe(channel.send(message), loop)
    future.result()


def eval_and_close_loop(bot_cli, eval_cli, timeout_seconds, loop):
    #print(f"[DEBUG] Called eval_and_close_loop ({threading.current_thread().getName()})")
    seconds = 0
    while True:
        if eval_cli.is_passed or seconds >= timeout_seconds:
            break
        time.sleep(1)
        seconds += 1

    future = asyncio.run_coroutine_threadsafe(bot_cli.close(), loop)
    future.result()
    future = asyncio.run_coroutine_threadsafe(eval_cli.close(), loop)
    future.result()
    loop.call_soon_threadsafe(loop.stop)
    #loop.call_soon_threadsafe(loop.close)


def eval_send_message_and_recieve_pattern(config, message, pattern, timeout_seconds):
    #print(f"[DEBUG] Called eval_send_message_and_recieve_pattern ({threading.current_thread().getName()})")
    bot_cli = BotClient(
        config.consumer_key,
        config.consumer_secret,
        config.access_token,
        config.access_secret,
    )
    eval_cli = EvalClient(pattern)

    loop = asyncio.get_event_loop()

    t1 = threading.Thread(
        target=run_bot,
        args=(bot_cli, config.test_bot_token, loop),
    )
    t2 = threading.Thread(
        target=run_bot,
        args=(eval_cli, config.eval_bot_token, loop),
    )
    t3 = threading.Thread(
        target=send_message,
        args=(eval_cli, config.test_channel_id, message, loop),
    )
    t4 = threading.Thread(
        target=eval_and_close_loop,
        args=(bot_cli, eval_cli, timeout_seconds, loop),
    )
    t1.start()
    t2.start()
    t3.start()
    t4.start()

    loop.run_forever()
    loop.close()

    return eval_cli.is_passed


@pytest.fixture()
def config(pytestconfig):
    file_name = pytestconfig.getoption("conf")
    return LocalConfig(file_name)


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

    def test_recieve_invalid_main_command(self, config):
        assert (
            eval_send_message_and_recieve_pattern(
                config, "!tw add edaisgod2525", r"\[INFO\] アカウントの登録に成功しました", 5
            )
            == True
        )
