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
import os
import os.path
import glob
import fcntl
import hashlib
from .AdapterAuxiliaries import AdapterAuxiliaries
from .AdapterBase import AdapterBase


class DirectoryAdapterBase(AdapterBase, metaclass=abc.ABCMeta):
    class _MessageIndexEntry:
        def __init__(self, path: str, last_modified_epoch: float, is_plaintext: bool):
            self.path: str = path
            self.last_modified_epoch: float = last_modified_epoch
            self.last_modified: time.struct_time = time.gmtime(last_modified_epoch)
            self.is_plaintext: bool = is_plaintext
            self.marked_as_deleted: bool = False

    def __init__(self, directory_path: str):
        self._directory_path: str = directory_path

        os.makedirs(directory_path, exist_ok=True)

        self._message_index: List[DirectoryAdapterBase._MessageIndexEntry] = []

    def login_successful(self, username: str, read_only: bool) -> None:
        self._message_index = self._generate_message_index()

    @abc.abstractmethod
    def _generate_message_index(self) -> List[DirectoryAdapterBase._MessageIndexEntry]:
        raise NotImplementedError("The _generate_message_index() method must be overridden prior to calling it!")

    def get_message_count(self) -> int:
        return len(self._message_index)

    def get_message_content(self, index: int, encoding: str) -> str:
        message = self._message_index[index]

        with open(message.path) as file:
            fcntl.flock(file.fileno(), fcntl.LOCK_SH)
            content = file.read()
            fcntl.flock(file.fileno(), fcntl.LOCK_UN)

        if message.is_plaintext:
            subject = "Plaintext file {}".format(self.get_message_unique_id(index)[0:8])
            from_to = AdapterAuxiliaries.generate_from_to_email_address("nobody")

            return AdapterAuxiliaries.wrap_plaintext_in_email(content, subject, from_to, from_to, message.last_modified)

        return content

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
                os.remove(message.path)

    def get_message_unique_id(self, index: int) -> str:
        # The file's path is always unique and shouldn't change (at least this program doesn't move the file)
        #  The last modified timestamp is used to detect changes
        message = self._message_index[index]

        hashed_string = "{}{}".format(message.path, message.last_modified_epoch).encode("utf-8")

        return hashlib.sha256(hashed_string).hexdigest()

    def _generate_message_index_using_full_directory_path(self, full_directory_path: str) -> List[DirectoryAdapterBase._MessageIndexEntry]:
        message_index = []

        paths = sorted(glob.glob(os.path.join(full_directory_path, "*")))
        absolute_file_paths_iter = filter(os.path.isfile, map(os.path.abspath, paths))

        for filepath in absolute_file_paths_iter:
            last_modified_epoch = os.stat(filepath).st_mtime

            if filepath.endswith(".eml"):
                message_index.append(DirectoryAdapterBase._MessageIndexEntry(filepath, last_modified_epoch, False))
            elif filepath.endswith(".txt"):
                message_index.append(DirectoryAdapterBase._MessageIndexEntry(filepath, last_modified_epoch, True))

        # The messages are sorted by last modification dates of their files; thus, if a new message is added, it will be at the end of the message list.
        # If more messages have the same modification date (this is very rare, though), those messages are sorted by their filenames.
        message_index.sort(key=lambda item: item.last_modified_epoch)

        return message_index
