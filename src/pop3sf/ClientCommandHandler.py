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


from typing import List, Tuple
import functools
from .Settings import Settings
from .Auxiliaries import Auxiliaries
from .POP3ResponseCodes import POP3ResponseCodes
from .ClientStatusHolder import ClientStatusHolder
from .SendDataToClientException import SendDataToClientException


class ClientCommandHandler:
    def __init__(self, client_status: ClientStatusHolder, command: str, args: List[str]):
        self._client_status: ClientStatusHolder = client_status

        self._command: str = command
        self._args: List[str] = args

    def handle_command(self) -> None:
        if self._client_status.authenticated:
            self._handle_transaction_state_command()
        else:
            self._handle_authorization_state_command()

    def _handle_authorization_state_command(self) -> None:
        # The APOP authentication method is not supported, as it's not widely used and it requires the password to be stored in plaintext.

        command_handler = {
            "CAPA": self._command_capa,
            "QUIT": self._command_quit_in_authorization_state,
            "XPRO": self._command_xpro,
            "UTF8": self._command_utf8,
            "LANG": self._command_lang,
            "USER": self._command_user,
            "PASS": self._command_pass
        }.get(self._command, self._invalid_command)

        command_handler()

    def _handle_transaction_state_command(self) -> None:
        command_handler = {
            "CAPA": self._command_capa,
            "LANG": self._command_lang,
            "NOOP": self._command_noop,
            "QUIT": self._command_quit_in_transaction_state,
            "STAT": self._command_stat,
            "LIST": self._command_list,
            "UIDL": self._command_uidl,
            "RETR": self._command_retr,
            "TOP": self._command_top,
            "DELE": self._command_dele,
            "RSET": self._command_rset
        }.get(self._command, self._invalid_command)

        command_handler()

    def _invalid_command(self) -> None:
        if Settings.MAX_INVALID_COMMANDS_PER_SESSION >= 0:
            self._client_status.invalid_command_count += 1
            if self._client_status.invalid_command_count > Settings.MAX_INVALID_COMMANDS_PER_SESSION:
                raise SendDataToClientException.err("Too many invalid commands").close_connection_after_sending_data()

        raise SendDataToClientException.err("Invalid command")

    def _command_capa(self) -> None:
        # The server supports PIPELINING, but it uses blocking writes, sometimes with huge amounts of data (e.g. RETR; see RFC 2449):
        #  "If either the client or server uses blocking writes, it MUST not exceed the window size of the underlying transport layer."

        self._check_argument_count((0,))

        capabilities = [
            "USER",
            "TOP",
            "UIDL",
            "RESP-CODES",
            "AUTH-RESP-CODE",
            "UTF8 USER",
            "LANG",
            "IMPLEMENTATION POP3SF"
        ]

        if self._client_status.adapter_helper.read_only_mode_allowed():
            capabilities.append("X-POP3SF-READ-ONLY")  # non-standard

        raise SendDataToClientException.ok_multiline("Listing all capabilities", "\r\n".join(capabilities))

    def _command_quit_in_authorization_state(self) -> None:
        self._check_argument_count((0,))
        raise SendDataToClientException.ok("Session is ending (nobody was logged in)").close_connection_after_sending_data()

    def _command_quit_in_transaction_state(self) -> None:
        self._check_argument_count((0,))

        self._client_status.adapter_helper.commit_deletions()

        raise SendDataToClientException.ok("Session is ending (an user was logged in)").close_connection_after_sending_data()

    def _command_xpro(self) -> None:
        self._check_argument_count((0,))

        if not self._client_status.adapter_helper.read_only_mode_allowed():
            raise SendDataToClientException.err("Read-only mailbox access mode is not allowed", pop3_response_code=POP3ResponseCodes.Codes.X_POP3SF_READ_ONLY)

        self._client_status.read_only_mailbox_access = True

        raise SendDataToClientException.ok("Mailbox access mode switched to read-only")

    def _command_utf8(self) -> None:
        self._check_argument_count((0,))

        self._client_status.encoding = "utf-8"

        raise SendDataToClientException.ok("UTF-8 support was enabled for this connection")

    def _command_lang(self) -> None:
        # The server probably won't ever support any other languages than English, so this command is implemented basically only because of the RFC 6856 compliance.

        self._check_argument_count((0, 1))

        if len(self._args) == 0:
            language_list = (
                "en English",
            )

            raise SendDataToClientException.ok_multiline("Listing all languages", "\r\n".join(language_list))

        if self._args[0] in ("*", "en"):
            self._client_status.custom_language = "en"

            raise SendDataToClientException.ok("The response text language was changed to English")

        raise SendDataToClientException.err("Invalid language tag")

    def _command_noop(self) -> None:
        self._check_argument_count((0,))
        raise SendDataToClientException.ok("Nothing happened")

    def _command_user(self) -> None:
        self._check_argument_count((1,))
        username = self._args[0]

        self._client_status.authorization_state_username = username

        raise SendDataToClientException.ok("Username accepted")

    def _command_pass(self) -> None:
        # self._check_argument_count((1,))

        username = self._client_status.authorization_state_username
        if username is None:
            raise SendDataToClientException.err("No username was sent using the USER command", pop3_response_code=POP3ResponseCodes.Codes.AUTH)

        # RFC 1939: "Since the PASS command has exactly one argument, a POP3 server may treat spaces in the argument as part of the password, instead of as argument separators."
        # If the str.join() function is used on an empty list, it outputs an empty string.
        password = " ".join(self._args)
        if not password:
            raise SendDataToClientException.err("Empty password", pop3_response_code=POP3ResponseCodes.Codes.AUTH)

        if not self._client_status.adapter_helper.verify_login_credentials(username, password):
            raise SendDataToClientException.err("Incorrect username or password", pop3_response_code=POP3ResponseCodes.Codes.AUTH)

        self._client_status.authentication_successful(username)

        response = "User successfully logged in"
        if self._client_status.read_only_mailbox_access:
            response += " (read-only)"

        raise SendDataToClientException.ok(response)

    def _command_stat(self) -> None:
        self._check_argument_count((0,))

        message_count = self._client_status.adapter_helper.get_undeleted_message_count()
        total_size = functools.reduce(lambda carry, item: carry + item[1], self._client_status.adapter_helper.get_all_undeleted_messages_sizes(), 0)

        raise SendDataToClientException.ok_human_unreadable("{} {}".format(message_count, total_size))

    def _command_list(self) -> None:
        self._check_argument_count((0, 1))

        # list all messages' sizes
        if len(self._args) == 0:
            listing = "\r\n".join(["{} {}".format(message_number, size) for message_number, size in self._client_status.adapter_helper.get_all_undeleted_messages_sizes()])

            raise SendDataToClientException.ok_multiline("Listing all messages' sizes", listing)

        # list specific message size
        index = self._parse_message_number_argument_to_index(self._args[0])
        message_size = self._client_status.adapter_helper.get_message_size(index)

        raise SendDataToClientException.ok_human_unreadable("{} {}".format(Auxiliaries.convert_index_to_message_number(index), message_size))

    def _command_uidl(self) -> None:
        self._check_argument_count((0, 1))

        # list all messages' unique ids
        if len(self._args) == 0:
            listing = "\r\n".join(["{} {}".format(message_number, unique_id) for message_number, unique_id in self._client_status.adapter_helper.get_all_undeleted_messages_unique_ids()])

            raise SendDataToClientException.ok_multiline("Listing all messages' unique IDs", listing)

        # list specific message unique id
        index = self._parse_message_number_argument_to_index(self._args[0])
        message_unique_id = self._client_status.adapter_helper.get_message_unique_id(index)

        raise SendDataToClientException.ok_human_unreadable("{} {}".format(Auxiliaries.convert_index_to_message_number(index), message_unique_id))

    def _command_retr(self) -> None:
        self._check_argument_count((1,))
        index = self._parse_message_number_argument_to_index(self._args[0])

        message_content = self._client_status.adapter_helper.get_message_content(index)

        raise SendDataToClientException.ok_multiline("Sending the message's content", message_content)

    def _command_top(self) -> None:
        self._check_argument_count((2,))
        index = self._parse_message_number_argument_to_index(self._args[0])
        n = self._parse_number_of_lines_argument(self._args[1])

        requested_message_content = self._client_status.adapter_helper.get_headers_and_first_n_lines_of_a_message(index, n)

        raise SendDataToClientException.ok_multiline("Sending the message's partial content", requested_message_content, force_add_crlf_before_multiline_termination_octet=(n == 0))

    def _command_dele(self) -> None:
        self._check_argument_count((1,))
        index = self._parse_message_number_argument_to_index(self._args[0])

        self._client_status.adapter_helper.mark_message_as_deleted(index)

        raise SendDataToClientException.ok("The message was marked as deleted")

    def _command_rset(self) -> None:
        self._check_argument_count((0,))

        self._client_status.adapter_helper.unmark_messages_marked_as_deleted()

        raise SendDataToClientException.ok("Messages marked as deleted were unmarked")

    def _check_argument_count(self, expected_argument_counts: Tuple[int, ...]) -> None:
        if len(self._args) not in expected_argument_counts:
            raise SendDataToClientException.err("Invalid argument count")

    def _parse_message_number_argument_to_index(self, message_number: str) -> int:
        try:
            index = int(message_number) - 1
        except ValueError:
            raise SendDataToClientException.err("Invalid message number (must be an integer)")

        if index < 0 or index >= self._client_status.adapter_helper.get_message_count():
            raise SendDataToClientException.err("Invalid message number (out of range)")

        if self._client_status.adapter_helper.is_message_marked_as_deleted(index):
            raise SendDataToClientException.err("Invalid message number (message marked as deleted)")

        return index

    def _parse_number_of_lines_argument(self, number_of_lines: str) -> int:
        # Used by the TOP command

        try:
            n = int(number_of_lines)
        except ValueError:
            raise SendDataToClientException.err("Invalid number of lines (must be an integer)")

        if n < 0:
            raise SendDataToClientException.err("Invalid number of lines (out of range)")

        return n
