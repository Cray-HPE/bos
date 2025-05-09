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
from dataclasses import dataclass

from bos.common.clients.api_client_with_timeout_option import APIClientWithTimeoutOption

from .components import ComponentEndpoint

@dataclass
class CfsEndpoints:
    components: ComponentEndpoint | None = None

class CFSClient(APIClientWithTimeoutOption[CfsEndpoints]):
    @property
    def _init_endpoints(self) -> CfsEndpoints:
        return CfsEndpoints()

    @property
    def read_timeout(self) -> int:
        return self.bos_options.cfs_read_timeout

    @property
    def components(self) -> ComponentEndpoint:
        if self._endpoints.components is None:
            self._endpoints.components = ComponentEndpoint(self.requests_session)
        return self._endpoints.components
