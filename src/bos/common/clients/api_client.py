#
# MIT License
#
# (C) Copyright 2025 Hewlett Packard Enterprise Development LP
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
from abc import ABC, abstractmethod
import threading
from typing import Unpack

from requests_retry_session import RequestsRetryAdapterArgs

from bos.common.utils import RetrySessionManager

class APIClient[Endpoints](RetrySessionManager, ABC):
    """
    As a subclass of RetrySessionManager, this class can be used as a context manager,
    and will have a requests session available as self.requests_session

    This context manager is used to provide API endpoints, via subclassing.
    """

    def __init__(self, **adapter_kwargs: Unpack[RequestsRetryAdapterArgs]):
        super().__init__(**adapter_kwargs)
        self._lock = threading.Lock()
        self._endpoint_data = self._init_endpoints

    @property
    def _endpoints(self) -> Endpoints:
        return self._endpoint_data

    @property
    @abstractmethod
    def _init_endpoints(self) -> Endpoints: ...

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool | None:
        """
        The only cleanup we need to do when exiting the context manager is to clear out
        our list of API clients. Our call to super().__exit__ will take care of closing
        out the underlying request session.
        """
        self._endpoint_data = self._init_endpoints
        return super().__exit__(exc_type, exc_val, exc_tb)
