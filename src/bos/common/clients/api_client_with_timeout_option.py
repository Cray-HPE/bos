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
from typing import Unpack

from requests_retry_session import RequestsRetryAdapterArgs

from bos.common.clients.bos.options import options
from bos.common.options import BaseOptions

from .api_client import APIClient

class APIClientWithTimeoutOption[T](APIClient[T], ABC):
    """
    As a subclass of RetrySessionManager, this class can be used as a context manager,
    and will have a requests session available as self.requests_session

    This context manager is used to provide API endpoints, via subclassing.
    """

    def __init__(self, bos_options: BaseOptions | None=None,
                 **adapter_kwargs: Unpack[RequestsRetryAdapterArgs]) -> None:
        self._bos_options = options if bos_options is None else bos_options
        kwargs = self.retry_kwargs
        kwargs.update(adapter_kwargs)
        super().__init__(**kwargs)

    @property
    def bos_options(self) -> BaseOptions:
        return self._bos_options

    @property
    @abstractmethod
    def read_timeout(self) -> int:
        """
        Return the read_timeout value for this client
        """

    @property
    def retry_kwargs(self) -> RequestsRetryAdapterArgs:
        return { "read_timeout": self.read_timeout }
