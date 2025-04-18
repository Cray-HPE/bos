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

from requests_retry_session import RequestsRetryAdapterArgs

from bos.common.clients.api_client_with_timeout_option import APIClientWithTimeoutOption

from .images import ImagesEndpoint

@dataclass
class ImsEndpoints:
    images: ImagesEndpoint | None = None

class IMSClient(APIClientWithTimeoutOption[ImsEndpoints]):

    @property
    def _init_endpoints(self) -> ImsEndpoints:
        return ImsEndpoints()

    @property
    def read_timeout(self) -> int:
        return self.bos_options.ims_read_timeout

    @property
    def retry_kwargs(self) -> RequestsRetryAdapterArgs:
        kwargs = super().retry_kwargs
        # If IMS being inaccessible is not a fatal error, then reduce the number
        # of retries we make, to prevent a lengthy delay
        kwargs["retries"] = 8 if self.bos_options.ims_errors_fatal else 4
        return kwargs

    @property
    def images(self) -> ImagesEndpoint:
        if self._endpoints.images is None:
            self._endpoints.images = ImagesEndpoint(self.requests_session)
        return self._endpoints.images
