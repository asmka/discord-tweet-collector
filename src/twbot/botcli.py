import asyncio
import logging
import re
import shlex

import discord
import tweepy

logging.basicConfig(level=logging.ERROR, format="%(threadName)s: %(message)s")
logger = logging.getLogger(__name__)


class TwListener(tweepy.StreamListener):
    def __init__(self, loop, uid, channel, match_ptn=None):
        super().__init__()
        self.loop = loop
        self.uid = uid
        self.channel = channel
        self.match_ptn = match_ptn

    def on_status(self, status):
        # Get new tweet
        # For some reason, get tweets of other users
        if status.user.id != self.uid:
            return

        # Not matched
        logger.debug(status.text)
        if self.match_ptn and not re.search(self.match_ptn, status.text):
            logger.debug("[DEBUG] status.text is not matched with regular expression")
            return

        url = f"https://twitter.com/{status.user.screen_name}/status/{status.id}"
        future = asyncio.run_coroutine_threadsafe(self.channel.send(url), self.loop)
        future.result()

    def on_error(self, status):
        logger.error(status)


class BotWriter:
    def __init__(self, auth, screen_name, channel, match_ptn):
        self.match_ptn = None
        self.stream = None

        loop = asyncio.get_event_loop()
        api = tweepy.API(auth)

        # Throw exception if the account is not exist
        status = api.get_user(screen_name)
        uid = status.id
        stream = tweepy.Stream(
            auth=auth, listener=TwListener(loop, uid, channel, match_ptn)
        )
        stream.filter(follow=[str(uid)], is_async=True)

        self.match_ptn = match_ptn
        self.stream = stream

    def __del__(self):
        if self.stream:
            self.stream.disconnect()


class BotClient(discord.Client):
    def __init__(self, consumer_key, consumer_secret, access_token, access_secret):
        super().__init__()
        self.auth = None
        self.writers = {}
        self._called_on_ready = False
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.access_token = access_token
        self.access_secret = access_secret

    # on_ready is not necessarily called just once.
    # So, do process only at the first calling.
    async def on_ready(self):
        if not self._called_on_ready:
            auth = tweepy.OAuthHandler(self.consumer_key, self.consumer_secret)
            auth.set_access_token(self.access_token, self.access_secret)
            self.auth = auth
            self._called_on_ready = True

    async def on_message(self, msg):
        # Raise error if msg.content cannot be parsed
        logger.debug(f"msg.content: {msg.content}")
        cmdlist = []
        try:
            cmdlist = shlex.split(msg.content)
            logger.debug(f"cmdlist: {cmdlist}")
        except:
            logger.debug(
                f"[DEBUG] Failed to parse msg.content (msg.content: {msg.content})"
            )
        cid = msg.channel.id

        maincmd = cmdlist[0] if len(cmdlist) > 0 else None
        subcmd = cmdlist[1] if len(cmdlist) > 1 else None

        # Do nothing when message has no '!tw'
        if maincmd != "!tw":
            return

        # Receive add command
        if subcmd == "add":
            screen_name = cmdlist[2] if len(cmdlist) > 2 else None
            match_ptn = cmdlist[3] if len(cmdlist) > 3 else None

            if not screen_name:
                emsg = f"[ERROR] アカウント名が指定されていません"
                await msg.channel.send(emsg)
                return

            if cid not in self.writers:
                self.writers[cid] = {}

            if screen_name in self.writers[cid]:
                emsg = f"[ERROR] 既に登録されているツイッターアカウントです (アカウント名: {screen_name})"
                await msg.channel.send(emsg)
                return

            try:
                if match_ptn:
                    # Check regular expression
                    re.compile(match_ptn)
                self.writers[cid][screen_name] = BotWriter(
                    self.auth, screen_name, msg.channel, match_ptn
                )
                imsg = f"[INFO] アカウントの登録に成功しました (アカウント名: {screen_name}"
                if match_ptn:
                    imsg += f', 正規表現: "{match_ptn}"'
                else:
                    imsg += ")"
                await msg.channel.send(imsg)
            except ValueError:
                logger.exception("[ERROR] Recieve Exception")
                emsg = f'[ERROR] 正規表現が不正です (正規表現: "{match_ptn})"'
                logger.error(emsg)
                await msg.channel.send(emsg)
                return
            except:
                logger.exception("[ERROR] Recieve Exception")
                emsg = f"[ERROR] 存在しないツイッターアカウント名です (アカウント名: {screen_name})"
                logger.error(emsg)
                await msg.channel.send(emsg)
                return

        # Receive remove command
        elif subcmd == "remove":
            account = cmdlist[2] if len(cmdlist) > 2 else None

            if not account:
                emsg = f"[ERROR] アカウント名が指定されていません"
                await msg.channel.send(emsg)
                return

            if cid not in self.writers or account not in self.writers[cid]:
                emsg = f"[ERROR] 登録されていないツイッターアカウントです (アカウント名: {account})"
                logger.error(emsg)
                await msg.channel.send(emsg)
                return

            self.writers[cid].pop(account)
            imsg = f"[INFO] アカウントの削除に成功しました (アカウント名: {account})"
            await msg.channel.send(imsg)

        # Receive list command
        elif subcmd == "list":
            imsg = f"[INFO] 登録済みのアカウントはありません"
            if cid in self.writers and self.writers[cid]:
                imsg = f"[INFO] 登録済みのアカウント:"
                for account in self.writers[cid]:
                    imsg += f"\r・{account}"
                    if self.writers[cid][account].match_ptn:
                        imsg += f" (正規表現: {self.writers[cid][account].match_ptn})"
            await msg.channel.send(imsg)

        # Receive help command
        elif subcmd == "help":
            imsg = f"[INFO] コマンド仕様:"
            imsg += f"\r・!tw add <アカウント名> [<正規表現パターン>]: 収集対象のアカウントを登録"
            imsg += f'\r　例: !tw add moujaatumare "#mildom" (#mildomを含むツイートのみ抽出)'
            imsg += f"\r・!tw remove <アカウント名>: 登録済みのアカウントを削除"
            imsg += f"\r・!tw list : 登録済みのアカウントの一覧表示"
            imsg += f"\r・!tw help : コマンド仕様を表示"
            await msg.channel.send(imsg)

        # Receive invalid command
        else:
            emsg = f'[ERROR] コマンドが不正です ("!tw help"を参照)'
            logger.error(emsg)
            await msg.channel.send(emsg)
