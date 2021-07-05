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


import email.message
import mysql.connector
from SingleuserAdapterToolBase import SingleuserAdapterToolBase


class MySQLSingleuserAdapterTool(SingleuserAdapterToolBase):
    class DatabaseCredentials:
        _DEFAULT_HOST: str = "localhost"

        def __init__(self, username: str, password: str, database: str, host: str = _DEFAULT_HOST):
            self.host: str = host
            self.username: str = username
            self.password: str = password
            self.database: str = database

    _DEFAULT_MESSAGES_TABLE_NAME: str = "pop3sf_singleuser_messages"

    def __init__(self, db_credentials: DatabaseCredentials, messages_table_name: str = _DEFAULT_MESSAGES_TABLE_NAME):
        self._mysql_connection = mysql.connector.connect(
            host=db_credentials.host,
            user=db_credentials.username,
            password=db_credentials.password,
            database=db_credentials.database
        )

        self._messages_table_name: str = messages_table_name

        self._create_mysql_tables_if_needed()

    def _create_mysql_tables_if_needed(self) -> None:
        cursor = self._mysql_connection.cursor()

        cursor.execute("""CREATE TABLE IF NOT EXISTS {} (
            id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY NOT NULL,
            message MEDIUMTEXT NOT NULL,
            is_plaintext BOOL NOT NULL,
            added_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
        )""".format(self._messages_table_name))

        self._mysql_connection.commit()

    def add_plaintext_message(self, message: str) -> None:
        self._add_message_to_database(message, True)

    def add_email_message(self, message: email.message.Message) -> None:
        self._add_message_to_database(str(message), False)

    def _add_message_to_database(self, text: str, is_plaintext: bool) -> None:
        cursor = self._mysql_connection.cursor()

        query = "INSERT INTO {} (message, is_plaintext) VALUES (%s, %s)".format(self._messages_table_name)
        cursor.execute(query, (text, is_plaintext))

        self._mysql_connection.commit()

    def close_db_connection(self) -> None:
        self._mysql_connection.close()
