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

from .groups import GroupsEndpoint
from .partitions import PartitionsEndpoint
from .state_components import StateComponentsEndpoint

class HSMClient(APIClientWithTimeoutOption):

    def __init__(self, **adapter_kwargs: Unpack[RequestsRetryAdapterArgs]):
        super().__init__(**adapter_kwargs)
        self._groups: GroupsEndpoint | None = GroupsEndpoint(self.requests_session)
        self._partitions: PartitionsEndpoint | None = PartitionsEndpoint(self.requests_session)
        self._state_components: StateComponentsEndpoint | None = StateComponentsEndpoint(self.requests_session)

    def _clear_endpoint_values(self) -> None:
        self._groups = None
        self._partitions = None
        self._state_components = None

    @property
    def read_timeout(self) -> int:
        return self.bos_options.hsm_read_timeout

    @property
    def groups(self) -> GroupsEndpoint:
        if self._groups is None:
            raise ValueError("Attempt to use uninitialized HSM groups endpoint")
        return self._groups

    @property
    def partitions(self) -> PartitionsEndpoint:
        if self._partitions is None:
            raise ValueError("Attempt to use uninitialized HSM partitions endpoint")
        return self._partitions

    @property
    def state_components(self) -> StateComponentsEndpoint:
        if self._state_components is None:
            raise ValueError("Attempt to use uninitialized HSM state components endpoint")
        return self._state_components
