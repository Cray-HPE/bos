#
# MIT License
#
# (C) Copyright 2021-2024 Hewlett Packard Enterprise Development LP
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
from json import JSONDecodeError
import logging

from requests.exceptions import HTTPError
from requests.exceptions import ConnectionError as RequestsConnectionError
from urllib3.exceptions import MaxRetryError

from bos.common.clients.endpoints import ApiResponseError, BaseEndpoint, JsonData, RequestsMethod
from bos.common.utils import PROTOCOL

from .exceptions import PowerControlException

LOGGER = logging.getLogger(__name__)

SERVICE_NAME = 'cray-power-control'
ENDPOINT = f"{PROTOCOL}://{SERVICE_NAME}"


class BasePcsEndpoint(BaseEndpoint, ABC):
    """
    This base class provides generic access to the PCS API.
    The individual endpoint needs to be overridden for a specific endpoint.
    """
    BASE_ENDPOINT = ENDPOINT

    def request(self,
                method: RequestsMethod,
                /,
                *,
                uri: str = "",
                **kwargs) -> JsonData:
        try:
            return super().request(method, uri=uri, **kwargs)
        except (ApiResponseError, RequestsConnectionError, HTTPError,
                JSONDecodeError, MaxRetryError) as err:
            raise PowerControlException(err) from err
