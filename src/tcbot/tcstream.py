import asyncio
import re
from typing import List, Tuple

import tweepy
import discord

from .logger import logger
from .monitordb import MonitorDB
from .twauth import TwitterAuth


class TweetCollectStream(tweepy.Stream):
    def __init__(
        self,
        tw_auth: TwitterAuth,
        monitor_db: MonitorDB,
        loop,
    ):
        super().__init__(
            tw_auth.consumer_key,
            tw_auth.consumer_secret,
            tw_auth.access_token,
            tw_auth.access_secret,
        )

        self.monitor_db = monitor_db
        self.loop = loop
        self.thread = None
        self.user_id_map = None

    def resume(self):
        monitors = self.monitor_db.select_all()
        user_id_map = {}
        for m in monitors:
            user_id_map[m["twitter_id"]] = m

        if self.thread:
            self.disconnect()

        self.thread = self.filter(
            follow=list(map(str, user_id_map.keys())), threaded=True
        )
        self.user_id_map = user_id_map

    def disconnect(self):
        super().disconnect()
        # Wait stream blocking I/O thread
        if self.thread:
            self.thread.join()
            self.thread = None

    def on_status(self, status):
        # Get new tweet
        # For some reason, get tweets of other users

        user_id = status.user.id
        if user_id not in self.user_id_map:
            return

        # Format tweet
        expand_text = status.text
        for e in status.entities["urls"]:
            expand_text = expand_text.replace(e["url"], e["display_url"])

        for m in self.user_id_map[user_id]:
            # Not matched
            if m["match_ptn"] and not re.search(m["match_ptn"], expand_text):
                logger.debug(
                    "[DEBUG] status.text is not matched with regular expression"
                )
                return

            url = f"https://twitter.com/{status.user.screen_name}/status/{status.id}"
            future = asyncio.run_coroutine_threadsafe(m.channel.send(url), self.loop)
            future.result()

    def on_error(self, status):
        logger.error(status)
