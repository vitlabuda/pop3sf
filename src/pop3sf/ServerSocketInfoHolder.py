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
from typing import Optional, Union


class ServerSocketInfoHolder:
    def __init__(self, listen_address: str, listen_port: Union[int, str], use_tls: bool, tls_certificate_file: Optional[str], tls_private_key_file: Optional[str]):
        if use_tls:
            assert tls_certificate_file is not None
            assert tls_private_key_file is not None
        else:
            assert tls_certificate_file is None
            assert tls_private_key_file is None

        self.listen_address: str = listen_address
        self.listen_port: Union[int, str] = listen_port

        self.use_tls: bool = use_tls
        self.tls_certificate_file: Optional[str] = tls_certificate_file
        self.tls_private_key_file: Optional[str] = tls_private_key_file

    @classmethod
    def new_insecure_socket(cls, listen_address: str, listen_port: Union[int, str]) -> ServerSocketInfoHolder:
        return cls(listen_address, listen_port, False, None, None)

    @classmethod
    def new_tls_socket(cls, listen_address: str, listen_port: Union[int, str], tls_certificate_file: str, tls_private_key_file: str) -> ServerSocketInfoHolder:
        # To generate a self-signed certificate & key pair:
        #  openssl req -x509 -newkey rsa:4096 -keyout private_key.key -out certificate.crt -days 1825 -nodes

        return cls(listen_address, listen_port, True, tls_certificate_file, tls_private_key_file)
