import asyncio
import re
import shlex
from typing import List, Tuple

import discord
import tweepy

from .monitordb import MonitorDB
from .logger import logger
from .exception import TCBotError
from .twauth import TwitterAuth
from .tcstream import TweetCollectStream


MAIN_CMD = "!tc"
ADD_CMD = "add"
REMOVE_CMD = "remove"
LIST_CMD = "list"


class BotClient(discord.Client):
    def __init__(
        self,
        monitor_db: MonitorDB,
        tw_auth: TwitterAuth,
        loop=None,
    ):
        if loop is None:
            self.loop = asyncio.get_event_loop()
        else:
            self.loop = loop

        self.monitor_db = monitor_db
        self.tw_auth = tw_auth
        self.stream = None

        super().__init__(loop=self.loop)

    def _resume_stream(self):
        # Close running stream before
        if self.stream:
            self.stream.disconnect()

        self.stream = TweetCollectStream(
            self,
            self.tw_auth,
            self.monitor_db,
            self.loop,
        )
        monitor_users = list(map(str, self.stream.user_id_map.keys()))
        self.stream.filter(follow=monitor_users, threaded=True)

    def _add(self, channel_id: int, args: List[str]) -> Tuple[str, str]:
        screen_name = args[0] if len(args) > 0 else None
        match_ptn = args[1] if len(args) > 1 else None

        if screen_name is None:
            raise TCBotError("アカウント名が指定されていません．")

        # Raise exception if the account is not exist
        try:
            status = self.tw_auth.api.get_user(screen_name=screen_name)
        except tweepy.TweepError as exc:
            raise TCBotError(f"存在しないアカウントです．アカウント名: {screen_name}") from exc
        else:
            twitter_id = status.id

        # Raise exception if the regular expression is invalid
        if match_ptn:
            try:
                re.compile(match_ptn)
            except re.error as exc:
                raise TCBotError(f"正規表現が不正です．正規表現: {match_ptn}") from exc

        # Raise exception if the account is already registered
        if self.monitor_db.select(channel_id, twitter_id):
            raise TCBotError(f"既に登録されているアカウントです．アカウント名: {screen_name}")

        # Update database
        self.monitor_db.insert(channel_id, twitter_id, screen_name, match_ptn)

        # Rerun stream
        self._resume_stream()

        return screen_name, match_ptn

    def _remove(self, channel_id: int, args: List[str]) -> str:
        screen_name = args[0] if len(args) > 0 else None

        if screen_name is None:
            raise TCBotError("アカウント名が指定されていません．")

        # Raise exception if the account is not exist
        try:
            status = self.tw_auth.api.get_user(screen_name=screen_name)
        except tweepy.TweepError as exc:
            raise TCBotError(f"存在しないアカウントです．アカウント名: {screen_name}") from exc
        else:
            twitter_id = status.id

        # Raise exception if the account is not registered
        if not self.monitor_db.select(channel_id, twitter_id):
            raise TCBotError(f"登録されていないアカウントです．アカウント名: {screen_name}")

        # Update database
        self.monitor_db.delete(channel_id, twitter_id)

        # Rerun stream
        self._resume_stream()

        return screen_name

    async def close(self):
        if not self.is_ready():
            raise Exception("Called close() before client is ready.")

        if self.stream:
            self.stream.disconnect()
            self.stream = None

        await super().close()

    async def _send_message(self, channel_id: int, msg: str):
        channel = self.get_channel(channel_id)
        await channel.send(msg)

    async def send_info(self, channel_id: int, msg: str):
        await self._send_message(channel_id, f"[INFO] {msg}")

    async def send_error(self, channel_id: int, msg: str):
        await self._send_message(channel_id, f"[ERROR] {msg}")

    async def on_ready(self):
        self._resume_stream()

    async def on_message(self, msg: discord.Message):
        if msg.author == self.user:
            return

        channel_id = msg.channel.id
        content = msg.content

        # Parse command line
        try:
            cmdlist = shlex.split(msg.content)
        except:
            logger.debug(f"Failed to parse content. content: {content})")
            return

        maincmd = cmdlist[0] if len(cmdlist) > 0 else None
        subcmd = cmdlist[1] if len(cmdlist) > 1 else None

        # Do nothing when message has no '!tc'
        if maincmd != MAIN_CMD:
            return

        # Receive add command
        if subcmd == ADD_CMD:
            try:
                user_name, match_ptn = self._add(channel_id, cmdlist[2:])
            except TCBotError as exc:
                logger.exception("Catch Exception")
                logger.error(str(exc))
                await self.send_error(channel_id, str(exc))
            else:
                await self.send_info(
                    channel_id,
                    f"アカウントの登録に成功しました．アカウント名: {user_name}, 正規表現: {repr(match_ptn)}",
                )
        # Receive remove command
        elif subcmd == REMOVE_CMD:
            try:
                user_name = self._remove(channel_id, cmdlist[2:])
            except TCBotError as exc:
                logger.exception("Catch Exception")
                logger.error(str(exc))
                await self.send_error(channel_id, str(exc))
            else:
                await self.send_info(
                    channel_id,
                    f"アカウントの削除に成功しました．アカウント名: {user_name}",
                )

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
