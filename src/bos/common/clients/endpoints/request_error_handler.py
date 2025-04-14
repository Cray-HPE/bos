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
from json import JSONDecodeError
import logging
from typing import NoReturn

from requests.exceptions import HTTPError
from requests.exceptions import ConnectionError as RequestsConnectionError
from urllib3.exceptions import MaxRetryError

from bos.common.utils import compact_response_text, exc_type_msg

from .defs import RequestData
from .exceptions import ApiResponseError

LOGGER = logging.getLogger(__name__)


class BaseRequestErrorHandler(ABC):
    """
    The abstract base class for request error handlers that will be used by an API endpoint.
    """

    @classmethod
    @abstractmethod
    def handle_exception(cls, err: Exception,
                         request_data: RequestData) -> NoReturn:
        ...


class RequestErrorHandler(BaseRequestErrorHandler):
    """
    The default request error handler used by API endpoints.
    """

    @classmethod
    def handle_api_response_error(cls, err: ApiResponseError,
                                  request_data: RequestData) -> NoReturn:
        LOGGER.error("Non-2XX response (%d) to %s %s; %s %s",
                     err.response_data.status_code, request_data.method_name, request_data.url,
                     err.response_data.reason, compact_response_text(err.response_data.text))
        raise err

    @classmethod
    def handle_connection_error(cls, err: RequestsConnectionError,
                                request_data: RequestData) -> NoReturn:
        LOGGER.error("%s %s: Unable to connect: %s", request_data.method_name,
                     request_data.url, exc_type_msg(err))
        raise err

    @classmethod
    def handle_http_error(cls, err: HTTPError,
                          request_data: RequestData) -> NoReturn:
        LOGGER.error("%s %s: Unexpected response: %s",
                     request_data.method_name, request_data.url,
                     exc_type_msg(err))
        raise err

    @classmethod
    def handle_json_decode_error(cls, err: JSONDecodeError,
                                 request_data: RequestData) -> NoReturn:
        LOGGER.error("%s %s: Non-JSON response: %s", request_data.method_name,
                     request_data.url, exc_type_msg(err))
        raise err

    @classmethod
    def handle_max_retry_error(cls, err: MaxRetryError,
                               request_data: RequestData) -> NoReturn:
        LOGGER.error("%s %s: Request failed after retries: %s",
                     request_data.method_name, request_data.url,
                     exc_type_msg(err))
        raise err

    @classmethod
    def default(cls, err: Exception, request_data: RequestData) -> NoReturn:
        LOGGER.error("%s %s: Unexpected exception: %s",
                     request_data.method_name, request_data.url,
                     exc_type_msg(err))
        raise err

    @classmethod
    def handle_exception(cls, err: Exception,
                         request_data: RequestData) -> NoReturn:
        if isinstance(err, ApiResponseError):
            cls.handle_api_response_error(err, request_data)
        if isinstance(err, RequestsConnectionError):
            cls.handle_connection_error(err, request_data)
        if isinstance(err, HTTPError):
            cls.handle_http_error(err, request_data)
        if isinstance(err, JSONDecodeError):
            cls.handle_json_decode_error(err, request_data)
        if isinstance(err, MaxRetryError):
            cls.handle_max_retry_error(err, request_data)
        cls.default(err, request_data)
