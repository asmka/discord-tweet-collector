import sys
import asyncio
import logging

import discord
import tweepy

logging.basicConfig(level=logging.DEBUG, format="%(threadName)s: %(message)s")
logger = logging.getLogger(__name__)


class TwListener(tweepy.StreamListener):
    def __init__(self, uid, channel, loop):
        super().__init__()
        self.uid = uid
        self.channel = channel
        self.loop = loop

    def on_status(self, status):
        # Get new tweet
        # For some reason, get tweets of other users
        if status.user.id_str != self.uid:
            return
        url = f"https://twitter.com/{status.user.screen_name}/status/{status.id_str}"
        future = asyncio.run_coroutine_threadsafe(self.channel.send(url), self.loop)
        future.result()

    def on_error(self, status):
        logger.error(status)


class BotWriter:
    def __init__(self, auth, screen_name, channel):
        loop = asyncio.get_event_loop()
        api = tweepy.API(auth)

        # Throw exception if the account is not exist
        status = api.get_user(screen_name)
        uid = status.id_str
        stream = tweepy.Stream(auth=auth, listener=TwListener(uid, channel, loop))
        stream.filter(follow=[uid], is_async=True)

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
        cmdlist = msg.content.split()
        cid = msg.channel.id

        # Do nothing when message has no '!tw'
        if len(cmdlist) < 1 or cmdlist[0] != "!tw":
            return

        # Receive add command
        elif len(cmdlist) == 3 and cmdlist[1] == "add":
            screen_name = cmdlist[2]

            if cid not in self.writers:
                self.writers[cid] = {}

            if screen_name in self.writers[cid]:
                emsg = f"[ERROR] 既に登録されているツイッターアカウントです (アカウント名: {screen_name})"
                return

            try:
                self.writers[cid][screen_name] = BotWriter(
                    self.auth, screen_name, msg.channel
                )
                imsg = f"[INFO] アカウントの登録に成功しました (アカウント名: {screen_name})"
                await msg.channel.send(imsg)
            except:
                logger.exception()
                emsg = f"[ERROR] 存在しないツイッターアカウント名です (アカウント名: {screen_name})"
                logger.error(emsg)
                await msg.channel.send(emsg)
                return

        # Receive remove command
        elif len(cmdlist) == 3 and cmdlist[1] == "remove":
            account = cmdlist[2]
            if cid not in self.writers or account not in self.writers[cid]:
                emsg = f"[ERROR] 登録されていないツイッターアカウントです (アカウント名: {account})"
                logger.error(emsg)
                await msg.channel.send(emsg)
                return
            self.writers[cid].pop(account)
            imsg = f"[INFO] アカウントの削除に成功しました (アカウント名: {account})"
            await msg.channel.send(imsg)

        # Receive list command
        elif len(cmdlist) == 2 and cmdlist[1] == "list":
            imsg = f"[INFO] 登録済みのアカウントはありません"
            if cid in self.writers and self.writers[cid]:
                imsg = f"[INFO] 登録済みのアカウント:"
                for account in self.writers[cid]:
                    imsg += f"\r・{account}"
            await msg.channel.send(imsg)

        # Receive help command
        elif len(cmdlist) == 2 and cmdlist[1] == "help":
            imsg = f"[INFO] コマンド仕様:"
            imsg += f"\r・add <アカウント名>: 収集対象のアカウントを登録"
            imsg += f"\r・remove <アカウント名>: 登録済みのアカウントを削除"
            imsg += f"\r・list : 登録済みのアカウントの一覧表示"
            imsg += f"\r・help : コマンド仕様を表示"
            await msg.channel.send(imsg)

        # Receive invalid command
        else:
            emsg = f'[ERROR] コマンドが不正です ("!tw help"を参照)'
            logger.error(emsg)
            await msg.channel.send(emsg)
