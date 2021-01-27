import sys

import discord

from .botcli import BotClient


def main():
    # Check arguments
    args = sys.argv
    if len(args) != 2:
        print(
            f"[ERROR] Usage: python {__file__} <token>",
            file=sys.stderr,
        )
        sys.exit(1)

    token = args[1]

    # Run bot
    bot_cli = BotClient()
    bot_cli.run(token)


if __name__ == "__main__":
    main()
