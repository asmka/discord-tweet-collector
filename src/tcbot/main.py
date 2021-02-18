import sys

from .logger import logger
from .config import Config
from .botcli import BotClient


def main():
    # Check arguments
    args = sys.argv
    if len(args) != 2:
        print(
            f"[ERROR] Usage: python {__file__} <config file>",
            file=sys.stderr,
        )
        sys.exit(1)

    config_file = args[1]

    # Parse config file
    try:
        config = Config(config_file)
    except Exception as exc:
        logger.exception("[ERROR] Recieve Exception")
        logger.error("[ERROR] Config file is invalid")
        print(
            f"[ERROR] Config file is invalid",
            file=sys.stderr,
        )
        sys.exit(1)

    # Run bot
    bot_cli = BotClient(
        config.consumer_key,
        config.consumer_secret,
        config.access_token,
        config.access_secret,
    )
    bot_cli.run(config.bot_token)


if __name__ == "__main__":
    main()
