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


from typing import Union
import abc
import ipaddress


class AdapterBase(metaclass=abc.ABCMeta):
    """
    The AdapterBase class is a abstract base class for adapters - classes that relay email messages from some external data source to the POP3 server.
    By extending this class, one specifies the methods of accessing and providing email messages to the POP3 server.

    The program gets an instance of an adapter by calling the Settings.get_adapter() method.
    This method is called for every newly connected client. It MUST return a new instance of an adapter of every time it is called.

    Some methods of this class accept an "index" integer argument. This argument refers to a specific message provided by the adapter.
    The index is always between 0 and get_message_count() - 1 and, except when passed to the is_message_marked_as_deleted() method,
     it's never the index of a message that was marked as deleted.

    All methods of this class are thread-safe - if the server is executing an adapter's method, no other adapter's method is executing at the same time.

    If all connected clients with the same username haven't the read-only mailbox access mode enabled, only one session can exist for a specific user at the same time.
    This prevents multiple concurrent sessions from deleting the same message which could cause inconsistency of the underlying adapter's data source.
    This "uniqueness" of standard (read-write) sessions is checked after the verify_login_credentials() method call,
     so the login_successful() method isn't called if this check fails.

    Every method of this class (including __init__) can safely raise the AdapterCloseConnectionException exception;
    in such case, the client connection will be closed immediately and the client thread will be terminated.
    It should be noted that if it's raised in a method other than connection_closed(), the connection_closed() method will be called.
    """

    # Can be overridden, if the inheritor wants to implement a different implementation.
    def connection_opened(self, client_address: Union[ipaddress.IPv4Address, ipaddress.IPv6Address], client_port: int) -> None:
        """
        This method is called once per session when a new client establishes connection with the POP3 server.
        This is the first method that is called on a new adapter's instance by the server.

        :param client_address: The client's IP address.
        :param client_port: The ephemeral port the client is connecting from.
        :raises AdapterCloseConnectionException: When an unrecoverable error occurs. The connection will be closed immediately.
        """

        pass

    # Can be overridden, if the inheritor wants to implement a different implementation.
    def read_only_mode_allowed(self) -> bool:
        """
        This method informs the server whether the adapter supports the non-standard POP3SF-specific read-only mailbox access extension.
        In most cases, this is not a problem, so the method returns True, if it's not overridden.
        This method can be called anytime and any number of times.

        :return: True if the adapter supports the read-only mailbox access extension, False otherwise.
        :raises AdapterCloseConnectionException: When an unrecoverable error occurs. The connection will be closed immediately.
        """

        return True

    @abc.abstractmethod
    def verify_login_credentials(self, username: str, password: str) -> bool:
        """
        This method verifies the user-supplied username and password and returns True if they are valid, False otherwise.
        It can be called any number of times until it returns True. It can never be called again after that.

        :param username: The user-supplied username.
        :param password: The user-supplied password.
        :return: True if the credentials are valid, False otherwise.
        :raises AdapterCloseConnectionException: When an unrecoverable error occurs. The connection will be closed immediately.
        """

        raise NotImplementedError("The verify_login_credentials() method must be overridden prior to calling it!")

    # Can be overridden, if the inheritor wants to implement a different implementation.
    def login_successful(self, username: str, read_only: bool) -> None:
        """
        This method is called once per session after the verify_login_credentials() returned True and it is ensured that
         the server can accept commands from the client after this call finishes.
        It is the right place for preparing the adapter's underlying data source.

        :param username: The user-supplied username, the same as the one passed to the verify_login_credentials() method.
        :param read_only: Whether the read-only mailbox access mode was enabled by the client. Always False if the read_only_mode_allowed() returns False.
        :raises AdapterCloseConnectionException: When an unrecoverable error occurs. The connection will be closed immediately.
        """

        pass

    @abc.abstractmethod
    def get_message_count(self) -> int:
        """
        This method returns the number of messages that the adapter's underlying data source contains, whilst also counting the messages marked as deleted!
        This method can be called anytime and any number of times after the login_successful() method was called.

        :return: The number of messages the adapter's data source contains, including the number of messages marked as deleted.
        :raises AdapterCloseConnectionException: When an unrecoverable error occurs. The connection will be closed immediately.
        """

        raise NotImplementedError("The get_message_count() method must be overridden prior to calling it!")

    @abc.abstractmethod
    def get_message_content(self, index: int, encoding: str) -> str:
        """
        This method returns a specific message's content as string.
        The message must be an email in the RFC 822 format! If the message is plaintext, one can use the
         AdapterAuxiliaries.wrap_plaintext_in_email() method to wrap it into an email's body.
        This method can be called anytime and any number of times after the login_successful() method was called.

        The encoding argument specifies to which encoding the message will be encoded to when sending it to the client. It will be either "ascii" or "utf-8".
        If the message cannot be encoded using the specified encoding, you MAY convert it and return a surrogate message that can be encoded using that encoding.
        However, you don't have to do this - if you provide a message that cannot be encoded, the server will send the client an -ERR [UTF8] response
         which is perfectly valid behavior. See RFC 6856 Section 2.1 for details.

        :param index: A specific message's index. See this class's docstring for details.
        :param encoding: The encoding to which the message will be encoded to when sending it to the client.
        :return: The message's content as string.
        :raises AdapterCloseConnectionException: When an unrecoverable error occurs. The connection will be closed immediately.
        """

        raise NotImplementedError("The get_message_content() method must be overridden prior to calling it!")

    @abc.abstractmethod
    def get_message_unique_id(self, index: int) -> str:
        """
        This methods returns a specific message's unique ID as string. The uniqueness is checked by the server's internal logic!
        The unique ID must be a 1 to 70 characters long string, containing only readable and non-whitespace ASCII characters.
        This method can be called anytime and any number of times after the login_successful() method was called.

        :param index: A specific message's index. See this class's docstring for details.
        :return: The message's unique ID as string.
        :raises AdapterCloseConnectionException: When an unrecoverable error occurs. The connection will be closed immediately.
        """

        raise NotImplementedError("The get_message_unique_id() method must be overridden prior to calling it!")

    @abc.abstractmethod
    def is_message_marked_as_deleted(self, index: int) -> bool:
        """
        This methods returns True if a specific message was marked as deleted using the mark_message_as_deleted() method, False otherwise.
        This method can be called anytime and any number of times after the login_successful() method was called.
         It can't be called if the read-only mailbox access mode was enabled by the client.

        :param index: A specific message's index which can refer to a message marked as deleted. See this class's docstring for details.
        :return: True if a specific message was marked as deleted using the mark_message_as_deleted() method, False otherwise.
        :raises AdapterCloseConnectionException: When an unrecoverable error occurs. The connection will be closed immediately.
        """

        raise NotImplementedError("The is_message_marked_as_deleted() method must be overridden prior to calling it!")

    @abc.abstractmethod
    def mark_message_as_deleted(self, index: int) -> None:
        """
        This method marks a specific message as deleted. However, it MUST NOT get deleted from the adapter's
         data source - this must be done in the commit_deletions() method.
        This method can be called anytime and any number of times after the login_successful() method was called.
         It can't get called if the read-only mailbox access mode was enabled by the client.

        :param index: A specific message's index. See this class's docstring for details.
        :raises AdapterCloseConnectionException: When an unrecoverable error occurs. The connection will be closed immediately.
        """

        raise NotImplementedError("The mark_message_as_deleted() method must be overridden prior to calling it!")

    @abc.abstractmethod
    def unmark_messages_marked_as_deleted(self) -> None:
        """
        This method unmarks all the messages that were marked as deleted using the mark_message_as_deleted() method.
        This method can be called anytime and any number of times after the login_successful() method was called.
         It can't get called if the read-only mailbox access mode was enabled by the client.

        :raises AdapterCloseConnectionException: When an unrecoverable error occurs. The connection will be closed immediately.
        """

        raise NotImplementedError("The unmark_messages_marked_as_deleted() method must be overridden prior to calling it!")

    @abc.abstractmethod
    def commit_deletions(self) -> None:
        """
        This method deletes the messages marked as deleted from the adapter's underlying data source.
        This method can be called once per session after the login_successful() method was called and before the client connection gets gracefully closed by the client.
         It can't get called if the read-only mailbox access mode was enabled by the client.
         After this method call finishes, only the connection_closed() method can be called.

        :raises AdapterCloseConnectionException: When an unrecoverable error occurs. The connection will be closed immediately.
        """

        raise NotImplementedError("The commit_deletions() method must be overridden prior to calling it!")

    # Can be overridden, if the inheritor wants to implement a different implementation.
    def connection_closed(self) -> None:
        """
        This method is called once per session after the client connection was closed.
        Since this method gets called even if the client connection dies, an (uncaught) exception is raised or anything else unexpected happens,
         it's the right place to perform resource cleanup tasks (e.g. closing the adapter's underlying data source, if it got opened).

        :raises AdapterCloseConnectionException: When an unrecoverable error occurs.
        """

        pass
