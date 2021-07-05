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


from typing import List
from .AdapterAuxiliaries import AdapterAuxiliaries
from .MySQLAdapterBase import MySQLAdapterBase


class MySQLSingleuserAdapter(MySQLAdapterBase):
    """
    This adapter relays messages from a MySQL table to the POP3 server.
    You can find the fields of the messages table in the _create_mysql_tables_if_needed() method of this class. The table gets automatically created if it doesn't exist.

    The valid username and bcrypt-hashed password is passed to the constructor, just as the database credentials & messages table name.

    An external program can freely insert messages into the messages table. However, it MUST NOT update or delete them!
    """

    _DEFAULT_MESSAGES_TABLE_NAME: str = "pop3sf_singleuser_messages"

    def __init__(self, username: str, password_bcrypt: str, db_credentials: MySQLAdapterBase.DatabaseCredentials, messages_table_name: str = _DEFAULT_MESSAGES_TABLE_NAME):
        super().__init__(db_credentials, messages_table_name)

        self._username: str = username
        self._password_bcrypt: str = password_bcrypt

    def _create_mysql_tables_if_needed(self) -> None:
        cursor = self._mysql_connection.cursor()

        cursor.execute("""CREATE TABLE IF NOT EXISTS {} (
            id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY NOT NULL,
            message MEDIUMTEXT NOT NULL,
            is_plaintext BOOL NOT NULL,
            added_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
        )""".format(self._messages_table_name))

        self._mysql_connection.commit()

    def _generate_message_index(self) -> List[MySQLAdapterBase._MessageIndexEntry]:
        # Fetch messages from the database
        cursor = self._mysql_connection.cursor()

        cursor.execute("SELECT id FROM {}".format(self._messages_table_name))

        messages = cursor.fetchall()

        # Generate the message index
        return [MySQLAdapterBase._MessageIndexEntry(message_id) for message_id, in messages]

    def verify_login_credentials(self, username: str, password: str) -> bool:
        return username == self._username and AdapterAuxiliaries.check_bcrypt_password(password, self._password_bcrypt)
