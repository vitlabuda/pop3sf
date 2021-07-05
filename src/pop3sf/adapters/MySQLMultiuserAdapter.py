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


from typing import Optional, List
from .AdapterAuxiliaries import AdapterAuxiliaries
from .MySQLAdapterBase import MySQLAdapterBase


class MySQLMultiuserAdapter(MySQLAdapterBase):
    """
    This adapter is similar to MySQLAdapter, but it offers multi-user capabilities.

    Instead of passing the username and bcrypt-hashed password to the constructor, the credentials are fetched from a MySQL table.
    Similarly, the messages table can store messages for multiple users.

    The fields of the aforementioned tables, which get automatically created if they don't exist, can be found in the _create_mysql_tables_if_needed() method of this class.

    An external program can freely insert messages into the messages table. However, it MUST NOT update or delete them!
    The users table can be modified freely from an external program.
    """

    _DEFAULT_MESSAGES_TABLE_NAME: str = "pop3sf_multiuser_messages"
    _DEFAULT_USERS_TABLE_NAME: str = "pop3sf_multiuser_users"

    def __init__(self, db_credentials: MySQLAdapterBase.DatabaseCredentials, messages_table_name: str = _DEFAULT_MESSAGES_TABLE_NAME, users_table_name: str = _DEFAULT_USERS_TABLE_NAME):
        self._users_table_name: str = users_table_name  # The super().__init__() calls the _create_mysql_tables_if_needed() method which uses this variable, so it needs to be defined there

        super().__init__(db_credentials, messages_table_name)

        self._user_id: Optional[int] = None

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

    def _generate_message_index(self) -> List[MySQLAdapterBase._MessageIndexEntry]:
        assert self._user_id is not None

        # Fetch the user's messages from the database
        cursor = self._mysql_connection.cursor()

        query = "SELECT id FROM {} WHERE user_id = %s".format(self._messages_table_name)
        cursor.execute(query, (self._user_id,))

        messages = cursor.fetchall()

        # Generate the message index
        return [MySQLAdapterBase._MessageIndexEntry(message_id) for message_id, in messages]

    def verify_login_credentials(self, username: str, password: str) -> bool:
        # Fetch the user's metadata from the database
        cursor = self._mysql_connection.cursor()

        query = "SELECT id,password_bcrypt FROM {} WHERE username = %s".format(self._users_table_name)
        cursor.execute(query, (username,))

        user_metadata = cursor.fetchall()
        if len(user_metadata) != 1:  # = if the user doesn't exist
            return False

        id_, password_bcrypt = user_metadata[0]

        # Check the user's password
        is_password_correct = AdapterAuxiliaries.check_bcrypt_password(password, password_bcrypt)
        if not is_password_correct:
            return False

        # Save the user's ID and return
        self._user_id = id_

        return True
