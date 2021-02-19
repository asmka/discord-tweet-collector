from typing import List, Dict

import psycopg2
from psycopg2.extras import DictCursor

from tcbot.exception import TCBotError


class MonitorDB:
    def __init__(self, database_url: str, table_name: str):
        try:
            self.connection = psycopg2.connect(database_url)
        except psycopg2.OperationalError as exc:
            raise TCBotError(
                f"Failed to connect database. url: {database_url}"
            ) from exc
        else:
            self.connection.autocommit = True

        self.table_name = table_name

    def _do_sql(self, query: str) -> List[Dict]:
        with self.connection.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(query)
            try:
                rows = []
                for row in cursor.fetchall():
                    rows.append(dict(row))
                return rows
            except psycopg2.ProgrammingError:
                return None

    def select(self, channel_id: int = None, twitter_id: int = None) -> List[Dict]:
        table_name = self.table_name
        monitors: List[Dict] = []

        if channel_id is None and twitter_id is None:
            monitors = self._do_sql(f"SELECT * FROM {table_name};")
        elif channel_id is None:
            monitors = self._do_sql(
                f"SELECT * FROM {table_name} WHERE twitter_id = {twitter_id};"
            )
        elif twitter_id is None:
            monitors = self._do_sql(
                f"SELECT * FROM {table_name} WHERE channel_id = {channel_id};"
            )
        else:
            monitors = self._do_sql(
                f"SELECT * FROM {table_name} "
                f"WHERE channel_id = {channel_id} AND twitter_id = {twitter_id};"
            )

        return monitors

    def insert(self, channel_id: int, twitter_id: int, match_ptn: str):
        try:
            self._do_sql(
                f"INSERT INTO {self.table_name} VALUES (%s, %s, %s);"
                % (
                    "null" if channel_id is None else channel_id,
                    "null" if twitter_id is None else twitter_id,
                    "null" if match_ptn is None else f"'{match_ptn}'",
                )
            )
        except psycopg2.Error as exc:
            raise TCBotError(
                "Failed to insert a row. row: (%s, %s, %s)"
                % (
                    "null" if channel_id is None else channel_id,
                    "null" if twitter_id is None else twitter_id,
                    "null" if match_ptn is None else f"'{match_ptn}'",
                )
            ) from exc

    def delete(self, channel_id: int, twitter_id: int):
        try:
            self._do_sql(
                f"DELETE FROM {self.table_name} "
                f"WHERE channel_id = {channel_id} AND twitter_id = {twitter_id};"
            )
        except psycopg2.Error as exc:
            raise TCBotError(
                "Failed to delete a row. key: ({channel_id}, {twitter_id})"
            ) from exc
