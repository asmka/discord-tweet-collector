import sys

from .logger import logger
from .exception import TCBotError
from .config import Config
from .monitordb import MonitorDB
from .twauth import TwitterAuth
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
    except TCBotError:
        logger.exception("[ERROR] Recieve Exception")
        logger.error("[ERROR] Config file is invalid")
        print(
            f"[ERROR] Config file is invalid",
            file=sys.stderr,
        )
        sys.exit(1)

    monitor_db = MonitorDB(config.db_url, "monitors")
    tw_auth = TwitterAuth(
        config.consumer_key,
        config.consumer_secret,
        config.access_token,
        config.access_secret,
    )
    # Run bot
    bot_cli = BotClient(monitor_db, tw_auth)
    bot_cli.run(config.bot_token)


if __name__ == "__main__":
    main()
