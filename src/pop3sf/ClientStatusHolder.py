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


from typing import Optional
import threading
from .Settings import Settings
from .GlobalResources import GlobalResources
from .POP3ResponseCodes import POP3ResponseCodes
from .ClientConnectionInfoHolder import ClientConnectionInfoHolder
from .AdapterHelperWrapper import AdapterHelperWrapper
from .SendDataToClientException import SendDataToClientException
from .adapters.AdapterBase import AdapterBase


class ClientStatusHolder:
    _threading_lock: threading.Lock = threading.Lock()

    def __init__(self, connection_info: ClientConnectionInfoHolder):
        self.connection_info: ClientConnectionInfoHolder = connection_info
        self.adapter_helper: AdapterHelperWrapper = AdapterHelperWrapper(self._safely_get_adapter(), self)

        self.authenticated: bool = False
        self.username: Optional[str] = None
        self.authorization_state_username: Optional[str] = None  # Used to save the username that the client provided using the USER command before sending the PASS command.
        self.read_only_mailbox_access: bool = False

        self.encoding: str = "ascii"
        self.custom_language: Optional[str] = None

        self.invalid_command_count: int = 0  # Can be used to disconnect the client if they send too many invalid commands
        self.invalid_password_count: int = 0  # Can be used to disconnect the client if they send too many incorrect passwords

    def _safely_get_adapter(self) -> AdapterBase:
        ClientStatusHolder._threading_lock.acquire()
        try:
            return Settings.get_adapter()
        finally:
            ClientStatusHolder._threading_lock.release()

    def authentication_successful(self, username: str) -> None:
        if not GlobalResources.get_exclusivity_ensurer().add_client(self.connection_info.connection_id, username, self.read_only_mailbox_access):
            raise SendDataToClientException.err("This user is logged in in another session", pop3_response_code=POP3ResponseCodes.Codes.IN_USE)

        self.authenticated = True
        self.username = username
        self.authorization_state_username = None

        self.adapter_helper.login_successful(username)

        GlobalResources.get_logger().debug("Client from {} logged in as \"{}\".".format(self.connection_info.get_client_address_as_string(), username))
