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
from typing import Optional
from .Auxiliaries import Auxiliaries
from .POP3ResponseCodes import POP3ResponseCodes


class SendDataToClientException(Exception):
    INTERNAL_SERVER_ERROR_MESSAGE: str = "Internal server error"

    def __init__(self, success: bool, pop3_response_code: POP3ResponseCodes.TYPE_ANNOTATION, message: str, is_message_human_readable: bool, message_multiline: Optional[str], force_add_crlf_before_multiline_termination_octet: bool):
        super().__init__("The server wants to send a response to a client.")

        self._success: bool = success
        self._pop3_response_code: POP3ResponseCodes.TYPE_ANNOTATION = pop3_response_code
        self._message: str = message
        self._is_message_human_readable: bool = is_message_human_readable
        self._message_multiline: Optional[str] = message_multiline
        self._force_add_crlf_before_multiline_termination_octet: bool = force_add_crlf_before_multiline_termination_octet

        # If you want to close the connection to the client immediately after sending data carried by the instance, set this to True from the outside.
        self.should_close_connection_after_sending_data: bool = False

    @classmethod
    def ok(cls, human_readable_message: str) -> SendDataToClientException:
        return cls(True, None, human_readable_message, True, None, False)

    @classmethod
    def ok_human_unreadable(cls, human_unreadable_message: str) -> SendDataToClientException:
        return cls(True, None, human_unreadable_message, False, None, False)

    @classmethod
    def ok_multiline(cls, human_readable_message: str, message_multiline: str, force_add_crlf_before_multiline_termination_octet: bool = False) -> SendDataToClientException:
        return cls(True, None, human_readable_message, True, message_multiline, force_add_crlf_before_multiline_termination_octet)

    @classmethod
    def err(cls, human_readable_message: str, pop3_response_code: POP3ResponseCodes.TYPE_ANNOTATION = None) -> SendDataToClientException:
        return cls(False, pop3_response_code, human_readable_message, True, None, False)

    @classmethod
    def err_internal(cls) -> SendDataToClientException:
        return cls.err(cls.INTERNAL_SERVER_ERROR_MESSAGE, pop3_response_code=POP3ResponseCodes.Codes.SYS_TEMP)

    @classmethod
    def err_read_only_mailbox_access(cls) -> SendDataToClientException:
        return cls.err("The mailbox access mode is set to read-only", pop3_response_code=POP3ResponseCodes.Codes.X_POP3SF_READ_ONLY)

    def close_connection_after_sending_data(self) -> SendDataToClientException:
        self.should_close_connection_after_sending_data = True

        return self

    # The client_status argument must be a ClientStatusHolder variable (could not annotate due to a circular import).
    def build_message(self, client_status) -> bytes:
        message_string = self._compose_the_first_line_of_the_message(client_status.custom_language)

        if self._message_multiline is not None:
            message_string += self._compose_next_lines_of_a_multiline_message()

            if self._force_add_crlf_before_multiline_termination_octet or not message_string.endswith("\r\n"):
                message_string += "\r\n"
            message_string += ".\r\n"

        return message_string.encode(client_status.encoding)

    def _compose_the_first_line_of_the_message(self, language: Optional[str]) -> str:
        first_line = "+OK " if self._success else "-ERR "

        if self._pop3_response_code is not None:
            first_line += "[{}] ".format(self._pop3_response_code.value)

        # It seems that in the RFC standards, it isn't clearly specified whether the response code or the language tag should be first.
        if (language is not None) and self._is_message_human_readable:
            first_line += "{} ".format(language)

        first_line += self._message
        first_line += "\r\n"

        return first_line

    def _compose_next_lines_of_a_multiline_message(self) -> str:
        # The reason why this method works with the next lines as string and not as a list of strings (lines) is that there would be no guarantee
        # that the there are no line breaks in a single list item, although it would be more effective in terms of computing power
        # (there would be no need to split it when byte-stuffing it).
        # However, since we use Python which is slow by itself, I guess there's no need to be upset about this.

        # This method also guarantees that all newline characters will be canonicalized to \r\n (CRLF), as required by POP3.

        lines = Auxiliaries.split_lines_without_discarding_empty_lines(self._message_multiline)
        lines = "\r\n".join(map(lambda line: ("." + line if line.startswith(".") else line), lines))

        return lines
