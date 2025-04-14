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
from abc import ABC
import logging

from bos.common.clients.endpoints import BaseEndpoint
from bos.common.tenant_utils import get_new_tenant_header
from bos.common.utils import PROTOCOL

LOGGER = logging.getLogger(__name__)

API_VERSION = 'v2'
SERVICE_NAME = 'cray-bos'
BASE_BOS_ENDPOINT = f"{PROTOCOL}://{SERVICE_NAME}/{API_VERSION}"


class BaseBosEndpoint(BaseEndpoint, ABC):
    """
    This base class provides generic access to the BOS API.
    The individual endpoint needs to be overridden for a specific endpoint.
    """
    BASE_ENDPOINT = BASE_BOS_ENDPOINT


class BaseBosNonTenantAwareEndpoint(BaseBosEndpoint, ABC):
    """
    This base class provides generic access to the BOS API for non-tenant-aware endpoints
    The individual endpoint needs to be overridden for a specific endpoint.
    """

    def get_item(self, item_id):
        """Get information for a single BOS item"""
        return self.get(uri=item_id)

    def get_items(self, **kwargs):
        """Get information for all BOS items"""
        return self.get(params=kwargs)

    def update_item(self, item_id, data):
        """Update information for a single BOS item"""
        return self.patch(uri=item_id, json=data)

    def update_items(self, data, **params):
        """Update information for multiple BOS items"""
        kwargs = { "json": data }
        if params:
            kwargs["params"] = params
        return self.patch(**kwargs)

    def put_items(self, data):
        """Put information for multiple BOS Items"""
        return self.put(json=data)

    def delete_items(self, **kwargs):
        """Delete information for multiple BOS items"""
        return self.delete(params=kwargs)


class BaseBosTenantAwareEndpoint(BaseBosEndpoint, ABC):
    """
    This base class provides generic access to the BOS API for tenant aware endpoints.
    The individual endpoint needs to be overridden for a specific endpoint.
    """
    def get_item(self, item_id, tenant):
        """Get information for a single BOS item"""
        kwargs = { "uri": item_id }
        if tenant:
            kwargs["headers"] = get_new_tenant_header(tenant)
        return self.get(**kwargs)

    def get_items(self, tenant: str | None = None, **params):
        """Get information for all BOS items"""
        kwargs = { "params": params }
        if tenant:
            kwargs["headers"] = get_new_tenant_header(tenant)
        return self.get(**kwargs)

    def update_item(self, item_id, tenant, data):
        """Update information for a single BOS item"""
        kwargs = { "uri": item_id, "json": data }
        if tenant:
            kwargs["headers"] = get_new_tenant_header(tenant)
        return self.patch(**kwargs)

    def update_items(self, tenant, data, **params):
        """Update information for multiple BOS items"""
        kwargs = { "json": data }
        if tenant:
            kwargs["headers"] = get_new_tenant_header(tenant)
        if params:
            kwargs["params"] = params
        return self.patch(**kwargs)

    def post_item(self, item_id, tenant, data=None):
        """Post information for a single BOS item"""
        kwargs = { "uri": item_id, "json": data }
        if tenant:
            kwargs["headers"] = get_new_tenant_header(tenant)
        return self.post(**kwargs)

    def put_items(self, tenant, data):
        """Put information for multiple BOS items"""
        kwargs = { "json": data }
        if tenant:
            kwargs["headers"] = get_new_tenant_header(tenant)
        return self.put(**kwargs)

    def delete_items(self, tenant: str | None = None, **params):
        """Delete information for multiple BOS items"""
        kwargs = { "params": params }
        if tenant:
            kwargs["headers"] = get_new_tenant_header(tenant)
        return self.delete(**kwargs)
