import sys
import argparse

from .logger import logger
from .exception import TCBotError
from .config import Config
from .monitordb import MonitorDB
from .twauth import TwitterAuth
from .botcli import BotClient


def main():
    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--conf", metavar="FILEPATH", help="config json file")
    args = parser.parse_args()

    config_file = args.conf

    # Parse config file
    try:
        config = Config(file_name=config_file)
    except TCBotError as exc:
        logger.exception("Catch Exception")
        logger.error(str(exc))
        sys.exit(1)

    monitor_db = MonitorDB(config.db_url, config.db_table)
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
