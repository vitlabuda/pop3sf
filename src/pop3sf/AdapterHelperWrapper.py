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


from typing import Tuple, List
import re
import time
from .Settings import Settings
from .Auxiliaries import Auxiliaries
from .POP3ResponseCodes import POP3ResponseCodes
from .SendDataToClientException import SendDataToClientException
from .AdapterThreadLockingWrapper import AdapterThreadLockingWrapper
from .adapters.AdapterBase import AdapterBase


class AdapterHelperWrapper:
    def __init__(self, adapter: AdapterBase, client_status):
        from .ClientStatusHolder import ClientStatusHolder  # Circular import prevention

        self._locking_adapter: AdapterThreadLockingWrapper = AdapterThreadLockingWrapper(adapter)
        self._client_status: ClientStatusHolder = client_status

    def connection_opened(self) -> None:
        self._locking_adapter.connection_opened(self._client_status.connection_info.address, self._client_status.connection_info.port)

    def read_only_mode_allowed(self) -> bool:
        return self._locking_adapter.read_only_mode_allowed()

    def verify_login_credentials(self, username: str, password: str) -> bool:
        success = self._locking_adapter.verify_login_credentials(username, password)

        if not success:
            self._perform_invalid_password_punishments()

        return success

    def _perform_invalid_password_punishments(self) -> None:
        time.sleep(Settings.FAILED_LOGIN_DELAY / 1000)

        if Settings.MAX_INVALID_PASSWORDS_PER_SESSION >= 0:
            self._client_status.invalid_password_count += 1
            if self._client_status.invalid_password_count > Settings.MAX_INVALID_PASSWORDS_PER_SESSION:
                raise SendDataToClientException.err("Too many incorrect passwords", pop3_response_code=POP3ResponseCodes.Codes.AUTH).close_connection_after_sending_data()

    def login_successful(self, username: str) -> None:
        self._locking_adapter.login_successful(username, self._client_status.read_only_mailbox_access)

    def get_message_count(self) -> int:
        message_count = self._locking_adapter.get_message_count()

        if message_count < 0:
            raise SendDataToClientException.err_internal()

        return message_count

    def get_undeleted_message_count(self) -> int:
        count = 0

        for index in range(self.get_message_count()):
            if not self.is_message_marked_as_deleted(index):
                count += 1

        return count

    def get_message_content(self, index: int) -> str:
        return self._locking_adapter.get_message_content(index, self._client_status.encoding)

    def get_headers_and_first_n_lines_of_a_message(self, index: int, n: int) -> str:  # Used by the TOP command
        all_lines = Auxiliaries.split_lines_without_discarding_empty_lines(self.get_message_content(index))
        requested_lines = []

        # Copy the message's headers (headers and body are separated by a blank line)
        while all_lines and all_lines[0]:
            requested_lines.append(all_lines.pop(0))

        # Add the empty line, if there is any
        if all_lines:
            requested_lines.append(all_lines.pop(0))

        # Copy the requested number of lines from the message's body
        for i, line in enumerate(all_lines):
            if i >= n:
                break

            requested_lines.append(line)

        return "\r\n".join(requested_lines)

    def is_message_marked_as_deleted(self, index: int) -> bool:
        if self._client_status.read_only_mailbox_access:
            return False  # When the adapter access is set to read-only, the DELE command can't be called -> the message can't ever be deleted.

        return self._locking_adapter.is_message_marked_as_deleted(index)

    def mark_message_as_deleted(self, index: int) -> None:
        if self._client_status.read_only_mailbox_access:
            raise SendDataToClientException.err_read_only_mailbox_access()

        self._locking_adapter.mark_message_as_deleted(index)

    def unmark_messages_marked_as_deleted(self) -> None:
        if self._client_status.read_only_mailbox_access:
            raise SendDataToClientException.err_read_only_mailbox_access()

        self._locking_adapter.unmark_messages_marked_as_deleted()

    def commit_deletions(self) -> None:
        if self._client_status.read_only_mailbox_access:
            return  # Any deletions cannot be committed anyway when the adapter access is set to read-only.

        self._locking_adapter.commit_deletions()

    def get_message_size(self, index: int) -> int:
        content = self.get_message_content(index)
        content = re.sub(r'\r\n|\r|\n', '\r\n', content)  # See RFC 1939, Section 11 (Message Format)

        try:
            message_size = len(content.encode(self._client_status.encoding))
        except UnicodeEncodeError:
            raise SendDataToClientException.err("The message, whose size was obtained, contains a non-ASCII character (the UTF-8 mode is not enabled)", pop3_response_code=POP3ResponseCodes.Codes.UTF8)

        return message_size

    def get_all_undeleted_messages_sizes(self) -> List[Tuple[int, int]]:
        # List comprehension is not used since the line would be too long and therefore confusing
        all_message_numbers_and_sizes = []

        for index in range(self.get_message_count()):
            if not self.is_message_marked_as_deleted(index):
                new_entry = Auxiliaries.convert_index_to_message_number(index), self.get_message_size(index)
                all_message_numbers_and_sizes.append(new_entry)

        return all_message_numbers_and_sizes

    def get_message_unique_id(self, index: int) -> str:
        unique_id = self._locking_adapter.get_message_unique_id(index)

        if not re.match(r'^[\x21-\x7e]{1,70}$', unique_id):
            raise SendDataToClientException.err_internal()

        return unique_id

    def get_all_undeleted_messages_unique_ids(self) -> List[Tuple[int, str]]:
        # List comprehension is not used since the line would be too long and therefore confusing
        all_message_numbers_and_unique_ids = []

        for index in range(self.get_message_count()):
            if not self.is_message_marked_as_deleted(index):
                new_entry = Auxiliaries.convert_index_to_message_number(index), self.get_message_unique_id(index)
                all_message_numbers_and_unique_ids.append(new_entry)

        # _Message unique IDs must be unique
        only_unique_ids = [unique_id for _, unique_id in all_message_numbers_and_unique_ids]
        if len(only_unique_ids) != len(set(only_unique_ids)):
            raise SendDataToClientException.err_internal()

        return all_message_numbers_and_unique_ids

    def connection_closed(self) -> None:
        self._locking_adapter.connection_closed()
