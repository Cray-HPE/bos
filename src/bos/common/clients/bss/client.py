#
# MIT License
#
# (C) Copyright 2024-2025 Hewlett Packard Enterprise Development LP
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
from typing import Unpack

from requests_retry_session import RequestsRetryAdapterArgs

from bos.common.clients.api_client_with_timeout_option import APIClientWithTimeoutOption

from .boot_parameters import BootParametersEndpoint

class BSSClient(APIClientWithTimeoutOption):

    def __init__(self, **adapter_kwargs: Unpack[RequestsRetryAdapterArgs]):
        super().__init__(**adapter_kwargs)
        self._boot_parameters: BootParametersEndpoint | None = BootParametersEndpoint(self.requests_session)

    def _clear_endpoint_values(self) -> None:
        self._boot_parameters = None

    @property
    def read_timeout(self) -> int:
        return self.bos_options.bss_read_timeout

    @property
    def boot_parameters(self) -> BootParametersEndpoint:
        if self._boot_parameters is None:
            raise ValueError("Attempt to use uninitialized BSS boot parameters endpoint")
        return self._boot_parameters
