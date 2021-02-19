import asyncio
import threading
import time
import re
from typing import List

import tweepy
import discord

from tcbot.twauth import TwitterAuth
from tcbot.monitordb import MonitorDB
from tcbot.botcli import BotClient


class EvalClient(discord.Client):
    def __init__(self, eval_ptns, loop=None):
        super().__init__(loop=loop)

        self.eval_ptn_itr = None
        self.eval_ptn = None
        self.is_no_message_case = True
        self.is_passed = True
        self.is_evaluating = True

        if eval_ptns:
            self.eval_ptn_itr = iter(eval_ptns)
            self.eval_ptn = next(self.eval_ptn_itr)
            self.is_no_message_case = False
            self.is_passed = False

    async def on_message(self, msg):
        if msg.author == self.user:
            return

        if self.is_no_message_case:
            self.is_passed = False
            self.is_evaluating = False
            return

        if re.search(self.eval_ptn, msg.content):
            try:
                self.eval_ptn = next(self.eval_ptn_itr)
            except StopIteration:
                self.is_passed = True
                self.is_evaluating = False


def run_bot(client: discord.Client, token: str, loop):
    future = asyncio.run_coroutine_threadsafe(client.start(token), loop)
    future.result()


def stop_bot(client: discord.Client, loop):
    future = asyncio.run_coroutine_threadsafe(client.close(), loop)
    future.result()


def send_messages(
    client: discord.Client,
    channel_id: int,
    messages: List[str],
    loop,
):
    channel = client.get_channel(int(channel_id))
    for msg in messages:
        future = asyncio.run_coroutine_threadsafe(channel.send(msg), loop)
        future.result()


def eval_send_messages(
    config,
    monitor_db: MonitorDB,
    messages: List[str],
    patterns: List[str],
    timeout_seconds: int,
):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    tw_auth = TwitterAuth(
        config.consumer_key,
        config.consumer_secret,
        config.access_token,
        config.access_secret,
    )

    test_cli = BotClient(
        monitor_db,
        tw_auth,
        loop=loop,
    )
    eval_cli = EvalClient(patterns, loop=loop)

    # Run event loop on another thread
    loop_thread = threading.Thread(target=loop.run_forever, name="loop_thread")
    loop_thread.start()

    # Run bots on other threads
    test_bot_thread = threading.Thread(
        target=run_bot,
        name="test_bot_thread",
        args=(test_cli, config.test_bot_token, loop),
    )
    eval_bot_thread = threading.Thread(
        target=run_bot,
        name="eval_bot_thread",
        args=(eval_cli, config.eval_bot_token, loop),
    )
    test_bot_thread.start()
    eval_bot_thread.start()

    # Wait bots are ready
    while True:
        if test_cli.is_ready() and eval_cli.is_ready():
            break

    send_messages(eval_cli, config.test_channel_id, messages, loop)

    # Wait finish evaluating
    seconds = 0
    while eval_cli.is_evaluating and seconds < timeout_seconds:
        time.sleep(1)
        seconds += 1

    stop_bot(test_cli, loop)
    stop_bot(eval_cli, loop)

    # Wait bots are closed
    while True:
        if test_cli.is_closed() and eval_cli.is_closed():
            break

    # Wait run_bot threads are finished
    test_bot_thread.join()
    eval_bot_thread.join()

    # Close event loop and thread
    loop.call_soon_threadsafe(loop.stop)
    loop_thread.join()
    loop.close()

    return eval_cli.is_passed
