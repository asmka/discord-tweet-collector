from typing import List, Dict

import discord
import pytest

from tcbot.monitordb import MonitorDB
from tcbot.botcli import BotClient
from tcbot.twauth import TwitterAuth

from evalcli import eval_send_messages

TT4BOT_USER_ID = 1359637846919847937
TWITTER_JP_USER_ID = 7080152


@pytest.fixture(scope="module")
def _empty_db_with_monitor_table(config):
    db = MonitorDB(config.db_url, config.db_table)
    db._do_sql(
        f"CREATE TABLE {config.db_table}("
        "channel_id bigint not null,"
        "twitter_id bigint not null,"
        "match_ptn text,"
        "PRIMARY KEY(channel_id, twitter_id)"
        ");"
    )
    yield db
    db._do_sql(f"DROP TABLE {config.db_table};")


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

    def test_add_exist_account_with_regular_expression(
        self, config, empty_monitor_db: MonitorDB
    ):
        assert eval_send_messages(
            config,
            empty_monitor_db,
            [r"!tc add tt4bot 'mildom\.com'"],
            [r"^\[INFO\] アカウントの登録に成功しました．アカウント名: tt4bot, 正規表現: 'mildom\\\\\.com'$"],
            5,
        )

    def test_add_not_exist_account(self, config, empty_monitor_db):
        assert eval_send_messages(
            config,
            empty_monitor_db,
            ["!tc add NON_EXSITING_ACCOUNT_202102212056"],
            [r"^\[ERROR\] 存在しないアカウントです．アカウント名: NON_EXSITING_ACCOUNT_202102212056$"],
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
        db.insert(config.test_channel_id, TT4BOT_USER_ID, None)
        assert eval_send_messages(
            config,
            db,
            ["!tc add tt4bot"],
            [r"^\[ERROR\] 既に登録されているアカウントです．アカウント名: tt4bot$"],
            5,
        )

    # remove command
    def test_remove_added_account(self, config, empty_monitor_db):
        assert eval_send_messages(
            config,
            empty_monitor_db,
            ["!tc add tt4bot", "!tc remove tt4bot"],
            [r"^\[INFO\] アカウントの削除に成功しました．アカウント名: tt4bot$"],
            5,
        )

    def test_remove_account_in_db(self, config, empty_monitor_db):
        db = empty_monitor_db
        db.insert(config.test_channel_id, TT4BOT_USER_ID, None)
        assert eval_send_messages(
            config,
            db,
            ["!tc remove tt4bot"],
            [r"^\[INFO\] アカウントの削除に成功しました．アカウント名: tt4bot$"],
            5,
        )

    def test_remove_non_exist_account(self, config, empty_monitor_db):
        assert eval_send_messages(
            config,
            empty_monitor_db,
            ["!tc remove NON_EXSITING_ACCOUNT_202102212056"],
            [r"^\[ERROR\] 存在しないアカウントです．アカウント名: NON_EXSITING_ACCOUNT_202102212056$"],
            5,
        )

    def test_remove_non_added_account(self, config, empty_monitor_db):
        assert eval_send_messages(
            config,
            empty_monitor_db,
            ["!tc remove tt4bot"],
            [r"^\[ERROR\] 登録されていないアカウントです．アカウント名: tt4bot$"],
            5,
        )

    # list command
    def test_list_with_empty_accounts(self, config, empty_monitor_db):
        assert eval_send_messages(
            config,
            empty_monitor_db,
            ["!tc list"],
            [r"^\[INFO\] 登録済みのアカウントはありません．$"],
            5,
        )

    def test_list_with_one_added_account(self, config, empty_monitor_db):
        assert eval_send_messages(
            config,
            empty_monitor_db,
            ["!tc add tt4bot", "!tc list"],
            [r"^\[INFO\] 登録済みのアカウント:" r"\r・アカウント名: tt4bot, 正規表現: None$"],
            5,
        )

    def test_list_with_two_added_accounts(self, config, empty_monitor_db):
        assert eval_send_messages(
            config,
            empty_monitor_db,
            ["!tc add tt4bot", r"!tc add TwitterJP 'mildom\.com'", "!tc list"],
            [
                r"^\[INFO\] 登録済みのアカウント:"
                r"\r・アカウント名: tt4bot, 正規表現: None"
                r"\r・アカウント名: TwitterJP, 正規表現: 'mildom\\\\\.com'$"
            ],
            5,
        )

    def test_list_with_two_accounts_in_db(self, config, empty_monitor_db):
        db = empty_monitor_db
        db.insert(config.test_channel_id, TT4BOT_USER_ID, None)
        db.insert(config.test_channel_id, TWITTER_JP_USER_ID, r"mildom\.com")
        assert eval_send_messages(
            config,
            empty_monitor_db,
            ["!tc list"],
            [
                r"^\[INFO\] 登録済みのアカウント:"
                r"\r・アカウント名: tt4bot, 正規表現: None"
                r"\r・アカウント名: TwitterJP, 正規表現: 'mildom\\\\\.com'$"
            ],
            5,
        )

    def test_help(self, config, empty_monitor_db):
        assert eval_send_messages(
            config,
            empty_monitor_db,
            ["!tc help"],
            [
                r"^\[INFO\] コマンド仕様:"
                r"\r・!tc add <アカウント名> \[<正規表現パターン>\]: 収集対象のアカウントを登録"
                r"\r　例: !tc add moujaatumare 'mildom\\\\\.com'"
                r"\r　動作: 'mildom\.com'を含むなるおのツイートのみ抽出（短縮リンクは展開）"
                r"\r・!tc remove <アカウント名>: 登録済みのアカウントを削除"
                r"\r・!tc list: 登録済みのアカウントの一覧表示"
                r"\r・!tc help: コマンド仕様を表示$"
            ],
            5,
        )

    def test_invalid_command(self, config, empty_monitor_db):
        assert eval_send_messages(
            config,
            empty_monitor_db,
            ["!tc invalid_command"],
            [r"^\[ERROR\] コマンドが不正です．'!tc help'を参照してください．$"],
            5,
        )
