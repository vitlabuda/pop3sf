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


from typing import Optional, Union, Tuple
import sys
import logging
from .Auxiliaries import Auxiliaries
from .CustomLoggingClassBase import CustomLoggingClassBase
from .ServerSocketInfoHolder import ServerSocketInfoHolder
from .adapters.AdapterBase import AdapterBase
from .adapters.AdapterCloseConnectionException import AdapterCloseConnectionException


class Settings:
    """
    This class contains the options that the server admin can alter.

    Some options are self-explanatory, while others are documented using comments above or next to them.
    """

    # If the value of any of these following options is None, such option won't be taken into account when initializing the server.
    WORKING_DIRECTORY: Optional[str] = "working_dir/"  # If it's a relative path, it's relative to the folder containing the run_pop3sf.sh bash script.
    UMASK: Optional[int] = None  # e.g. 0o077; see https://man7.org/linux/man-pages/man2/umask.2.html
    DROP_ROOT_PRIVILEGES: Optional[Auxiliaries.DropRootPrivilegesInfo] = Auxiliaries.DropRootPrivilegesInfo("nobody", "nogroup")  # This option will only be taken into account when the server gets executed under the root user (uid 0).

    # Specify on what addresses & ports you want to listen via ServerSocketInfoHolder objects, created using the
    #  ServerSocketInfoHolder.new_insecure_socket() or ServerSocketInfoHolder.new_tls_socket() method.
    #  The server is able to listen on multiple sockets at the same time.
    #  The server supports both IPv4 and IPv6, but it has the IPV6_V6ONLY socket option disabled. Thus, it is necessary to create separate ServerSocketInfoHolder for IPv4 and IPv6.
    #  In most cases, it will be necessary to run the server with root privileges if you want to bind a server socket to a privileged port (< 1024). To drop the privileges after
    #   the server creates the socket, the DROP_ROOT_PRIVILEGES option should be used.
    # IT IS STRONGLY RECOMMENDED NOT TO USE INSECURE NON-TLS (NON-SSL) SOCKETS, AS CLIENT'S PERSONAL INFORMATION MIGHT
    #  GET LEAKED WHEN TRAVELLING ACROSS AN UNTRUSTED NETWORK, SUCH AS THE INTERNET!
    LISTEN_ON: Tuple[ServerSocketInfoHolder, ...] = (
        # ServerSocketInfoHolder.new_insecure_socket("0.0.0.0", 8110),  # default non-SSL POP3 port: 110
        ServerSocketInfoHolder.new_tls_socket("0.0.0.0", 8995, "certificate.crt", "private_key.key"),  # default SSL POP3 port: 995
    )

    CLIENT_TIMEOUT: int = 600  # in seconds
    MAX_CONCURRENT_CLIENTS: int = 25
    MAX_INVALID_COMMANDS_PER_SESSION: int = -1  # Set to a negative number if you don't want to impose a limit; if exceeded, the client will be forcibly disconnected
    MAX_INVALID_PASSWORDS_PER_SESSION: int = 3  # Set to a negative number if you don't want to impose a limit; if exceeded, the client will be forcibly disconnected
    FAILED_LOGIN_DELAY: int = 500  # The time to wait after an invalid login attempt in milliseconds; set to 0 if you don't want to impose a delay

    # In case the client handler raises an unexpected exception:
    # - DEBUG = True -> The exception will be reraised, thus closing the client connection and displaying the exception's stack trace.
    # - DEBUG = False -> The exception will be silently ignored and the client connection will be closed (ideal for production use).
    DEBUG: bool = False

    @staticmethod
    def get_adapter() -> AdapterBase:
        """
        This method returns an adapter that provides email messages to the POP3 server.
        It's called for every newly connected client. It MUST return a new instance of an adapter of every time it is called.

        Calls of this method are thread-safe.

        :return: A new adapter instance.
        """

        # from .adapters.ListAdapter import ListAdapter
        # return ListAdapter("user", "password", [
        #    "Hello World!",
        #    "Multiline\nmessage\n",
        #    "Some other message\n.Byte-stuffing test\nAnother line",
        #    "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\nLine 6\nLine 7\nLine 8\nLine 8\nLine 10\n"
        # ])

        # from .adapters.DirectorySingleuserAdapter import DirectorySingleuserAdapter
        # return DirectorySingleuserAdapter("user", '$2b$12$4HAJ3RYUEH1WDVOu/B5qWuNEWxojAz4EjW9WzH7KqY6DwUPHeASZm', "emails_singleuser")  # The bcrypt-hashed password is "password"; The directory path is relative to WORKING_DIRECTORY

        # from .adapters.DirectoryMultiuserAdapter import DirectoryMultiuserAdapter
        # return DirectoryMultiuserAdapter("emails_multiuser")  # The directory path is relative to WORKING_DIRECTORY

        # from .adapters.MySQLSingleuserAdapter import MySQLSingleuserAdapter
        # return MySQLSingleuserAdapter("user", '$2b$12$4HAJ3RYUEH1WDVOu/B5qWuNEWxojAz4EjW9WzH7KqY6DwUPHeASZm', MySQLSingleuserAdapter.DatabaseCredentials("user", "pass", "pop3sf"))  # The bcrypt-hashed password is "password"

        # from .adapters.MySQLMultiuserAdapter import MySQLMultiuserAdapter
        # return MySQLMultiuserAdapter(MySQLMultiuserAdapter.DatabaseCredentials("user", "pass", "pop3sf"))

        raise AdapterCloseConnectionException("No adapter was chosen!")

    @staticmethod
    def get_logger() -> Union[logging.Logger, CustomLoggingClassBase]:
        """
        This method returns a logger object that will be used to log various event during the server's runtime.
        It's called only once - when the program starts.

        It can either be a logging.Logger instance, or an instance of a custom class extending the CustomLoggingClassBase abstract base class.
         In the second case, you must ensure that the methods used for logging are thread-safe!

        :return: A logger object.
        """

        logging.basicConfig(stream=sys.stderr, level=logging.INFO)
        return logging.getLogger("pop3sf")
