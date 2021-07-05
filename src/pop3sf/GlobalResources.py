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


from typing import Optional, Union
import logging
from .CustomLoggingClassBase import CustomLoggingClassBase
from .PerUserExclusivityEnsurer import PerUserExclusivityEnsurer


class GlobalResources:
    _logger: Optional[Union[logging.Logger, CustomLoggingClassBase]] = None
    _exclusivity_ensurer: Optional[PerUserExclusivityEnsurer] = None

    @classmethod
    def set_resources(cls, logger: Union[logging.Logger, CustomLoggingClassBase], exclusivity_ensurer: PerUserExclusivityEnsurer) -> None:
        assert cls._logger is None
        assert cls._exclusivity_ensurer is None

        cls._logger = logger
        cls._exclusivity_ensurer = exclusivity_ensurer

    @classmethod
    def get_logger(cls) -> Union[logging.Logger, CustomLoggingClassBase]:
        assert cls._logger is not None

        return cls._logger

    @classmethod
    def get_exclusivity_ensurer(cls) -> PerUserExclusivityEnsurer:
        assert cls._exclusivity_ensurer is not None

        return cls._exclusivity_ensurer
