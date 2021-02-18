from typing import List, Dict

import discord
import pytest

from tcbot.monitordb import MonitorDB
from tcbot.botcli import BotClient
from tcbot.twauth import TwitterAuth

from evalcli import eval_send_messages


EDAISGOD2525_USER_ID = 1170664739199807488
TT4BOT_USER_ID = 1359637846919847937


@pytest.fixture(scope="module")
def _empty_db_with_monitor_table(config):
    table_name = "test_monitors"
    db = MonitorDB(config.db_url, table_name)
    db._do_sql(
        f"CREATE TABLE {table_name}("
        "channel_id bigint not null,"
        "twitter_id bigint not null,"
        "twitter_name text not null,"
        "match_ptn text,"
        "PRIMARY KEY(channel_id, twitter_id)"
        ");"
    )
    yield db
    db._do_sql(f"DROP TABLE {table_name};")


@pytest.fixture(scope="function")
def empty_monitor_db(_empty_db_with_monitor_table):
    db = _empty_db_with_monitor_table
    yield db
    # Clean up table
    db._do_sql(f"DELETE FROM {db.table_name};")


class TestBotClient:
    def test_invalid_main_command(self, config, empty_monitor_db):
        assert eval_send_messages(config, empty_monitor_db, ["!tcc add"], [], 5)

    # add command
    def test_add_exist_account(self, config, empty_monitor_db: MonitorDB):
        assert eval_send_messages(
            config,
            empty_monitor_db,
            ["!tc add tt4bot"],
            [r"^\[INFO\] アカウントの登録に成功しました．アカウント名: tt4bot, 正規表現: None$"],
            5,
        )

    def test_add_not_exist_account(self, config, empty_monitor_db):
        assert eval_send_messages(
            config,
            empty_monitor_db,
            ["!tc add NON_EXSITING_ACCOUNT_202102211456"],
            [r"^\[ERROR\] 存在しないアカウントです．アカウント名: NON_EXSITING_ACCOUNT_202102211456$"],
            5,
        )

    def test_add_account_twice(self, config, empty_monitor_db):
        assert eval_send_messages(
            config,
            empty_monitor_db,
            ["!tc add tt4bot", "!tc add tt4bot"],
            [
                r"^\[INFO\] アカウントの登録に成功しました．アカウント名: tt4bot, 正規表現: None$",
                r"^\[ERROR\] 既に登録されているアカウントです．アカウント名: tt4bot$",
            ],
            5,
        )

    def test_add_account_in_db(self, config, empty_monitor_db):
        db = empty_monitor_db
        db.insert(config.test_channel_id, TT4BOT_USER_ID, "tt4bot", None)
        assert eval_send_messages(
            config,
            db,
            ["!tc add tt4bot"],
            [
                r"^\[ERROR\] 既に登録されているアカウントです．アカウント名: tt4bot$",
            ],
            5,
        )
