# SPDX-License-Identifier: BSD-3-Clause
#
# Copyright (c) 2021 Vít Labuda. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification, are permitted provided that the
# following conditions are met:
#  1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following
#     disclaimer.
#  2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the
#     following disclaimer in the documentation and/or other materials provided with the distribution.
#  3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote
#     products derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


from __future__ import annotations
from typing import List
import abc
import time
import datetime
import mysql.connector
from .AdapterAuxiliaries import AdapterAuxiliaries
from .AdapterBase import AdapterBase


class MySQLAdapterBase(AdapterBase, metaclass=abc.ABCMeta):
    class DatabaseCredentials:
        _DEFAULT_HOST: str = "localhost"

        def __init__(self, username: str, password: str, database: str, host: str = _DEFAULT_HOST):
            self.host: str = host
            self.username: str = username
            self.password: str = password
            self.database: str = database

    class _MessageIndexEntry:
        def __init__(self, id_: int):
            self.id_: int = id_
            self.marked_as_deleted: bool = False

    def __init__(self, db_credentials: DatabaseCredentials, messages_table_name: str):
        self._mysql_connection = mysql.connector.connect(
            host=db_credentials.host,
            user=db_credentials.username,
            password=db_credentials.password,
            database=db_credentials.database
        )

        self._messages_table_name: str = messages_table_name
        self._create_mysql_tables_if_needed()

        self._message_index: List[MySQLAdapterBase._MessageIndexEntry] = []

    @abc.abstractmethod
    def _create_mysql_tables_if_needed(self) -> None:
        raise NotImplementedError("The _create_mysql_tables_if_needed() method must be overridden prior to calling it!")

    def login_successful(self, username: str, read_only: bool) -> None:
        self._message_index = self._generate_message_index()

    @abc.abstractmethod
    def _generate_message_index(self) -> List[MySQLAdapterBase._MessageIndexEntry]:
        raise NotImplementedError("The _generate_message_index() method must be overridden prior to calling it!")

    def get_message_count(self) -> int:
        return len(self._message_index)

    def get_message_content(self, index: int, encoding: str) -> str:
        message_id = self._message_index[index].id_

        # Fetch the message from the database
        cursor = self._mysql_connection.cursor()

        query = "SELECT message,is_plaintext,added_timestamp FROM {} WHERE id = %s".format(self._messages_table_name)
        cursor.execute(query, (message_id,))

        message, is_plaintext, added_timestamp = cursor.fetchone()

        # Return the message contents as an email
        if is_plaintext:
            subject = "Plaintext database entry {}".format(message_id)
            from_to = AdapterAuxiliaries.generate_from_to_email_address("nobody")

            return AdapterAuxiliaries.wrap_plaintext_in_email(message, subject, from_to, from_to, self._convert_datetime_object_to_struct_time(added_timestamp))

        return message

    def _convert_datetime_object_to_struct_time(self, datetime_object: datetime.datetime) -> time.struct_time:
        # If the datetime object is converted to struct_time only using the datetime.timetuple() method, the timezone is missing.

        epoch = time.mktime(datetime_object.timetuple())

        return time.gmtime(epoch)

    def get_message_unique_id(self, index: int) -> str:
        # The message ID is unique, as it's auto-incremented by the MySQL database

        return str(self._message_index[index].id_)

    def is_message_marked_as_deleted(self, index: int) -> bool:
        return self._message_index[index].marked_as_deleted

    def mark_message_as_deleted(self, index: int) -> None:
        self._message_index[index].marked_as_deleted = True

    def unmark_messages_marked_as_deleted(self) -> None:
        for message in self._message_index:
            message.marked_as_deleted = False

    def commit_deletions(self) -> None:
        for message in self._message_index:
            if message.marked_as_deleted:
                self._delete_message_from_database(message)

    def _delete_message_from_database(self, message: _MessageIndexEntry) -> None:
        cursor = self._mysql_connection.cursor()

        query = "DELETE FROM {} WHERE id = %s".format(self._messages_table_name)
        cursor.execute(query, (message.id_,))

        self._mysql_connection.commit()

    def connection_closed(self) -> None:
        self._mysql_connection.close()
