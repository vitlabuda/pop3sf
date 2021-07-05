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


from typing import Union, List
import gc
import socket
import select
import ssl
import threading
from .Settings import Settings
from .Auxiliaries import Auxiliaries
from .GlobalResources import GlobalResources
from .ClientHandler import ClientHandler
from .ClientConnectionInfoHolder import ClientConnectionInfoHolder
from .ServerSocketInfoHolder import ServerSocketInfoHolder
from .PerUserExclusivityEnsurer import PerUserExclusivityEnsurer
from .POP3SFRuntimeError import POP3SFRuntimeError


class POP3SF:
    PROGRAM_VERSION: float = 1.0

    _LISTEN_BACKLOG: int = 64

    def __init__(self):
        Auxiliaries.change_working_directory_and_umask()

        GlobalResources.set_resources(Settings.get_logger(), PerUserExclusivityEnsurer())

        self._threads: List[threading.Thread] = []
        self._server_sockets: List[Union[socket.socket, ssl.SSLSocket]] = self._generate_server_sockets()
        self._server_poll_object: select.poll = self._generate_poll_object_from_server_sockets()

        Auxiliaries.drop_root_privileges_if_needed()  # The root privileges are dropped after the server sockets have been created, as the sockets have already been bound, possibly to a privileged port.

        self._continue_polling_for_new_connections: bool = True
        self._next_connection_id: int = 1

    def _generate_server_sockets(self) -> List[Union[socket.socket, ssl.SSLSocket]]:
        server_sockets = []

        for info_holder in Settings.LISTEN_ON:
            server_sockets += self._generate_server_sockets_from_info_holder(info_holder)

        if len(server_sockets) == 0:
            raise POP3SFRuntimeError("The server couldn't create any listening server sockets!")

        return server_sockets

    def _generate_server_sockets_from_info_holder(self, info_holder: ServerSocketInfoHolder) -> List[Union[socket.socket, ssl.SSLSocket]]:
        server_sockets = []
        addrinfo_list = socket.getaddrinfo(info_holder.listen_address, info_holder.listen_port, proto=socket.IPPROTO_TCP)

        for addrinfo in addrinfo_list:
            socket_ = self._create_plain_tcp_server_socket(addrinfo)

            if info_holder.use_tls:
                socket_ = self._wrap_plain_tcp_server_socket_in_tls(socket_, info_holder.tls_certificate_file, info_holder.tls_private_key_file)

            server_sockets.append(socket_)

        return server_sockets

    def _create_plain_tcp_server_socket(self, addrinfo: tuple) -> Union[socket.socket, ssl.SSLSocket]:
        plain_tcp_socket = socket.socket(family=addrinfo[0], type=addrinfo[1], proto=addrinfo[2])

        plain_tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if addrinfo[0] == socket.AF_INET6:
            plain_tcp_socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)  # Disable dual-stack on IPv6 sockets

        plain_tcp_socket.bind(addrinfo[4])
        plain_tcp_socket.listen(POP3SF._LISTEN_BACKLOG)

        return plain_tcp_socket

    def _wrap_plain_tcp_server_socket_in_tls(self, plain_tcp_socket: Union[socket.socket, ssl.SSLSocket], certificate_file: str, private_key_file: str) -> Union[socket.socket, ssl.SSLSocket]:
        tls_context = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
        tls_context.load_cert_chain(certfile=certificate_file, keyfile=private_key_file)

        return tls_context.wrap_socket(plain_tcp_socket, server_side=True)

    def _generate_poll_object_from_server_sockets(self) -> select.poll:
        poll_object = select.poll()

        for server_socket in self._server_sockets:
            poll_object.register(server_socket, select.POLLIN)

        return poll_object

    def start_server_loop(self) -> None:
        self._send_on_start_log_messages()

        while self._continue_polling_for_new_connections:
            self._poll_server_sockets()

        for server_socket in self._server_sockets:
            server_socket.close()

        self._send_on_exit_log_messages()

    def _send_on_start_log_messages(self) -> None:
        GlobalResources.get_logger().info("POP3SF successfully started.")
        GlobalResources.get_logger().info("Listening on " + ", ".join(map(Auxiliaries.get_server_sockets_address_as_string, self._server_sockets)) + ".")

        for server_socket in self._server_sockets:
            if not isinstance(server_socket, ssl.SSLSocket):
                GlobalResources.get_logger().warning("The server socket listening on {} is not secured with TLS! Personal information may get leaked!".format(Auxiliaries.get_server_sockets_address_as_string(server_socket)))

    def _send_on_exit_log_messages(self) -> None:
        GlobalResources.get_logger().info("The server is exiting.")

    def _poll_server_sockets(self) -> None:
        try:
            poll_events = self._server_poll_object.poll()
        except KeyboardInterrupt:
            self._continue_polling_for_new_connections = False
            return

        for fd, events in poll_events:
            if events & select.POLLIN:
                server_socket = self._find_server_socket_by_polled_fd(fd)
                self._accept_client_connection_on_a_server_socket(server_socket)
            else:
                raise POP3SFRuntimeError("Unexpected event(s) ({}) happened on server socket with FD {}!".format(events, fd))

    def _find_server_socket_by_polled_fd(self, fd: int) -> Union[socket.socket, ssl.SSLSocket]:
        for server_socket in self._server_sockets:
            if fd == server_socket.fileno():
                return server_socket

        raise POP3SFRuntimeError("The poll() function returned an invalid file descriptor!")

    def _accept_client_connection_on_a_server_socket(self, server_socket: Union[socket.socket, ssl.SSLSocket]) -> None:
        try:
            client_socket, client_addr = server_socket.accept()
        except ssl.SSLError:
            return

        connection_info = ClientConnectionInfoHolder(self._next_connection_id, client_socket, client_addr)
        self._start_per_client_thread(connection_info)

        self._next_connection_id += 1

    def _start_per_client_thread(self, connection_info: ClientConnectionInfoHolder) -> None:
        if not self._check_if_another_client_can_be_connected():
            try:
                connection_info.socket.close()
            except OSError:
                pass
            return

        thread = threading.Thread(target=ClientHandler.initialize_client_handler, args=(connection_info,), daemon=True)
        thread.start()

        self._threads.append(thread)

    def _check_if_another_client_can_be_connected(self) -> bool:
        # For every connected client, a new thread is created.
        # The concurrently connected client limit (= concurrently running thread limit) is defined in the Settings.py file.

        self._threads = [thread for thread in self._threads if thread.is_alive()]

        # Invoke the garbage collector manually to forcibly release any unnecessary memory associated with the died threads (disconnected clients) before connecting another client
        gc.collect()

        return len(self._threads) < Settings.MAX_CONCURRENT_CLIENTS
