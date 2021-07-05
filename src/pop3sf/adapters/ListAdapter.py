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
from typing import Optional, List
import time
import hashlib
from .AdapterAuxiliaries import AdapterAuxiliaries
from .AdapterBase import AdapterBase
from .AdapterCloseConnectionException import AdapterCloseConnectionException


class ListAdapter(AdapterBase):
    """
    This class simply relays messages from a list of strings to the POP3 server.

    It has little practical use - it's intended for testing and as an example.
    """

    class _Message:
        def __init__(self, content: str):
            self.content: str = content
            self.marked_as_deleted: bool = False

    def __init__(self, username: str, password: str, messages: List[str], wrap_plaintext_in_email: bool = True, plaintext_wrapper_message_date: Optional[time.struct_time] = None) -> None:
        # A RFC-822-compliant message needs to have a "Date:" header in it.
        # Since the wrapped message needs to be the same every time, the date also needs to be the same!
        if wrap_plaintext_in_email and plaintext_wrapper_message_date is None:
            raise AdapterCloseConnectionException("It's required to wrap plaintext messages in email bodies, but no message date was specified!")

        self._username: str = username
        self._password: str = password
        self._messages: List[str] = messages
        self._wrap_plaintext_in_email: bool = wrap_plaintext_in_email
        self._plaintext_wrapper_message_date: Optional[time.struct_time] = plaintext_wrapper_message_date

        self._message_objects: List[ListAdapter._Message] = self._generate_message_objects()

    def _generate_message_objects(self) -> List[ListAdapter._Message]:
        from_to = AdapterAuxiliaries.generate_from_to_email_address(self._username)

        if self._wrap_plaintext_in_email:
            return [ListAdapter._Message(AdapterAuxiliaries.wrap_plaintext_in_email(body, "Email {}".format(i), from_to, from_to, self._plaintext_wrapper_message_date)) for i, body in enumerate(self._messages, 1)]

        return [ListAdapter._Message(body) for body in self._messages]

    def verify_login_credentials(self, username: str, password: str) -> bool:
        return username == self._username and password == self._password

    def get_message_count(self) -> int:
        return len(self._message_objects)

    def get_message_content(self, index: int, encoding: str) -> str:
        return self._message_objects[index].content

    def is_message_marked_as_deleted(self, index: int) -> bool:
        return self._message_objects[index].marked_as_deleted

    def mark_message_as_deleted(self, index: int) -> None:
        self._message_objects[index].marked_as_deleted = True

    def unmark_messages_marked_as_deleted(self) -> None:
        for message_object in self._message_objects:
            message_object.marked_as_deleted = False

    def commit_deletions(self) -> None:
        # There is nowhere to commit the deletions in this (rare) case
        pass

    def get_message_unique_id(self, index: int) -> str:
        # The message's content might not be unique, but we have no other unique identifier in this (rare) case
        content = self.get_message_content(index, "utf-8").encode("utf-8")

        return hashlib.sha256(content).hexdigest()
