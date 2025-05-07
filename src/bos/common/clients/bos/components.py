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
from collections.abc import Iterable
import logging
from typing import Unpack

from bos.common.types.components import (ComponentData,
                                         ComponentRecord,
                                         ComponentUpdateFilter,
                                         GetComponentsFilter)
from bos.common.types.components import ComponentBulkUpdateParams as CompBulkUpdateParams

from .base import (BaseBosNonTenantAwareGetItemEndpoint,
                   BaseBosNonTenantAwareGetItemsEndpoint,
                   BaseBosNonTenantAwareUpdateItemEndpoint,
                   BaseBosNonTenantAwareUpdateItemsEndpoint,
                   BaseBosNonTenantAwarePutItemsEndpoint)
from .options import options

LOGGER = logging.getLogger(__name__)

type CompList = list[ComponentRecord]
type CompUpdateData = ComponentData | ComponentRecord
type CompBulkUpdateData = CompList | ComponentUpdateFilter

class ComponentEndpoint(
    BaseBosNonTenantAwareGetItemEndpoint[ComponentRecord],
    BaseBosNonTenantAwareGetItemsEndpoint[GetComponentsFilter, ComponentRecord],
    BaseBosNonTenantAwareUpdateItemEndpoint[CompUpdateData, ComponentRecord],
    BaseBosNonTenantAwareUpdateItemsEndpoint[CompBulkUpdateParams, CompBulkUpdateData,
                                             ComponentRecord],
    BaseBosNonTenantAwarePutItemsEndpoint[ComponentRecord]
):
    ENDPOINT = 'components'

    def get_component(self, component_id: str) -> ComponentRecord:
        return self.get_item_untenanted(component_id)

    def get_components(self, **kwargs: Unpack[GetComponentsFilter]) -> CompList:
        page_size = kwargs.get("page_size")
        if page_size is None:
            kwargs["page_size"] = page_size = options.max_component_batch_size
        results = self.get_items_untenanted(params=kwargs)
        if page_size == 0:
            return results
        next_page = results
        while len(next_page) == page_size:
            last_id = next_page[-1]["id"]
            kwargs["start_after_id"]=last_id
            next_page = self.get_items_untenanted(params=kwargs)
            results.extend(next_page)
        return results

    def update_component(self, component_id: str, data: CompUpdateData) -> ComponentRecord:
        return self.update_item_untenanted(component_id, data)

    def update_components(self, data: CompBulkUpdateData,
                          **params: Unpack[CompBulkUpdateParams]) -> CompList:
        return self.update_items_untenanted(data, params=params)

    def put_components(self, data: Iterable[ComponentRecord]) -> list[ComponentRecord]:
        return self.put_items_untenanted(data)
