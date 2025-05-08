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
HSM State/Components endpoint definitions
"""

import logging
from typing import cast, TypedDict

from bos.common.utils import exc_type_msg

from .base import BaseHsmEndpoint
from .exceptions import HWStateManagerException
from .types import StateComponentsDataArray

LOGGER = logging.getLogger(__name__)


class StateComponentsGetListParams(TypedDict, total=False):
    partition: str


class StateComponentsEndpoint(BaseHsmEndpoint[StateComponentsGetListParams,
                                              StateComponentsDataArray]):
    ENDPOINT = 'State/Components'

    def read_all_node_xnames(self) -> set[str]:
        """
        Queries HSM for the full set of xname components that
        have been discovered; return these as a set.
        """
        component_array = self.get_list()
        try:
            return {
                component['ID']
                for component in component_array['Components']
                if component.get('Type', None) == 'Node'
            }
        except KeyError as ke:
            LOGGER.error("Unexpected API response from HSM: %s",
                         exc_type_msg(ke))
            raise HWStateManagerException(ke) from ke

    def get_components(self, node_list: list[str],
                       enabled: bool|None=None) -> StateComponentsDataArray:
        """
        Get information for all list components HSM

        :return the HSM components
        :rtype Dictionary containing a 'Components' key whose value is a list
        containing each component, where each component is itself represented by a
        dictionary.

        Here is an example of the returned values.
        {
        "Components": [
            {
            "ID": "x3000c0s19b1n0",
            "Type": "Node",
            "State": "Ready",
            "Flag": "OK",
            "Enabled": true,
            "Role": "Compute",
            "NID": 1,
            "NetType": "Sling",
            "Arch": "X86",
            "Class": "River"
            },
            {
            "ID": "x3000c0s19b2n0",
            "Type": "Node",
            "State": "Ready",
            "Flag": "OK",
            "Enabled": true,
            "Role": "Compute",
            "NID": 1,
            "NetType": "Sling",
            "Arch": "X86",
            "Class": "River"
            }
        ]
        }
        """
        if not node_list:
            LOGGER.warning("hsm.get_components called with empty node list")
            return {'Components': []}
        payload = {'ComponentIDs': node_list}
        if enabled is not None:
            payload['enabled'] = [str(enabled)]
        return cast(StateComponentsDataArray, self.post(uri="Query", json=payload))
