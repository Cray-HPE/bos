# Copyright 2021-2022 Hewlett Packard Enterprise Development LP
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
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# (MIT License)

import json
import logging
from requests.exceptions import HTTPError, ConnectionError
from urllib3.exceptions import MaxRetryError

from bos.operators.utils import PROTOCOL, requests_retry_session

LOGGER = logging.getLogger('bos.operators.utils.clients.bos.base')

API_VERSION = 'v2'
SERVICE_NAME = 'cray-bos'
BASE_ENDPOINT = "%s://%s/%s" % (PROTOCOL, SERVICE_NAME, API_VERSION)


def log_call_errors(func):
    def wrap(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            return result
        except (ConnectionError, MaxRetryError) as e:
            LOGGER.error("Unable to connect to BOS: {}".format(e))
            raise e
        except HTTPError as e:
            LOGGER.error("Unexpected response from BOS: {}".format(e))
            raise e
        except json.JSONDecodeError as e:
            LOGGER.error("Non-JSON response from BOS: {}".format(e))
            raise e
    return wrap


class BaseBosEndpoint(object):
    """ 
    This base class provides generic access to the BOS API. 
    The individual endpoint needs to be overridden for a specific endpoint.
    """
    ENDPOINT = ''

    def __init__(self):
        self.base_url = "%s/%s" % (BASE_ENDPOINT, self.ENDPOINT)

    @log_call_errors
    def get_item(self, item_id):
        """Get information for a single BOS item"""
        url = self.base_url + '/' + item_id
        session = requests_retry_session()
        response = session.get(url)
        response.raise_for_status()
        item = json.loads(response.text)
        return item

    @log_call_errors
    def get_items(self, **kwargs):
        """Get information for all BOS items"""
        session = requests_retry_session()
        response = session.get(self.base_url, params=kwargs)
        response.raise_for_status()
        items = json.loads(response.text)
        return items

    @log_call_errors
    def update_item(self, item_id, data):
        """Update information for a single BOS item"""
        url = self.base_url + '/' + item_id
        session = requests_retry_session()
        response = session.patch(url, json=data)
        response.raise_for_status()
        item = json.loads(response.text)
        return item

    @log_call_errors
    def update_items(self, data):
        """Update information for a multiple BOS items"""
        session = requests_retry_session()
        response = session.patch(self.base_url, json=data)
        response.raise_for_status()
        items = json.loads(response.text)
        return items

    @log_call_errors
    def put_items(self, data):
        """Put information for multiple BOS Items"""
        session = requests_retry_session()
        response = session.put(self.base_url, json=data)
        response.raise_for_status()
        items = json.loads(response.text)
        return items
