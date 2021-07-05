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
import threading


class PerUserExclusivityEnsurer(object):
    class _Client:
        def __init__(self, connection_id: int, username: str, read_only: bool):
            self.connection_id: int = connection_id
            self.username: str = username
            self.read_only: bool = read_only

    _threading_lock: threading.Lock = threading.Lock()
    _singleton_instance: Optional[PerUserExclusivityEnsurer] = None

    def __new__(cls, *args, **kwargs) -> PerUserExclusivityEnsurer:
        PerUserExclusivityEnsurer._threading_lock.acquire()
        try:
            if cls._singleton_instance is None:
                cls._singleton_instance = super().__new__(cls, *args, *kwargs)

            return cls._singleton_instance
        finally:
            PerUserExclusivityEnsurer._threading_lock.release()

    def __init__(self):
        super().__init__()

        PerUserExclusivityEnsurer._threading_lock.acquire()
        try:
            self._clients: List[PerUserExclusivityEnsurer._Client] = []
        finally:
            PerUserExclusivityEnsurer._threading_lock.release()

    def add_client(self, connection_id: int, username: str, read_only: bool) -> bool:
        PerUserExclusivityEnsurer._threading_lock.acquire()
        try:
            return self._add_client_locked(connection_id, username, read_only)
        finally:
            PerUserExclusivityEnsurer._threading_lock.release()

    def _add_client_locked(self, connection_id: int, username: str, read_only: bool) -> bool:
        for client in self._clients:
            # There can either be ONLY ONE read-write session or ANY NUMBER of read-only sessions per user at the same time.
            if (username == client.username) and not (read_only and client.read_only):
                return False

        new_client = PerUserExclusivityEnsurer._Client(connection_id, username, read_only)
        self._clients.append(new_client)

        return True

    def remove_client(self, connection_id: int) -> None:
        PerUserExclusivityEnsurer._threading_lock.acquire()
        try:
            self._remove_client_locked(connection_id)
        finally:
            PerUserExclusivityEnsurer._threading_lock.release()

    def _remove_client_locked(self, connection_id: int) -> None:
        self._clients = [client for client in self._clients if connection_id != client.connection_id]
