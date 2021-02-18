import asyncio
import re
import shlex
from typing import List, Tuple

import discord
import tweepy

from .logger import logger
from .chwriter import send_info, send_error
from .exception import TCBotError
from .twstream import Monitor, TweetStream


class BotClient(discord.Client):
    def __init__(
        self, consumer_key, consumer_secret, access_token, access_secret, loop=None
    ):
        super().__init__(loop=loop)
        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_secret)
        api = tweepy.API(auth)
        if api.verify_credentials() == False:
            raise ValueError("[ERROR] Failed to authenticate twitter api.")

        self.api = api

        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.access_token = access_token
        self.access_secret = access_secret

        self.stream = None
        self.stream_thread = None

        self.monitors_table = {}
        self.monitor_users = set()
        self.user_owners = {}

        self.monitor_db = None

        self.loop = loop

    def _enumerate_monitors(self):
        enum_monitors = []
        for monitors_dict in self.monitors_table.values():
            for monitor in monitors_dict.values():
                enum_monitors.append(monitor)

        return enum_monitors

    def _sync_close_stream(self):
        if not self.stream:
            raise TCBotError(
                "Called _sync_close_stream() even though stream is not created."
            )

        self.stream.disconnect()
        # Wait stream blocking I/O thread
        self.stream_thread.join()

    def _add(self, channel, args: List[str]) -> Tuple[str, str]:
        screen_name = args[0] if len(args) > 0 else None
        match_ptn = args[1] if len(args) > 1 else None

        if not screen_name:
            raise TCBotError("アカウント名が指定されていません．")

        # Raise exception if the account is not exist
        try:
            status = self.api.get_user(screen_name=screen_name)
        except tweepy.TweepError as exc:
            raise TCBotError(f"存在しないアカウントです．アカウント名: {screen_name}") from exc
        else:
            tw_user_id = status.id

        # Raise exception if the regular expression is invalid
        if match_ptn:
            try:
                re.compile(match_ptn)
            except re.error as exc:
                raise TCBotError(f"正規表現が不正です．正規表現: {match_ptn}") from exc

        # Raise exception if the account is already registered
        if channel.id in self.monitors_table:
            if screen_name in self.monitors_table[channel.id]:
                raise TCBotError(f"既に登録されているアカウントです．アカウント名: {screen_name}")
        else:
            self.monitors_table[channel.id] = {}

        # Update management data
        monitor = Monitor(channel, tw_user_id, match_ptn)
        self.monitors_table[channel.id][screen_name] = monitor
        self.monitor_db.add(channel.id, tw_user_id, match_ptn)

        if tw_user_id not in self.monitor_users:
            self.monitor_users.add(tw_user_id)

        if screen_name not in self.user_owners:
            self.user_owners[screen_name] = set()
        self.user_owners[screen_name].add(channel.id)

        # Reconstruct stream to run just one stream
        if self.stream:
            self._sync_close_stream()

        self.stream = TweetStream(
            self.consumer_key,
            self.consumer_secret,
            self.access_token,
            self.access_secret,
            self._enumerate_monitors(),
            self.loop,
        )
        self.stream_thread = self.stream.filter(
            follow=list(map(str, self.monitor_users)), threaded=True
        )

        return screen_name, match_ptn

    async def close(self):
        if not self.is_ready():
            raise Exception("Called close() before client is ready.")

        await super().close()

        # self.bot_writer.close()
        if self.stream:
            self._sync_close_stream()

    async def on_message(self, msg):
        if msg.author == self.user:
            return

        # Parse command line
        try:
            cmdlist = shlex.split(msg.content)
        except:
            logger.debug(f"Failed to parse msg.content (msg.content: {msg.content})")
            return

        maincmd = cmdlist[0] if len(cmdlist) > 0 else None
        subcmd = cmdlist[1] if len(cmdlist) > 1 else None

        # Do nothing when message has no '!tc'
        if maincmd != "!tc":
            return

        # Receive add command
        if subcmd == "add":
            try:
                user_name, match_ptn = self._add(msg.channel, cmdlist[2:])
            except TCBotError as exc:
                logger.exception("Catch Exception")
                logger.error(str(exc))
                await send_error(msg.channel, str(exc))
            else:
                await send_info(
                    msg.channel,
                    f"アカウントの登録に成功しました．アカウント名: {user_name}, 正規表現: {repr(match_ptn)}",
                )

        ## Receive remove command
        # elif subcmd == "remove":
        #    screen_name = cmdlist[2] if len(cmdlist) > 2 else None

        #    if not screen_name:
        #        emsg = f"[ERROR] アカウント名が指定されていません"
        #        await msg.channel.send(emsg)
        #        return

        #    try:
        #        self.bot_writer.remove(msg.channel, screen_name)
        #    except Exception as exc:
        #        logger.exception("[ERROR] Recieve Exception")
        #        logger.error(exc)
        #        await msg.channel.send(exc)
        #        return

        #    imsg = f"[INFO] アカウントの削除に成功しました (アカウント名: {screen_name})"
        #    await msg.channel.send(imsg)

        ## Receive list command
        # elif subcmd == "list":
        #    imsg = f"[INFO] 登録済みのアカウントはありません"
        #    if cid in self.bot_writer.user_list and self.bot_writer.user_list[cid]:
        #        imsg = f"[INFO] 登録済みのアカウント:"
        #        for screen_name in self.bot_writer.user_list[cid]:
        #            imsg += f"\r・{screen_name}"
        #            if self.bot_writer.writers[(cid, screen_name)].match_ptn:
        #                imsg += f" (正規表現: {repr(self.bot_writer.writers[(cid, screen_name)].match_ptn)})"
        #    await msg.channel.send(imsg)

        ## Receive help command
        # elif subcmd == "help":
        #    imsg = f"[INFO] コマンド仕様:"
        #    imsg += f"\r・!tw add <アカウント名> [<正規表現パターン>]: 収集対象のアカウントを登録"
        #    imsg += f'\r　例: !tw add moujaatumare "#mildom" (#mildomを含むツイートのみ抽出)'
        #    imsg += f"\r・!tw remove <アカウント名>: 登録済みのアカウントを削除"
        #    imsg += f"\r・!tw list : 登録済みのアカウントの一覧表示"
        #    imsg += f"\r・!tw help : コマンド仕様を表示"
        #    await msg.channel.send(imsg)

        ## Receive invalid command
        # else:
        #    emsg = f'[ERROR] コマンドが不正です ("!tw help"を参照)'
        #    logger.error(emsg)
        #    await msg.channel.send(emsg)
