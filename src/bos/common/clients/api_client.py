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
from abc import ABC
from typing import Type, TypeVar

from bos.common.clients.endpoints import BaseGenericEndpoint
from bos.common.utils import RetrySessionManager

ClientEndpoint = TypeVar('ClientEndpoint', bound=BaseGenericEndpoint)


class APIClient(RetrySessionManager, ABC):
    """
    As a subclass of RetrySessionManager, this class can be used as a context manager,
    and will have a requests session available as self.requests_session

    This context manager is used to provide API endpoints, via subclassing.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._endpoint_values: dict[Type[ClientEndpoint], ClientEndpoint] = {}

    def get_endpoint(self,
                     endpoint_type: Type[ClientEndpoint]) -> ClientEndpoint:
        """
        Endpoints are created only as needed, and passed the managed retry session.
        """
        if endpoint_type not in self._endpoint_values:
            self._endpoint_values[endpoint_type] = endpoint_type(
                self.requests_session)
        return self._endpoint_values[endpoint_type]

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool | None:
        """
        The only cleanup we need to do when exiting the context manager is to clear out
        our list of API clients. Our call to super().__exit__ will take care of closing
        out the underlying request session.
        """
        self._endpoint_values.clear()
        return super().__exit__(exc_type, exc_val, exc_tb)
