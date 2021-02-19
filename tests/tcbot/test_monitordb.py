import pytest

from tcbot.monitordb import MonitorDB
from tcbot.exception import TCBotError


@pytest.fixture(scope="module")
def _empty_db_with_monitor_table(config):
    table_name = "test_monitors"
    db = MonitorDB(config.db_url, table_name)
    db._do_sql(
        f"CREATE TABLE {table_name}("
        "channel_id bigint not null,"
        "twitter_id bigint not null,"
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


class TestMonitorDB:
    def test_connect_to_db_with_valid_url(self, config):
        MonitorDB(config.db_url, "test_monitors")

    def test_connect_to_db_with_invalid_url(self):
        with pytest.raises(
            TCBotError,
            match=r"^Failed to connect database\. url: postgresql://INVALID_URL$",
        ):
            MonitorDB("postgresql://INVALID_URL", "test_monitors")

    # INSERT
    def test_insert_invalid_channel_id_with_None(self, empty_monitor_db):
        db = empty_monitor_db
        with pytest.raises(
            TCBotError,
            match=r"^Failed to insert a row\. row: \(null, 456, 'pattern'\)$",
        ):
            db.insert(None, 456, "pattern")

    def test_insert_invalid_channel_id_with_string(self, empty_monitor_db):
        db = empty_monitor_db
        with pytest.raises(
            TCBotError,
            match=r"^Failed to insert a row\. row: \(abc, 456, 'pattern'\)$",
        ):
            db.insert("abc", 456, "pattern")

    def test_insert_invalid_twitter_id_with_None(self, empty_monitor_db):
        db = empty_monitor_db
        with pytest.raises(
            TCBotError,
            match=r"^Failed to insert a row\. row: \(123, null, 'pattern'\)$",
        ):
            db.insert(123, None, "pattern")

    def test_insert_invalid_twitter_id_with_string(self, empty_monitor_db):
        db = empty_monitor_db
        with pytest.raises(
            TCBotError,
            match=r"^Failed to insert a row\. row: \(123, def, 'pattern'\)$",
        ):
            db.insert(123, "def", "pattern")

    def test_insert_match_ptn_with_None(self, empty_monitor_db):
        db = empty_monitor_db
        db.insert(123, 456, None)
        assert db.select() == [
            {
                "channel_id": 123,
                "twitter_id": 456,
                "match_ptn": None,
            }
        ]

    def test_insert_match_ptn_with_string(self, empty_monitor_db):
        db = empty_monitor_db
        db.insert(123, 456, r"mildom\.com")
        assert db.select() == [
            {
                "channel_id": 123,
                "twitter_id": 456,
                "match_ptn": r"mildom\.com",
            }
        ]

    def test_insert_duplicate_primary_key(self, empty_monitor_db):
        db = empty_monitor_db
        db.insert(123, 456, r"1st mildom\.com")
        with pytest.raises(
            TCBotError,
            match=r"^Failed to insert a row\. row: \(123, 456, '2nd mildom\\\.com'\)$",
        ):
            db.insert(123, 456, r"2nd mildom\.com")

    # DELETE
    def test_delete_exist_row(self, empty_monitor_db):
        db = empty_monitor_db
        db.insert(123, 456, r"mildom\.com")
        db.delete(123, 456)
        assert db.select() == []

    def test_delete_non_exist_row(self, empty_monitor_db):
        db = empty_monitor_db
        db.insert(123, 456, r"mildom\.com")
        db.delete(123, 654)
        db.delete(321, 456)
        db.delete(456, 123)
        assert db.select() == [
            {
                "channel_id": 123,
                "twitter_id": 456,
                "match_ptn": r"mildom\.com",
            }
        ]
