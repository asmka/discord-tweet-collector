import sys

import discord


class BotClient(discord.Client):
    def __init__(self):
        super().__init__()

    async def on_ready(self):
        pass

    async def on_message(self, msg):
        pass
