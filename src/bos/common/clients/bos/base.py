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
from collections.abc import Iterable, Mapping
import logging
from typing import cast

from bos.common.clients.endpoints import BaseEndpoint
from bos.common.clients.endpoints.base_generic_endpoint import GetDeleteKwargs, RequestKwargs
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

def get_delete_request_kwargs(tenant: str|None,
                              uri: str|None=None,
                              params: Mapping|None=None) -> GetDeleteKwargs:
    kwargs = GetDeleteKwargs()
    if tenant:
        kwargs["headers"] = get_new_tenant_header(tenant)
    if uri is not None:
        kwargs["uri"] = uri
    if params is not None:
        kwargs["params"] = params
    return kwargs

def request_kwargs(tenant: str|None,
                   uri: str|None=None,
                   json: Mapping|Iterable|None=None,
                   params: Mapping|None=None) -> RequestKwargs:
    get_delete_kwargs = get_delete_request_kwargs(tenant=tenant, uri=uri, params=params)
    kwargs = RequestKwargs(**get_delete_kwargs)
    if json is not None:
        kwargs["json"] = json
    return kwargs


class BaseBosGetItemEndpoint[ReturnT: Mapping](BaseBosEndpoint, ABC):
    """
    This base class provides generic access to the BOS API.
    The individual endpoint needs to be overridden for a specific endpoint.
    """
    def get_item(self, item_id: str, tenant: str|None) -> ReturnT:
        """Get information for a single BOS item"""
        kwargs = get_delete_request_kwargs(uri=item_id, tenant=tenant)
        return cast(ReturnT, self.get(**kwargs))


class BaseBosGetItemsEndpoint[ParamsT: Mapping|None, ReturnT: Mapping](BaseBosEndpoint, ABC):
    """
    This base class provides generic access to the BOS API.
    The individual endpoint needs to be overridden for a specific endpoint.
    """
    def get_items(self, tenant: str|None, params: ParamsT) -> list[ReturnT]:
        """Get information for all BOS items"""
        kwargs = get_delete_request_kwargs(params=params, tenant=tenant)
        return cast(list[ReturnT], self.get(**kwargs))


class BaseBosUpdateItemEndpoint[DataT: Mapping, ReturnT: Mapping](BaseBosEndpoint, ABC):
    """
    This base class provides generic access to the BOS API.
    The individual endpoint needs to be overridden for a specific endpoint.
    """
    def update_item(self, item_id: str, tenant: str|None, data: DataT) -> ReturnT:
        """Update information for a single BOS item"""
        kwargs = request_kwargs(uri=item_id, json=data, tenant=tenant)
        return cast(ReturnT, self.patch(**kwargs))


class BaseBosUpdateItemsEndpoint[
    ParamsT: Mapping|None,
    DataT: Iterable|Mapping,
    ReturnT: Mapping
](BaseBosEndpoint, ABC):
    """
    This base class provides generic access to the BOS API.
    The individual endpoint needs to be overridden for a specific endpoint.
    """
    def update_items(self, tenant: str|None, data: DataT, params: ParamsT) -> list[ReturnT]:
        """Update information for multiple BOS items"""
        kwargs = request_kwargs(json=data, params=params, tenant=tenant)
        return cast(list[ReturnT], self.patch(**kwargs))


class BaseBosPostItemEndpoint[DataT: Mapping|None, ReturnT: Mapping](BaseBosEndpoint, ABC):
    """
    This base class provides generic access to the BOS API.
    The individual endpoint needs to be overridden for a specific endpoint.
    """
    def post_item(self, item_id: str, tenant: str|None, data: DataT) -> ReturnT:
        """Post information for a single BOS item"""
        kwargs = request_kwargs(uri=item_id, json=data, tenant=tenant)
        return cast(ReturnT, self.post(**kwargs))


