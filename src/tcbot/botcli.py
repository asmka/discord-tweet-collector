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
HELP_CMD = "help"


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
        if monitor_users:
            self.stream.filter(follow=monitor_users, threaded=True)

    async def _send_message(self, channel_id: int, msg: str):
        channel = self.get_channel(channel_id)
        await channel.send(msg)

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
        if self.monitor_db.select(channel_id=channel_id, twitter_id=twitter_id):
            raise TCBotError(f"既に登録されているアカウントです．アカウント名: {screen_name}")

        # Update database
        self.monitor_db.insert(channel_id, twitter_id, match_ptn)

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
        if not self.monitor_db.select(channel_id=channel_id, twitter_id=twitter_id):
            raise TCBotError(f"登録されていないアカウントです．アカウント名: {screen_name}")

        # Update database
        self.monitor_db.delete(channel_id, twitter_id)

        # Rerun stream
        self._resume_stream()

        return screen_name

    def _list(self, channel_id: int) -> List[Tuple[str, str]]:
        monitor_users = []

        monitors = self.monitor_db.select(channel_id=channel_id)
        for m in monitors:
            twitter_id = m["twitter_id"]
            match_ptn = m["match_ptn"]
            twitter_name = self.tw_auth.api.get_user(id=twitter_id).screen_name
            monitor_users.append((twitter_name, match_ptn))

        return monitor_users

    async def close(self):
        if not self.is_ready():
            raise Exception("Called close() before client is ready.")

        if self.stream:
            self.stream.disconnect()
            self.stream = None

        await super().close()

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

        # Do nothing when message has no MAIN_CMD
        if maincmd != MAIN_CMD:
            return

        # Receive ADD_CMD
        if subcmd == ADD_CMD:
            try:
                twitter_name, match_ptn = self._add(channel_id, cmdlist[2:])
            except TCBotError as exc:
                logger.exception("Catch Exception")
                logger.error(str(exc))
                await self.send_error(channel_id, str(exc))
            else:
                await self.send_info(
                    channel_id,
                    f"アカウントの登録に成功しました．アカウント名: {twitter_name}, 正規表現: {repr(match_ptn)}",
                )
        # Receive REMOVE_CMD
        elif subcmd == REMOVE_CMD:
            try:
                twitter_name = self._remove(channel_id, cmdlist[2:])
            except TCBotError as exc:
                logger.exception("Catch Exception")
                logger.error(str(exc))
                await self.send_error(channel_id, str(exc))
            else:
                text = f"アカウントの削除に成功しました．アカウント名: {twitter_name}"
                await self.send_info(channel_id, text)
        # Receive LIST_CMD
        elif subcmd == LIST_CMD:
            try:
                monitor_users: List[Tuple[str, str]] = self._list(channel_id)
            except TCBotError as exc:
                logger.exception("Catch Exception")
                logger.error(str(exc))
                await self.send_error(channel_id, str(exc))
            else:
                if monitor_users:
                    text = f"登録済みのアカウント:"
                    for twitter_name, match_ptn in monitor_users:
                        text += f"\r・アカウント名: {twitter_name}, 正規表現: {repr(match_ptn)}"
                    await self.send_info(channel_id, text)
                else:
                    text = f"登録済みのアカウントはありません．"
                    await self.send_info(channel_id, text)
        # Receive HELP_CMD
        elif subcmd == HELP_CMD:
            text = (
                "コマンド仕様:"
                + f"\r・{MAIN_CMD} {ADD_CMD} <アカウント名> [<正規表現パターン>]: 収集対象のアカウントを登録"
                + f"\r　例: {MAIN_CMD} {ADD_CMD} moujaatumare %s" % repr(r"mildom\.com")
                + f"\r　動作: 'mildom.com'を含むなるおのツイートのみ抽出（短縮リンクは展開）"
                + f"\r・{MAIN_CMD} {REMOVE_CMD} <アカウント名>: 登録済みのアカウントを削除"
                + f"\r・{MAIN_CMD} {LIST_CMD}: 登録済みのアカウントの一覧表示"
                + f"\r・{MAIN_CMD} {HELP_CMD}: コマンド仕様を表示"
            )
            await self.send_info(channel_id, text)
        # Receive invalid command
        else:
            text = f"コマンドが不正です．'{MAIN_CMD} {HELP_CMD}'を参照してください．"
            logger.error(text)
            await self.send_error(channel_id, text)
