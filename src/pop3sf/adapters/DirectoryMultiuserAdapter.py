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
import os
import os.path
import re
import fcntl
from .AdapterAuxiliaries import AdapterAuxiliaries
from .DirectoryAdapterBase import DirectoryAdapterBase


class DirectoryMultiuserAdapter(DirectoryAdapterBase):
    """
    This adapter is similar to DirectoryAdapter, but it offers multi-user capabilities.

    Instead of passing the username and bcrypt-hashed password to the constructor, the credentials are loaded from a file in a per-user directory.
    The directory, whose path is passed to the constructor, contains directories whose names are used as usernames.
     The folder name (username) must match this regular expression: ^[0-9A-Za-z_-]{1,64}$
    Each of these directories contains a file named ".pop3sf_password_bcrypt" that contains a bcrypt-hashed password for the user and the messages themselves.
    Message files with .eml extension will be relayed to the client without modification, whilst .txt files will be wrapped into an email's body; other files are ignored.

    An external program must not rename, move, delete or write to the message files!
    It can add them at any time, but it must do so atomically - it must lock the files using flock() while writing the message!
    """

    _PASSWORD_FILE_NAME: str = ".pop3sf_password_bcrypt"

    def __init__(self, directory_path: str):
        super().__init__(directory_path)

        self._per_user_directory_path: Optional[str] = None

    def _generate_message_index(self) -> List[DirectoryAdapterBase._MessageIndexEntry]:
        assert self._per_user_directory_path is not None

        return self._generate_message_index_using_full_directory_path(self._per_user_directory_path)

    def verify_login_credentials(self, username: str, password: str) -> bool:
        # Check if the username's length and whether it contains only an allowed set of characters (if all characters were allowed, the program would be vulnerable to directory traversal)
        if not re.match(r'^[0-9A-Za-z_-]{1,64}$', username):
            return False

        # Get the per-user directory path
        per_user_directory_path = os.path.join(self._directory_path, username)

        # Get the path of the file that contains a bcrypt-hashed password and check if it exists
        password_file_path = os.path.join(per_user_directory_path, DirectoryMultiuserAdapter._PASSWORD_FILE_NAME)
        if not os.path.isfile(password_file_path):  # This also obviously checks whether the per-user directory exists
            return False

        # Load the bcrypt-hashed password from the file
        with open(password_file_path) as file:
            fcntl.flock(file.fileno(), fcntl.LOCK_SH)
            password_bcrypt = file.read().strip()
            fcntl.flock(file.fileno(), fcntl.LOCK_UN)

        # Check the password
        is_password_correct = AdapterAuxiliaries.check_bcrypt_password(password, password_bcrypt)
        if not is_password_correct:
            return False

        # Save the per-user directory path and return
        self._per_user_directory_path = per_user_directory_path

        return True
