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
import bcrypt
import mysql.connector
from MultiuserAdapterToolBase import MultiuserAdapterToolBase


class MySQLMultiuserAdapterTool(MultiuserAdapterToolBase):
    class DatabaseCredentials:
        _DEFAULT_HOST: str = "localhost"

        def __init__(self, username: str, password: str, database: str, host: str = _DEFAULT_HOST):
            self.host: str = host
            self.username: str = username
            self.password: str = password
            self.database: str = database

    _DEFAULT_MESSAGES_TABLE_NAME: str = "pop3sf_multiuser_messages"
    _DEFAULT_USERS_TABLE_NAME: str = "pop3sf_multiuser_users"

    def __init__(self, db_credentials: DatabaseCredentials, messages_table_name: str = _DEFAULT_MESSAGES_TABLE_NAME, users_table_name: str = _DEFAULT_USERS_TABLE_NAME):
        self._mysql_connection = mysql.connector.connect(
            host=db_credentials.host,
            user=db_credentials.username,
            password=db_credentials.password,
            database=db_credentials.database
        )

        self._messages_table_name: str = messages_table_name
        self._users_table_name: str = users_table_name

        self._create_mysql_tables_if_needed()

    def _create_mysql_tables_if_needed(self) -> None:
        cursor = self._mysql_connection.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS {} (
            id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY NOT NULL,
            user_id INT UNSIGNED NOT NULL,
            message MEDIUMTEXT NOT NULL,
            is_plaintext BOOL NOT NULL,
            added_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
        )""".format(self._messages_table_name))

        cursor = self._mysql_connection.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS {} (
            id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY NOT NULL,
            username VARCHAR(64) UNIQUE NOT NULL,
            password_bcrypt CHAR(60) NOT NULL
        )""".format(self._users_table_name))

        self._mysql_connection.commit()

    def does_user_exist(self, username: str) -> bool:
        cursor = self._mysql_connection.cursor()

        query = "SELECT id FROM {} WHERE username = %s".format(self._users_table_name)
        cursor.execute(query, (username,))

        user_metadata = cursor.fetchall()

        return len(user_metadata) == 1

    def add_user(self, username: str, password: str) -> None:
        if self.does_user_exist(username):
            raise MySQLMultiuserAdapterTool.UserAlreadyExistsException(username)

        cursor = self._mysql_connection.cursor()

        query = "INSERT INTO {} (username, password_bcrypt) VALUES (%s, %s)".format(self._users_table_name)
        values = (username, self._hash_password_using_bcrypt(password))
        cursor.execute(query, values)

        self._mysql_connection.commit()

    def change_user_password(self, username: str, new_password: str) -> None:
        if not self.does_user_exist(username):
            raise MySQLMultiuserAdapterTool.UserDoesNotExistException(username)

        cursor = self._mysql_connection.cursor()

        query = "UPDATE {} SET password_bcrypt = %s WHERE username = %s".format(self._users_table_name)
        values = (self._hash_password_using_bcrypt(new_password), username)
        cursor.execute(query, values)

        self._mysql_connection.commit()

    def _hash_password_using_bcrypt(self, password: str) -> str:
        password_bcrypt = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

        return password_bcrypt.decode("utf-8")

    def add_plaintext_message(self, username: str, message: str) -> None:
        self._add_message_to_database(message, username, True)

    def add_email_message(self, username: str, message: email.message.Message) -> None:
        self._add_message_to_database(str(message), username, False)

    def _add_message_to_database(self, text: str, username: str, is_plaintext: bool) -> None:
        if not self.does_user_exist(username):
            raise MySQLMultiuserAdapterTool.UserDoesNotExistException(username)

        user_id = self._get_user_id_by_username(username)

        cursor = self._mysql_connection.cursor()

        query = "INSERT INTO {} (user_id, message, is_plaintext) VALUES (%s, %s, %s)".format(self._messages_table_name)
        cursor.execute(query, (user_id, text, is_plaintext))

        self._mysql_connection.commit()

    def _get_user_id_by_username(self, username: str) -> int:
        cursor = self._mysql_connection.cursor()

        query = "SELECT id FROM {} WHERE username = %s".format(self._users_table_name)
        cursor.execute(query, (username,))

        return cursor.fetchone()[0]

    def close_db_connection(self) -> None:
        self._mysql_connection.close()
