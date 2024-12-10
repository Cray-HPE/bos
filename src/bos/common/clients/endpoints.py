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
import functools
import json
import logging
from typing import ContextManager

import requests
from requests.exceptions import HTTPError, ConnectionError
from urllib3.exceptions import MaxRetryError

from bos.common.utils import exc_type_msg

LOGGER = logging.getLogger('bos.common.clients.endpoints')


def log_call_errors(func):

    @functools.wraps(func)
    def wrap(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            return result
        except (ConnectionError, MaxRetryError) as e:
            LOGGER.error("Unable to connect to BOS: %s", exc_type_msg(e))
            raise e
        except HTTPError as e:
            LOGGER.error("Unexpected response from BOS: %s", exc_type_msg(e))
            raise e
        except json.JSONDecodeError as e:
            LOGGER.error("Non-JSON response from BOS: %s", exc_type_msg(e))
            raise e

    return wrap


class BaseEndpoint(ABC):
    """
    This base class provides generic access to an API.
    The individual endpoint needs to be overridden for a specific endpoint.
    """
    BASE_ENDPOINT = ''
    ENDPOINT = ''

    def __init__(self, session: requests.Session):
        super().__init__()
        self.base_url = f"{self.BASE_ENDPOINT}/{self.ENDPOINT}"
        self.session = session


    @log_call_errors
    def request(self, method: ContextManager, *, uri: str="", **kwargs):
        """Make API request"""
        url = f"{self.base_url}{uri}" if uri and uri[0] == '/' else f"{self.base_url}{uri}"
        LOGGER.debug("%s %s (kwargs=%s)", method.__name__.upper(), url, kwargs)
        with method(url, **kwargs) as response:
            response.raise_for_status()
            return json.loads(response.text) if response.text else None


    def delete(self, **kwargs):
        """Delete request"""
        return self.request(self.session.delete, **kwargs)


    def get(self, **kwargs):
        """Get request"""
        return self.request(self.session.get, **kwargs)


    def patch(self, **kwargs):
        """Patch request"""
        return self.request(self.session.patch, **kwargs)


    def post(self, **kwargs):
        """Post request"""
        return self.request(self.session.post, **kwargs)


    def put(self, **kwargs):
        """Put request"""
        return self.request(self.session.put, **kwargs)
