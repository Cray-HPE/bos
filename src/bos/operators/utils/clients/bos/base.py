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
import requests
from requests.exceptions import HTTPError, ConnectionError
from urllib3.exceptions import MaxRetryError

from bos.common.tenant_utils import get_new_tenant_header
from bos.common.utils import PROTOCOL, exc_type_msg

LOGGER = logging.getLogger('bos.operators.utils.clients.bos.base')

API_VERSION = 'v2'
SERVICE_NAME = 'cray-bos'
BASE_ENDPOINT = f"{PROTOCOL}://{SERVICE_NAME}/{API_VERSION}"


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


class BaseBosEndpoint(ABC):
    """
    This base class provides generic access to the BOS API.
    The individual endpoint needs to be overridden for a specific endpoint.
    """
    ENDPOINT = ''

    def __init__(self, session: requests.Session):
        super().__init__()
        self.base_url = f"{BASE_ENDPOINT}/{self.ENDPOINT}"
        self.session = session


class BaseBosNonTenantAwareEndpoint(BaseBosEndpoint):
    """
    This base class provides generic access to the BOS API for non-tenant-aware endpoints
    The individual endpoint needs to be overridden for a specific endpoint.
    """

    @log_call_errors
    def get_item(self, item_id):
        """Get information for a single BOS item"""
        url = self.base_url + '/' + item_id
        LOGGER.debug("GET %s", url)
        with self.session.get(url) as response:
            response.raise_for_status()
            item = json.loads(response.text)
        return item

    @log_call_errors
    def get_items(self, **kwargs):
        """Get information for all BOS items"""
        LOGGER.debug("GET %s with params=%s", self.base_url, kwargs)
        with self.session.get(self.base_url, params=kwargs) as response:
            response.raise_for_status()
            items = json.loads(response.text)
        return items

    @log_call_errors
    def update_item(self, item_id, data):
        """Update information for a single BOS item"""
        url = self.base_url + '/' + item_id
        LOGGER.debug("PATCH %s with body=%s", url, data)
        with self.session.patch(url, json=data) as response:
            response.raise_for_status()
            item = json.loads(response.text)
        return item

    @log_call_errors
    def update_items(self, data):
        """Update information for multiple BOS items"""
        LOGGER.debug("PATCH %s with body=%s", self.base_url, data)
        with self.session.patch(self.base_url, json=data) as response:
            response.raise_for_status()
            items = json.loads(response.text)
        return items

    @log_call_errors
    def put_items(self, data):
        """Put information for multiple BOS Items"""
        LOGGER.debug("PUT %s with body=%s", self.base_url, data)
        with self.session.put(self.base_url, json=data) as response:
            response.raise_for_status()
            items = json.loads(response.text)
        return items

    @log_call_errors
    def delete_items(self, **kwargs):
        """Delete information for multiple BOS items"""
        LOGGER.debug("DELETE %s with params=%s", self.base_url, kwargs)
        with self.session.delete(self.base_url, params=kwargs) as response:
            response.raise_for_status()
            return json.loads(response.text) if response.text else None


class BaseBosTenantAwareEndpoint(BaseBosEndpoint):
    """
    This base class provides generic access to the BOS API for tenant aware endpoints.
    The individual endpoint needs to be overridden for a specific endpoint.
    """

    @log_call_errors
    def get_item(self, item_id, tenant):
        """Get information for a single BOS item"""
        url = self.base_url + '/' + item_id
        LOGGER.debug("GET %s for tenant=%s", url, tenant)
        with self.session.get(url, headers=get_new_tenant_header(tenant)) as response:
            response.raise_for_status()
            item = json.loads(response.text)
        return item

    @log_call_errors
    def get_items(self, **kwargs):
        """Get information for all BOS items"""
        headers = None
        if "tenant" in kwargs:
            tenant = kwargs.pop("tenant")
            headers = get_new_tenant_header(tenant)
            LOGGER.debug("GET %s for tenant=%s with params=%s", self.base_url, tenant, kwargs)
        else:
            LOGGER.debug("GET %s with params=%s", self.base_url, kwargs)
        with self.session.get(self.base_url, params=kwargs, headers=headers) as response:
            response.raise_for_status()
            items = json.loads(response.text)
        return items

    @log_call_errors
    def update_item(self, item_id, tenant, data):
        """Update information for a single BOS item"""
        url = self.base_url + '/' + item_id
        LOGGER.debug("PATCH %s for tenant=%s with body=%s", url, tenant, data)
        with self.session.patch(url, json=data, headers=get_new_tenant_header(tenant)) as response:
            response.raise_for_status()
            item = json.loads(response.text)
        return item

    @log_call_errors
    def update_items(self, tenant, data):
        """Update information for multiple BOS items"""
        LOGGER.debug("PATCH %s for tenant=%s with body=%s", self.base_url, tenant, data)
        with self.session.patch(self.base_url, json=data,
                                headers=get_new_tenant_header(tenant)) as response:
            response.raise_for_status()
            items = json.loads(response.text)
        return items

    @log_call_errors
    def put_items(self, tenant, data):
        """Put information for multiple BOS items"""
        LOGGER.debug("PUT %s for tenant=%s with body=%s", self.base_url, tenant, data)
        with self.session.put(self.base_url, json=data, headers=get_new_tenant_header(tenant)) as response:
            response.raise_for_status()
            items = json.loads(response.text)
        return items

    @log_call_errors
    def delete_items(self, **kwargs):
        """Delete information for multiple BOS items"""
        headers = None
        if "tenant" in kwargs:
            tenant = kwargs.pop("tenant")
            headers = get_new_tenant_header(tenant)
            LOGGER.debug("DELETE %s for tenant=%s with params=%s", self.base_url, tenant, kwargs)
        else:
            LOGGER.debug("DELETE %s with params=%s", self.base_url, kwargs)
        with self.session.delete(self.base_url, params=kwargs, headers=headers) as response:
            response.raise_for_status()
            return json.loads(response.text) if response.text else None
