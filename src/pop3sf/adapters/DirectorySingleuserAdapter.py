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
from .DirectoryAdapterBase import DirectoryAdapterBase


class DirectorySingleuserAdapter(DirectoryAdapterBase):
    """
    This adapter relays messages from a filesystem directory to the POP3 server.

    The valid username and bcrypt-hashed password is passed to the constructor, just as the path of the directory where the messages will be taken from.
    Message files with .eml extension will be relayed to the client without modification, whilst .txt files will be wrapped into an email's body; other files are ignored.

    An external program must not rename, move, delete or write to the message files!
    It can add them at any time, but it must do so atomically - it must lock the files using flock() while writing the message!
    """

    def __init__(self, username: str, password_bcrypt: str, directory_path: str):
        super().__init__(directory_path)

        self._username: str = username
        self._password_bcrypt: str = password_bcrypt

    def _generate_message_index(self) -> List[DirectoryAdapterBase._MessageIndexEntry]:
        return self._generate_message_index_using_full_directory_path(self._directory_path)

    def verify_login_credentials(self, username: str, password: str) -> bool:
        return username == self._username and AdapterAuxiliaries.check_bcrypt_password(password, self._password_bcrypt)
