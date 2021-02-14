import asyncio
import threading
import time
import re
from typing import List

import discord

from localconfig import LocalConfig
from twbot.botcli import BotClient


class EvalClient(discord.Client):
    def __init__(self, eval_ptns, loop=None):
        super().__init__(loop=loop)

        self.eval_ptn_itr = None
        self.eval_ptn = None
        self.is_no_message_case = True
        self.is_passed = True

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
    while True:
        if eval_cli.is_no_message_case and not eval_cli.is_passed:
            break
        if not eval_cli.is_no_message_case and eval_cli.is_passed:
            break
        if seconds >= timeout_seconds:
            break
        time.sleep(1)
        seconds += 1

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


def eval_send_messages(config: LocalConfig, messages: List[str], patterns, timeout_seconds):
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
    loop.close()

    return eval_cli.is_passed
