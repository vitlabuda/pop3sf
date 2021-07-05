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


import string
import os
import os.path
import time
import re
import random
import fcntl
import bcrypt
import email.message
from MultiuserAdapterToolBase import MultiuserAdapterToolBase


class DirectoryMultiuserAdapterTool(MultiuserAdapterToolBase):
    class ForbiddenUsernameException(MultiuserAdapterToolBase.MultiuserAdapterToolException):
        def __init__(self, username: str):
            super().__init__("The username '{}' is contains forbidden characters!".format(username))

    _PASSWORD_FILE_NAME: str = ".pop3sf_password_bcrypt"

    def __init__(self, directory_path: str):
        self._directory_path: str = directory_path

        os.makedirs(directory_path, exist_ok=True)

    def _validate_username_and_get_per_user_directory_path(self, username: str) -> str:
        if not re.match(r'^[0-9A-Za-z_-]{1,64}$', username):
            raise DirectoryMultiuserAdapterTool.ForbiddenUsernameException(username)

        return os.path.join(self._directory_path, username)

    def does_user_exist(self, username: str) -> bool:
        per_user_directory_path = self._validate_username_and_get_per_user_directory_path(username)

        return os.path.exists(per_user_directory_path)

    def add_user(self, username: str, password: str) -> None:
        if self.does_user_exist(username):
            raise DirectoryMultiuserAdapterTool.UserAlreadyExistsException(username)

        per_user_directory_path = self._validate_username_and_get_per_user_directory_path(username)
        os.mkdir(per_user_directory_path)

        self.change_user_password(username, password)

    def change_user_password(self, username: str, new_password: str) -> None:
        if not self.does_user_exist(username):
            raise DirectoryMultiuserAdapterTool.UserDoesNotExistException(username)

        per_user_directory_path = self._validate_username_and_get_per_user_directory_path(username)
        password_file_path = os.path.join(per_user_directory_path, DirectoryMultiuserAdapterTool._PASSWORD_FILE_NAME)

        password_bcrypt = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())
        with open(password_file_path, "w") as file:
            fcntl.flock(file.fileno(), fcntl.LOCK_EX)
            file.write(password_bcrypt.decode("utf-8"))
            fcntl.flock(file.fileno(), fcntl.LOCK_UN)

    def add_plaintext_message(self, username: str, message: str) -> None:
        self._write_message_to_file(message, username, "txt")

    def add_email_message(self, username: str, message: email.message.Message) -> None:
        self._write_message_to_file(str(message), username, "eml")

    def _write_message_to_file(self, text: str, username: str, filename_extension: str) -> None:
        if not self.does_user_exist(username):
            raise DirectoryMultiuserAdapterTool.UserDoesNotExistException(username)

        per_user_directory_path = self._validate_username_and_get_per_user_directory_path(username)
        filepath = os.path.join(per_user_directory_path, self._generate_filename(filename_extension))

        with open(filepath, "w") as file:
            fcntl.flock(file.fileno(), fcntl.LOCK_EX)
            file.write(text)
            fcntl.flock(file.fileno(), fcntl.LOCK_UN)

    def _generate_filename(self, filename_extension: str) -> str:
        random_string = "".join(random.choices(string.digits + string.ascii_lowercase, k=40))

        return "{}_{}.{}".format(time.time_ns(), random_string, filename_extension)
