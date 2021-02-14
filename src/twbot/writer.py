import discord


async def send_info(channel: discord.TextChannel, msg):
    prefix = "[INFO] "
    await channel.send(prefix + msg)


async def send_error(channel: discord.TextChannel, msg):
    prefix = "[ERROR] "
    await channel.send(prefix + msg)
