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


from typing import List, Union
import os
import re
import socket
import ssl
import pwd
import grp


class Auxiliaries:
    class DropRootPrivilegesInfo:
        def __init__(self, drop_to_user: str, drop_to_group: str):
            self.drop_to_user: str = drop_to_user
            self.drop_to_group: str = drop_to_group

    @staticmethod
    def split_lines_without_discarding_empty_lines(string: str) -> List[str]:
        # At the moment, this is only a wrapper function for future expansion.

        # Not using st.splitlines() because it discards the last line, if it's empty.
        return re.split(r'\r\n|\r|\n', string)

    @staticmethod
    def convert_index_to_message_number(index: int) -> int:
        # At the moment, this is only a wrapper function for future expansion.
        return index + 1

    @staticmethod
    def get_server_sockets_address_as_string(server_socket: Union[socket.socket, ssl.SSLSocket]) -> str:
        # In case of a IPv6 socket, the server_addr tuple has 4 elements.
        server_addr = server_socket.getsockname()[0:2]

        return str(server_addr)

    @staticmethod
    def change_working_directory_and_umask() -> None:
        # This method was moved here from the POP3SF class because it's unrelated to the class's main purpose
        # (listening on server sockets and accepting client connections from them), although it only gets called from there.
        from .Settings import Settings  # Circular import prevention

        if Settings.UMASK is not None:
            os.umask(Settings.UMASK)

        if Settings.WORKING_DIRECTORY is not None:
            os.makedirs(Settings.WORKING_DIRECTORY, exist_ok=True)

            os.chdir(Settings.WORKING_DIRECTORY)

    @staticmethod
    def drop_root_privileges_if_needed() -> None:
        # This method was moved here from the POP3SF class because it's unrelated to the class's main purpose
        # (listening on server sockets and accepting client connections from them), although it only gets called from there.
        from .Settings import Settings  # Circular import prevention

        if (Settings.DROP_ROOT_PRIVILEGES is not None) and (os.geteuid() == 0):
            new_gid = grp.getgrnam(Settings.DROP_ROOT_PRIVILEGES.drop_to_group).gr_gid
            new_uid = pwd.getpwnam(Settings.DROP_ROOT_PRIVILEGES.drop_to_user).pw_uid

            os.setgroups([])
            os.setgid(new_gid)
            os.setuid(new_uid)