class BaseBosPutItemsEndpoint[DataT: Mapping](BaseBosEndpoint, ABC):
    """
    This base class provides generic access to the BOS API.
    The individual endpoint needs to be overridden for a specific endpoint.
    """
    def put_items(self, tenant: str|None, data: Iterable[DataT]) -> list[DataT]:
        """Put information for multiple BOS items"""
        kwargs = request_kwargs(json=data, tenant=tenant)
        return cast(list[DataT], self.put(**kwargs))


class BaseBosDeleteItemsEndpoint[ParamsT: Mapping|None](BaseBosEndpoint, ABC):
    """
    This base class provides generic access to the BOS API.
    The individual endpoint needs to be overridden for a specific endpoint.
    """
    def delete_items(self, tenant: str|None, params: ParamsT) -> None:
        """Delete information for multiple BOS items"""
        kwargs = get_delete_request_kwargs(params=params, tenant=tenant)
        self.delete(**kwargs)

### The following are for non-tenant-aware endpoints, which just auto-fill tenant=None

class BaseBosNonTenantAwareGetItemEndpoint[ReturnT: Mapping](BaseBosGetItemEndpoint[ReturnT], ABC):
    """
    This base class provides generic access to the BOS API for non-tenant-aware endpoints
    The individual endpoint needs to be overridden for a specific endpoint.
    """
    def get_item_untenanted(self, item_id: str) -> ReturnT:
        """Get information for a single BOS item"""
        return self.get_item(item_id=item_id, tenant=None)


class BaseBosNonTenantAwareGetItemsEndpoint[
    ParamsT: Mapping|None,
    ReturnT: Mapping
](BaseBosGetItemsEndpoint[ParamsT, ReturnT], ABC):
    """
    This base class provides generic access to the BOS API for non-tenant-aware endpoints
    The individual endpoint needs to be overridden for a specific endpoint.
    """
    def get_items_untenanted(self, params: ParamsT) -> list[ReturnT]:
        """Get information for all BOS items"""
        return self.get_items(tenant=None, params=params)

class BaseBosNonTenantAwareUpdateItemEndpoint[
    DataT: Mapping,
    ReturnT: Mapping
](BaseBosUpdateItemEndpoint[DataT, ReturnT], ABC):
    """
    This base class provides generic access to the BOS API for non-tenant-aware endpoints
    The individual endpoint needs to be overridden for a specific endpoint.
    """
    def update_item_untenanted(self, item_id: str, data: DataT) -> ReturnT:
        """Update information for a single BOS item"""
        return self.update_item(item_id=item_id, tenant=None, data=data)

class BaseBosNonTenantAwareUpdateItemsEndpoint[
    ParamsT: Mapping|None,
    DataT: Iterable|Mapping,
    ReturnT: Mapping
](BaseBosUpdateItemsEndpoint[ParamsT, DataT, ReturnT], ABC):
    """
    This base class provides generic access to the BOS API for non-tenant-aware endpoints
    The individual endpoint needs to be overridden for a specific endpoint.
    """
    def update_items_untenanted(self, data: DataT, params: ParamsT) -> list[ReturnT]:
        """Update information for multiple BOS items"""
        return self.update_items(tenant=None, data=data, params=params)

class BaseBosNonTenantAwarePutItemsEndpoint[DataT: Mapping](BaseBosPutItemsEndpoint[DataT], ABC):
    """
    This base class provides generic access to the BOS API for non-tenant-aware endpoints
    The individual endpoint needs to be overridden for a specific endpoint.
    """
    def put_items_untenanted(self, data: Iterable[DataT]) -> list[DataT]:
        """Put information for multiple BOS Items"""
        return self.put_items(tenant=None, data=data)

class BaseBosNonTenantAwareDeleteItemsEndpoint[
    ParamsT: Mapping|None
](BaseBosDeleteItemsEndpoint[ParamsT], ABC):
    """
    This base class provides generic access to the BOS API for non-tenant-aware endpoints
    The individual endpoint needs to be overridden for a specific endpoint.
    """
    def delete_items_untenanted(self, params: ParamsT) -> None:
        """Delete information for multiple BOS items"""
        self.delete_items(tenant=None, params=params)
