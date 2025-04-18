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
"""
TenantAwareDBWrapper class
"""

from abc import ABC

from typing import Generic

from bos.common.tenant_utils import get_tenant_aware_key

from .dbwrapper import DBWrapper
from .defs import BosDataRecord as DataT

class TenantAwareDBWrapper(DBWrapper[DataT], Generic[DataT], ABC):
    """A wrapper around a Redis database connection, for a database
    with tenant-aware keys
    """
    def has_tenanted_entry(self, name: str, tenant: str | None, /) -> bool:
        """
        Checks if data exists for given name/tenant
        """
        return get_tenant_aware_key(name, tenant) in self

    def tenanted_get(self, name: str, tenant: str | None, /) -> DataT:
        """Get the data for the given name/tenant."""
        return self.get(get_tenant_aware_key(name, tenant))

    def tenanted_get_and_delete(self, name: str, tenant: str | None, /) -> DataT:
        """Get the data for the given name/tenant and delete it from the DB."""
        return self.get_and_delete(get_tenant_aware_key(name, tenant))

    def tenanted_put(self, name: str, tenant: str | None, new_data: DataT, /) -> None:
        """Put data in to the database, replacing any old data."""
        self.put(get_tenant_aware_key(name, tenant), new_data)

    def tenanted_delete(self, name: str, tenant: str | None, /) -> None:
        """Deletes data from the database."""
        return self.delete(get_tenant_aware_key(name, tenant))

    def tenanted_mput(self, name_tenant_data_map: dict[tuple[str, str|None], DataT], /) -> None:
        """Put data in to the database, replacing any old data."""
        self.mput({ get_tenant_aware_key(*name_tenant_tuple): data
                    for name_tenant_tuple, data in name_tenant_data_map.items() })
