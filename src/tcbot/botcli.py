import asyncio
import re
import shlex
from typing import List, Tuple

import discord
import tweepy

from .monitordb import MonitorDB
from .logger import logger
from .chwriter import send_info, send_error
from .exception import TCBotError
from .twauth import TwitterAuth
from .tcstream import TweetCollectStream


class BotClient(discord.Client):
    def __init__(
        self,
        monitor_db: MonitorDB,
        tw_auth: TwitterAuth,
        loop=None,
    ):

        self.monitor_db = monitor_db
        self.tw_auth = tw_auth
        self.loop = loop

        self.stream = TweetCollectStream(
            self.tw_auth,
            self.monitor_db,
            self.loop,
        )

        super().__init__(loop=loop)

    def _add(self, channel, args: List[str]) -> Tuple[str, str]:
        screen_name = args[0] if len(args) > 0 else None
        match_ptn = args[1] if len(args) > 1 else None

        if not screen_name:
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
        if self.monitor_db.select(channel.id, twitter_id):
            raise TCBotError(f"既に登録されているアカウントです．アカウント名: {screen_name}")

        # Update database
        self.monitor_db.insert(channel.id, twitter_id, screen_name, match_ptn)

        # Reconstruct stream to run just one stream
        self.stream.resume()

        return screen_name, match_ptn

    async def close(self):
        if not self.is_ready():
            raise Exception("Called close() before client is ready.")

        await super().close()
        self.stream.disconnect()
        self.stream = None

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
