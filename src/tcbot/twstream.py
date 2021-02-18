import asyncio
import re
from typing import List, Tuple

import tweepy
import discord

from .logger import logger


class Monitor:
    def __init__(self, channel: discord.TextChannel, user_id: int, match_ptn: str):
        self.channel = channel
        self.user_id = user_id
        self.match_ptn = match_ptn


class TweetStream(tweepy.Stream):
    def __init__(
        self,
        consumer_key,
        consumer_secret,
        access_token,
        access_secret,
        monitors: List[Monitor],
        loop,
    ):
        super().__init__(consumer_key, consumer_secret, access_token, access_secret)
        monitors_dict = {}
        for m in monitors:
            if m.user_id not in monitors_dict:
                monitors_dict[m.user_id] = []
            monitors_dict[m.user_id].append(m)

        self.loop = loop
        self.monitors_dict = monitors_dict

    def on_status(self, status):
        # Get new tweet
        # For some reason, get tweets of other users

        user_id = status.user.id
        if user_id not in self.monitors_dict:
            return

        # Format tweet
        expand_text = status.text
        for e in status.entities["urls"]:
            expand_text = expand_text.replace(e["url"], e["display_url"])

        for m in self.monitors_dict[user_id]:
            # Not matched
            if m.match_ptn and not re.search(m.match_ptn, expand_text):
                logger.debug(
                    "[DEBUG] status.text is not matched with regular expression"
                )
                return

            url = f"https://twitter.com/{status.user.screen_name}/status/{status.id}"
            future = asyncio.run_coroutine_threadsafe(m.channel.send(url), self.loop)
            future.result()

    def on_error(self, status):
        logger.error(status)
