#
# MIT License
#
# (C) Copyright 2021-2025 Hewlett Packard Enterprise Development LP
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
import logging
from typing import Generic, Type, TypeVar

import requests

from .defs import RequestData, RequestsMethod
from .exceptions import ApiResponseError
from .request_error_handler import BaseRequestErrorHandler, RequestErrorHandler

LOGGER = logging.getLogger(__name__)

RequestReturnT = TypeVar('RequestReturnT')


class BaseGenericEndpoint(ABC, Generic[RequestReturnT]):
    """
    This base class provides generic access to an API endpoint.
    RequestReturnT represents the type of data this API will return.
    Most often this will be the Json data from the response body, but in some
    cases (like with BSS), we are after something else.

    Exceptions are handled by a separate class, since different API clients
    may want to handle these differently.
    """
    BASE_ENDPOINT: str = ''
    ENDPOINT: str = ''

    @property
    def error_handler(self) -> Type[BaseRequestErrorHandler]:
        return RequestErrorHandler

    def __init__(self, session: requests.Session):
        super().__init__()
        self.session = session

    @classmethod
    @abstractmethod
    def format_response(cls, response: requests.Response) -> RequestReturnT:
        ...

    @classmethod
    def base_url(cls) -> str:
        return f"{cls.BASE_ENDPOINT}/{cls.ENDPOINT}"

    @classmethod
    def url(cls, uri: str) -> str:
        base_url = cls.base_url()
        if not uri:
            return base_url
        if uri[0] == '/' or base_url[-1] == '/':
            return f"{base_url}{uri}"
        return f"{base_url}/{uri}"

    def request(self,
                method: RequestsMethod,
                /,
                *,
                uri: str = "",
                **kwargs) -> RequestReturnT:
        url = self.url(uri)
        LOGGER.debug("%s %s (kwargs=%s)", method.__name__.upper(), url, kwargs)
        try:
            return self._request(method, url, **kwargs)
        except Exception as err:
            self.error_handler.handle_exception(
                err,
                RequestData(method_name=method.__name__.upper(),
                            url=url,
                            request_options=kwargs))

    @classmethod
    def _request(cls, method: RequestsMethod, url: str, /,
                 **kwargs) -> RequestReturnT:
        """Make API request"""
        with method(url, **kwargs) as response:
            if not response.ok:
                raise ApiResponseError(response=response)
            return cls.format_response(response)

    def delete(self, **kwargs) -> RequestReturnT:
        """Delete request"""
        return self.request(self.session.delete, **kwargs)

    def get(self, **kwargs) -> RequestReturnT:
        """Get request"""
        return self.request(self.session.get, **kwargs)

    def patch(self, **kwargs) -> RequestReturnT:
        """Patch request"""
        return self.request(self.session.patch, **kwargs)

    def post(self, **kwargs) -> RequestReturnT:
        """Post request"""
        return self.request(self.session.post, **kwargs)

    def put(self, **kwargs) -> RequestReturnT:
        """Put request"""
        return self.request(self.session.put, **kwargs)
