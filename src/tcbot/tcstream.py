import asyncio
import threading
import re
import requests
from typing import List, Dict, Any

import tweepy
import discord

from .logger import logger
from .monitordb import MonitorDB
from .twauth import TwitterAuth


class TweetCollectStream(tweepy.Stream):
    def __init__(
        self,
        client: discord.Client,
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

        self.client = client
        self.loop = loop
        self.thread = None
        self.user_id_map = None

        # Create a monitor dictonary searched from twitter id
        monitors: List[Dict[str:Any]] = monitor_db.select()
        user_id_map: Dict[int : List[Dict[str:Any]]] = {}
        for m in monitors:
            tid = m["twitter_id"]
            if tid not in user_id_map:
                user_id_map[tid] = []
            user_id_map[tid].append(m)

        self.user_id_map = user_id_map

    async def _reconnect(self):
        logger.info("Reconnecting stream...")
        monitor_users = list(map(str, self.user_id_map.keys()))
        if monitor_users:
            # Wait stream is disconnected
            while self.running:
                pass
            self.filter(follow=monitor_users, threaded=True)

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
                logger.debug("status.text is not matched with regular expression")
                continue

            url = f"https://twitter.com/{status.user.screen_name}/status/{status.id}"
            channel = self.client.get_channel(m["channel_id"])
            future = asyncio.run_coroutine_threadsafe(channel.send(url), self.loop)
            future.result()

    def on_exception(self, exception):
        # Stream is already disconnected
        super().on_exception(exception)

        if isinstance(exception, requests.exceptions.ChunkedEncodingError):
            # Recconect stream because connection is reset by peer
            asyncio.run_coroutine_threadsafe(self._reconnect(), self.loop).result()
        else:
            logger.error("Catch not expected exception")
