import asyncio
import threading
import time
import re
import json
from typing import List

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
    def __init__(self, eval_ptns, loop=None):
        super().__init__(loop=loop)

        self.eval_ptn_itr = None
        self.eval_ptn = None
        self.is_no_message_case = True
        self.is_passed = None

        if eval_ptns:
            self.eval_ptn_itr = iter(eval_ptns)
            self.eval_ptn = next(self.eval_ptn_itr)
            self.is_no_message_case = False

    async def on_message(self, msg):
        if msg.author == self.user:
            return

        if self.is_no_message_case:
            self.is_passed = False
            return

        if re.search(self.eval_ptn, msg.content):
            try:
                self.eval_ptn = next(self.eval_ptn_itr)
            except StopIteration:
                self.is_passed = True


def run_bot(client: discord.Client, token: str, loop):
    future = asyncio.run_coroutine_threadsafe(client.start(token), loop)
    future.result()


def stop_bot(client: discord.Client, loop):
    # Wait until bot is ready
    while not client.is_ready():
        pass
    future = asyncio.run_coroutine_threadsafe(client.close(), loop)
    future.result()

    # Wait until bot is closed
    while not client.is_closed():
        pass


def wait_test_and_stop_bots(
    test_cli: BotClient, eval_cli: EvalClient, timeout_seconds: int, loop
):
    # Evaluate test case
    seconds = 0
    while eval_cli.is_passed is None and seconds < timeout_seconds:
        time.sleep(1)
        seconds += 1

    # In case of getting no messages
    if eval_cli.is_passed is None:
        eval_cli.is_passed = True

    # Wait test_cli on_message process with itself
    time.sleep(1)

    # Stop bots and loop
    stop_bot(test_cli, loop)
    stop_bot(eval_cli, loop)


def send_messages(
    test_cli: BotClient,
    eval_cli: EvalClient,
    channel_id: int,
    messages: List[str],
    loop,
):
    # Wait bots are ready
    while not (test_cli.is_ready() and eval_cli.is_ready()):
        pass

    # Send message
    channel = eval_cli.get_channel(int(channel_id))
    for msg in messages:
        future = asyncio.run_coroutine_threadsafe(channel.send(msg), loop)
        future.result()


def eval_send_messages(config, messages: List[str], patterns, timeout_seconds):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    test_cli = BotClient(
        config.consumer_key,
        config.consumer_secret,
        config.access_token,
        config.access_secret,
        loop=loop,
    )
    eval_cli = EvalClient(patterns, loop=loop)

    t1 = threading.Thread(
        target=run_bot,
        args=(test_cli, config.test_bot_token, loop),
    )
    t2 = threading.Thread(
        target=run_bot,
        args=(eval_cli, config.eval_bot_token, loop),
    )
    t3 = threading.Thread(
        target=send_messages,
        args=(
            test_cli,
            eval_cli,
            config.test_channel_id,
            messages,
            loop,
        ),
    )
    t4 = threading.Thread(
        target=wait_test_and_stop_bots,
        args=(
            test_cli,
            eval_cli,
            timeout_seconds,
            loop,
        ),
    )

    loop_thread = threading.Thread(target=loop.run_forever)
    loop_thread.start()

    t1.start()
    t2.start()
    t3.start()
    t4.start()

    t1.join()
    t2.join()
    t3.join()
    t4.join()

    loop.stop()
    loop_thread.join()

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

    def test_invalid_main_command(self, config):
        assert eval_send_messages(config, ["!tww add"], [], 5)

    def test_add_command_exist_account(self, config):
        assert eval_send_messages(
            config,
            ["!tw add edaisgod2525"],
            [r"^\[INFO\] アカウントの登録に成功しました．アカウント名: edaisgod2525, 正規表現: None$"],
            5,
        )

    def test_add_command_not_exist_account(self, config):
        assert eval_send_messages(
            config,
            ["!tw add NON_EXSITING_ACCOUNT_202102211456"],
            [r"^\[ERROR\] 存在しないアカウントです．アカウント名: NON_EXSITING_ACCOUNT_202102211456$"],
            5,
        )

    def test_add_command_already_added_account(self, config):
        assert eval_send_messages(
            config,
            ["!tw add edaisgod2525", "!tw add edaisgod2525"],
            [
                r"^\[INFO\] アカウントの登録に成功しました．アカウント名: edaisgod2525, 正規表現: None$",
                r"^\[ERROR\] 既に登録されているアカウントです．アカウント名: edaisgod2525$",
            ],
            5,
        )
