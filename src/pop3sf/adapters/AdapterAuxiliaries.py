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
import time
import email.mime.text
import bcrypt


class AdapterAuxiliaries:
    @staticmethod
    def check_bcrypt_password(user_supplied_password: str, expected_password_bcrypt: str) -> bool:
        return bcrypt.checkpw(user_supplied_password.encode("utf-8"), expected_password_bcrypt.encode("utf-8"))

    @staticmethod
    def generate_from_to_email_address(username: str) -> str:
        return "{} <{}@localhost>".format(username, username)

    @staticmethod
    def wrap_plaintext_in_email(body: str, subject: str, from_: str, to: str, date: time.struct_time) -> str:
        date_str = time.strftime("%a, %d %b %Y %H:%M:%S %z", date)

        email_ = email.mime.text.MIMEText(body, "plain", "utf-8")
        email_.add_header("Date", date_str)
        email_.add_header("From", from_)
        email_.add_header("To", to)
        email_.add_header("Subject", subject)
        email_.add_header("X-Mailer", "POP3SF-Plaintext-Wrapper")

        return str(email_)
