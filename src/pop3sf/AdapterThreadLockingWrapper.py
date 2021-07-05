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


from typing import Union
import ipaddress
import threading
from .adapters.AdapterBase import AdapterBase


class AdapterThreadLockingWrapper:
    _threading_lock: threading.Lock = threading.Lock()

    def __init__(self, adapter: AdapterBase):
        self._adapter: AdapterBase = adapter

    def connection_opened(self, client_address: Union[ipaddress.IPv4Address, ipaddress.IPv6Address], client_port: int) -> None:
        AdapterThreadLockingWrapper._threading_lock.acquire()
        try:
            self._adapter.connection_opened(client_address, client_port)
        finally:
            AdapterThreadLockingWrapper._threading_lock.release()

    def read_only_mode_allowed(self) -> bool:
        AdapterThreadLockingWrapper._threading_lock.acquire()
        try:
            return self._adapter.read_only_mode_allowed()
        finally:
            AdapterThreadLockingWrapper._threading_lock.release()

    def verify_login_credentials(self, username: str, password: str) -> bool:
        AdapterThreadLockingWrapper._threading_lock.acquire()
        try:
            return self._adapter.verify_login_credentials(username, password)
        finally:
            AdapterThreadLockingWrapper._threading_lock.release()

    def login_successful(self, username: str, read_only: bool) -> None:
        AdapterThreadLockingWrapper._threading_lock.acquire()
        try:
            self._adapter.login_successful(username, read_only)
        finally:
            AdapterThreadLockingWrapper._threading_lock.release()

    def get_message_count(self) -> int:
        AdapterThreadLockingWrapper._threading_lock.acquire()
        try:
            return self._adapter.get_message_count()
        finally:
            AdapterThreadLockingWrapper._threading_lock.release()

    def get_message_content(self, index: int, encoding: str) -> str:
        AdapterThreadLockingWrapper._threading_lock.acquire()
        try:
            return self._adapter.get_message_content(index, encoding)
        finally:
            AdapterThreadLockingWrapper._threading_lock.release()

    def get_message_unique_id(self, index: int) -> str:
        AdapterThreadLockingWrapper._threading_lock.acquire()
        try:
            return self._adapter.get_message_unique_id(index)
        finally:
            AdapterThreadLockingWrapper._threading_lock.release()

    def is_message_marked_as_deleted(self, index: int) -> bool:
        AdapterThreadLockingWrapper._threading_lock.acquire()
        try:
            return self._adapter.is_message_marked_as_deleted(index)
        finally:
            AdapterThreadLockingWrapper._threading_lock.release()

    def mark_message_as_deleted(self, index: int) -> None:
        AdapterThreadLockingWrapper._threading_lock.acquire()
        try:
            self._adapter.mark_message_as_deleted(index)
        finally:
            AdapterThreadLockingWrapper._threading_lock.release()

    def unmark_messages_marked_as_deleted(self) -> None:
        AdapterThreadLockingWrapper._threading_lock.acquire()
        try:
            self._adapter.unmark_messages_marked_as_deleted()
        finally:
            AdapterThreadLockingWrapper._threading_lock.release()

    def commit_deletions(self) -> None:
        AdapterThreadLockingWrapper._threading_lock.acquire()
        try:
            self._adapter.commit_deletions()
        finally:
            AdapterThreadLockingWrapper._threading_lock.release()

    def connection_closed(self) -> None:
        AdapterThreadLockingWrapper._threading_lock.acquire()
        try:
            self._adapter.connection_closed()
        finally:
            AdapterThreadLockingWrapper._threading_lock.release()
