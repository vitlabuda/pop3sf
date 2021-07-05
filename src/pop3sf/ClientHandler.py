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


from typing import Any, List, Tuple, Generator
import select
from .Settings import Settings
from .Auxiliaries import Auxiliaries
from .POP3ResponseCodes import POP3ResponseCodes
from .GlobalResources import GlobalResources
from .ClientStatusHolder import ClientStatusHolder
from .ClientCommandHandler import ClientCommandHandler
from .ClientConnectionInfoHolder import ClientConnectionInfoHolder
from .SendDataToClientException import SendDataToClientException
from .CloseConnectionException import CloseConnectionException
from .POP3SFRuntimeError import POP3SFRuntimeError
from .adapters.AdapterCloseConnectionException import AdapterCloseConnectionException


# All methods of this class, including __init__, get executed on a separate (per-client) thread.
# The client socket will automatically be closed when the handle_client method finishes.
class ClientHandler:
    _RECEIVE_SIZE: int = 16384
    _RECEIVE_BUFFER_MAX_SIZE: int = 262144

    # If OSError was raised, the client connection probably died.
    _EXPECTED_EXCEPTIONS: Tuple[Any, ...] = (CloseConnectionException, AdapterCloseConnectionException, OSError)

    @classmethod
    def initialize_client_handler(cls, connection_info: ClientConnectionInfoHolder) -> None:
        # This method is also called in a separate (per-client) thread.
        GlobalResources.get_logger().debug("Client connected from {}.".format(connection_info.get_client_address_as_string()))

        client_status = None
        try:
            client_status = ClientStatusHolder(connection_info)
            client_status.adapter_helper.connection_opened()

            client_handler = cls(client_status)
            client_handler.handle_client()

        except Exception as e:
            cls._handle_exception_in_client_handler_initializer(e)

        finally:
            try:
                # Close the connection, no matter what happened
                connection_info.socket.close()
            except OSError:
                pass

            try:
                # Inform the adapter about the connection closure
                if client_status is not None:
                    client_status.adapter_helper.connection_closed()
            except Exception as e:
                cls._handle_exception_in_client_handler_initializer(e)
            finally:
                # Remove the client from the exclusivity ensurer
                GlobalResources.get_exclusivity_ensurer().remove_client(connection_info.connection_id)

                # Send a log message
                GlobalResources.get_logger().debug("Client from {} disconnected.".format(connection_info.get_client_address_as_string()))

    @classmethod
    def _handle_exception_in_client_handler_initializer(cls, e: Exception) -> None:
        if not Settings.DEBUG:
            return

        for class_ in cls._EXPECTED_EXCEPTIONS:
            if isinstance(e, class_):
                break
        else:
            raise e

    def __init__(self, client_status: ClientStatusHolder):
        client_status.connection_info.socket.settimeout(Settings.CLIENT_TIMEOUT)

        self._client_status: ClientStatusHolder = client_status

    def handle_client(self) -> None:
        self._send_greeting_to_client()

        for line in self._line_receiver_generator():
            self._parse_line_and_call_command_handler(line)

    def _send_greeting_to_client(self) -> None:
        self._encode_and_send_data_to_client(SendDataToClientException.ok("The POP3 server is ready (POP3SF)"))

    def _line_receiver_generator(self) -> Generator:
        # Documentation: "The socket must be in blocking mode; it can have a timeout, but the file object’s internal buffer may end up in an inconsistent state if a timeout occurs."
        # --> The reason why socket.makefile() is not used and a custom buffering implementation wrapping around the recv() syscall is used instead (this method).

        buffer = ""

        while True:
            split_buffer = Auxiliaries.split_lines_without_discarding_empty_lines(buffer)
            buffer = split_buffer.pop()
            for line in split_buffer:
                yield line

            received_data = self._receive_all_buffered_data_from_socket()

            try:
                # Even if the UTF-8 mode isn't active, it's possible to receive the data as UTF-8, because all ASCII characters can be decoded as UTF-8.
                buffer += received_data.decode("utf-8")
            except UnicodeDecodeError:
                raise CloseConnectionException("The received data contained an invalid UTF-8 character.")

            if len(buffer) > ClientHandler._RECEIVE_BUFFER_MAX_SIZE:
                raise CloseConnectionException("The received data buffer is too large!")

    def _receive_all_buffered_data_from_socket(self) -> bytes:
        # If the whole buffer wasn't received, a whole multibyte UTF-8 character would not have to be received which would cause a decoding error.
        # Although one might say that the probability of this happening is next to nothing and that this is pure over-engineering,
        #  I had problems with this exact thing while testing this program (and trust me, it was quite hard to figure it out).

        received_data = self._receive_data_from_socket()  # If no data is buffered, it will wait for some data to be received from the remote host.

        # I couldn't get the socket.MSG_DONTWAIT option to work for some reason, so I decided to use this approach with poll().
        poll_object = select.poll()
        poll_object.register(self._client_status.connection_info.socket, select.POLLIN)

        while True:
            poll_result = poll_object.poll(0)
            if not poll_result:
                break

            socket_events = poll_result[0][1]
            if socket_events == select.POLLIN:
                received_data += self._receive_data_from_socket()
            else:
                raise CloseConnectionException("The poll() syscall returned an unexpected/erroneous event - the connection is probably dead.")

            if len(received_data) > ClientHandler._RECEIVE_BUFFER_MAX_SIZE:
                raise CloseConnectionException("The received data buffer is too large!")

        return received_data

    def _receive_data_from_socket(self) -> bytes:
        received_data = self._client_status.connection_info.socket.recv(ClientHandler._RECEIVE_SIZE)
        if not received_data:
            raise CloseConnectionException("The received data is empty - the connection is probably dead.")

        return received_data

    def _parse_line_and_call_command_handler(self, line: str) -> None:
        try:
            command, args = self._parse_command(line)

            self._call_command_handler(command, args)

        except SendDataToClientException as e:
            self._encode_and_send_data_to_client(e)
        else:
            raise POP3SFRuntimeError("No response to a POP3 client command was sent by the command handler!")

    def _parse_command(self, line: str) -> Tuple[str, List[str]]:
        line = line.strip()

        if not line:
            raise SendDataToClientException.err("Empty command")

        # Whitespace should get discarded automatically by str.split(), so this is only for forward compatibility with newer Python version, where this behaviour could change
        split_line = [argument.strip() for argument in line.split()]
        command = split_line.pop(0).upper()

        return command, split_line

    def _call_command_handler(self, command: str, args: List[str]) -> None:
        command_handler = ClientCommandHandler(self._client_status, command, args)
        command_handler.handle_command()

    def _encode_and_send_data_to_client(self, data_container: SendDataToClientException) -> None:
        try:
            sent_bytes = data_container.build_message(self._client_status)
        except UnicodeEncodeError:
            # If this fails, something is terribly wrong (as the error response in this case contains only ASCII characters)
            sent_bytes = SendDataToClientException.err("The sent data contains a non-ASCII character (the UTF-8 mode is not enabled)", pop3_response_code=POP3ResponseCodes.Codes.UTF8).build_message(self._client_status)

        self._send_data_to_client(sent_bytes, data_container.should_close_connection_after_sending_data)

    def _send_data_to_client(self, sent_bytes: bytes, should_close_connection_after_sending_data: bool) -> None:
        self._client_status.connection_info.socket.sendall(sent_bytes)

        if should_close_connection_after_sending_data:
            raise CloseConnectionException("The command handler wants to close the client connection.")
