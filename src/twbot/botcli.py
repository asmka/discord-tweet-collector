import asyncio
import re
import shlex

import discord
import tweepy

from .logger import logger


class TwStream(tweepy.Stream):
    def __init__(
        self, consumer_key, consumer_secret, access_token, access_secret, loop, writers
    ):
        super().__init__(consumer_key, consumer_secret, access_token, access_secret)
        writers_dict = {}
        for w in writers.values():
            if w.uid not in writers_dict:
                writers_dict[w.uid] = []
            writers_dict[w.uid].append(w)

        self.loop = loop
        self.writers_dict = writers_dict

    def on_status(self, status):
        # Get new tweet
        # For some reason, get tweets of other users
        if status.user.id not in self.writers_dict:
            return

        # Format tweet
        expand_text = status.text
        for e in status.entities["urls"]:
            expand_text = expand_text.replace(e["url"], e["display_url"])

        for w in self.writers_dict[status.user.id]:
            # Not matched
            if w.match_ptn and not re.search(w.match_ptn, expand_text):
                logger.debug(
                    "[DEBUG] status.text is not matched with regular expression"
                )
                return

            url = f"https://twitter.com/{status.user.screen_name}/status/{status.id}"
            future = asyncio.run_coroutine_threadsafe(w.channel.send(url), self.loop)
            future.result()

    def on_error(self, status):
        logger.error(status)


class Writer:
    def __init__(self, channel, uid, match_ptn):
        self.channel = channel
        self.uid = uid
        self.match_ptn = match_ptn


class BotWriter:
    def __init__(self, consumer_key, consumer_secret, access_token, access_secret, api):
        self.loop = asyncio.get_event_loop()

        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.access_token = access_token
        self.access_secret = access_secret
        self.api = api

        self.writers = {}
        self.user_counts = {}
        self.follows = []
        self.stream = None
        self.user_list = {}

    def close(self):
        if self.stream:
            self.stream.disconnect()
            self.stream = None

    def add(self, channel, screen_name, match_ptn):
        # Raise exception if the account is not exist
        status = self.api.get_user(screen_name=screen_name)
        uid = status.id
        cid = channel.id

        # Check regular expression
        if match_ptn:
            try:
                re.compile(match_ptn)
            except:
                logger.exception("[ERROR] Recieve Exception")
                emsg = f"[ERROR] 正規表現が不正です (正規表現: {repr(match_ptn)})"
                logger.error(emsg)
                return

        # Raise exception if the account is already registered
        if (cid, screen_name) in self.writers:
            raise ValueError(f"[ERROR] 既に登録されているツイッターアカウントです (アカウント名: {screen_name})")

        self.writers[(cid, screen_name)] = Writer(channel, uid, match_ptn)
        if screen_name not in self.user_counts:
            self.user_counts[screen_name] = 0
        self.user_counts[screen_name] += 1
        if cid not in self.user_list:
            self.user_list[cid] = []
        self.user_list[cid].append(screen_name)

        if str(uid) not in self.follows:
            self.follows.append(str(uid))

        # Reconstruct stream to run just one stream
        if self.stream:
            self.stream.disconnect()
        self.stream = TwStream(
            self.consumer_key,
            self.consumer_secret,
            self.access_token,
            self.access_secret,
            self.loop,
            self.writers,
        )
        # self.stream = tweepy.Stream(
        #    auth=self.auth, listener=TwListener(self.loop, self.writers)
        # )
        self.stream.filter(follow=self.follows, threaded=True)

    def remove(self, channel, screen_name):
        # Raise exception if the account is not exist
        cid = channel.id

        # Raise exception if the account is already registered
        if (cid, screen_name) not in self.writers:
            raise ValueError(f"[ERROR] 登録されていないツイッターアカウントです (アカウント名: {screen_name})")

        uid = self.writers[(cid, screen_name)].uid
        self.writers.pop((cid, screen_name))
        self.user_counts[screen_name] -= 1
        if self.user_counts[screen_name] == 0:
            self.follows.remove(str(uid))
            self.user_counts.pop(screen_name)
        self.user_list[cid].remove(screen_name)

        # Reconstruct stream to run just one stream
        if self.stream:
            self.stream.disconnect()
        self.stream = TwStream(
            self.consumer_key,
            self.consumer_secret,
            self.access_token,
            self.access_secret,
            self.loop,
            self.writers,
        )
        # self.stream = tweepy.Stream(
        #    auth=self.auth, listener=TwListener(self.loop, self.writers)
        # )
        self.stream.filter(follow=self.follows, threaded=True)


class BotClient(discord.Client):
    def __init__(self, consumer_key, consumer_secret, access_token, access_secret):
        super().__init__()
        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_secret)
        api = tweepy.API(auth)
        if api.verify_credentials() == False:
            raise ValueError("[ERROR] Failed to authenticate twitter api.")

        self.api = api
        self.bot_writer = None
        self.called_on_ready = False

        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.access_token = access_token
        self.access_secret = access_secret

    async def close(self):
        self.bot_writer.close()
        await super().close()

    # on_ready is not necessarily called just once.
    # So, do process only at the first calling.
    async def on_ready(self):
        if not self.called_on_ready:
            self.bot_writer = BotWriter(
                self.consumer_key,
                self.consumer_secret,
                self.access_token,
                self.access_secret,
                self.api,
            )
            self.called_on_ready = True

    async def on_message(self, msg):
        # Raise error if msg.content cannot be parsed
        cmdlist = []
        try:
            cmdlist = shlex.split(msg.content)
        except:
            logger.debug(
                f"[DEBUG] Failed to parse msg.content (msg.content: {msg.content})"
            )
            return

        maincmd = cmdlist[0] if len(cmdlist) > 0 else None
        subcmd = cmdlist[1] if len(cmdlist) > 1 else None
        cid = msg.channel.id

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

            try:
                self.bot_writer.add(msg.channel, screen_name, match_ptn)
                imsg = f"[INFO] アカウントの登録に成功しました (アカウント名: {screen_name}"
                if match_ptn:
                    imsg += f", 正規表現: {repr(match_ptn)}"
                else:
                    imsg += ")"
                await msg.channel.send(imsg)
            except Exception as exc:
                logger.exception("[ERROR] Recieve Exception")
                logger.error(exc)
                await msg.channel.send(exc)
                return

        # Receive remove command
        elif subcmd == "remove":
            screen_name = cmdlist[2] if len(cmdlist) > 2 else None

            if not screen_name:
                emsg = f"[ERROR] アカウント名が指定されていません"
                await msg.channel.send(emsg)
                return

            try:
                self.bot_writer.remove(msg.channel, screen_name)
            except Exception as exc:
                logger.exception("[ERROR] Recieve Exception")
                logger.error(exc)
                await msg.channel.send(exc)
                return

            imsg = f"[INFO] アカウントの削除に成功しました (アカウント名: {screen_name})"
            await msg.channel.send(imsg)

        # Receive list command
        elif subcmd == "list":
            imsg = f"[INFO] 登録済みのアカウントはありません"
            if cid in self.bot_writer.user_list and self.bot_writer.user_list[cid]:
                imsg = f"[INFO] 登録済みのアカウント:"
                for screen_name in self.bot_writer.user_list[cid]:
                    imsg += f"\r・{screen_name}"
                    if self.bot_writer.writers[(cid, screen_name)].match_ptn:
                        imsg += f" (正規表現: {repr(self.bot_writer.writers[(cid, screen_name)].match_ptn)})"
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
