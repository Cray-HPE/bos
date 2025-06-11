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

from typing import Literal, TypedDict

from .base import BaseHsmEndpoint
from .types import LocksComponentsDataArray


class LocksGetListParams(TypedDict, total=True):
    """
    Other params are supported in the API spec, but we only define here the ones we care about
    """
    # Other types are supported, but we always query for Nodes
    type: Literal['Node']
    # Similarly, we always query for locked nodes
    locked: Literal[True]


def _locks_get_list_params() -> LocksGetListParams:
    """
    Return the parameters we use when listing locked nodes
    """
    return LocksGetListParams(type="Node", locked=True)


class LocksEndpoint(BaseHsmEndpoint[LocksGetListParams, LocksComponentsDataArray]):
    ENDPOINT = 'locks/status'

    def get_locked_nodes(self) -> set[str]:
        """
        Returns the set of xname strings of all locked nodes
        """
        lock_comps_data_array = self.get_list(params=_locks_get_list_params())

        try:
            components = lock_comps_data_array["Components"]
        except KeyError:
            return set()
        return { component["ID"] for component in components if "ID" in component }
