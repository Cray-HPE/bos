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
from collections import defaultdict
from collections.abc import Iterable
import logging
from typing import cast

from .base import BasePcsEndpoint
from .types import PowerStatusAll, PowerStatusGet

LOGGER = logging.getLogger(__name__)


class PowerStatusEndpoint(BasePcsEndpoint):
    ENDPOINT = 'power-status'

    def query(self,
              xname: list[str]|None=None) -> PowerStatusAll:
        """
        This is the one to one implementation to the underlying power control get query.
        For reasons of compatibility with existing calls into older power control APIs,
        existing functions call into this function to preserve the existing functionality
        already implemented.

        Users may specify one of three filters, and a power_status_all (PCS defined schema)
        is returned.

        Per the spec, a power_status_all is returned. power_status_all is an array of power
        statuses.
        """
        params: PowerStatusGet = { "xname": xname } if xname else {}
        # PCS added the POST option for this endpoint in app version 2.3.0
        # (chart versions 2.0.8 and 2.1.5)
        return cast(PowerStatusAll, self.post(json=params))

    def status(self, nodes: Iterable[str]) -> defaultdict[str, set[str]]:
        """
        For a given iterable of nodes, represented by xnames, query PCS for
        the power status. Return a dictionary of nodes that have
        been bucketed by status.

        Args:
          nodes (list): Nodes to get status for
          session (session object): An already instantiated session
          kwargs: Any additional args used for filtering when calling _power_status.
            This can be useful if you want to limit your search to only available or unavailable
            nodes, and allows a more future-proof way of handling arguments to PCS as a catch-all
            parameter.

        Returns:
          status_dict (dict): Keys are different states; values are a literal set of nodes.
            Nodes with errors associated with them are saved with the error value as a
            status key.

        Raises:
          PowerControlException: Any non-nominal response from PCS.
          JSONDecodeError: Error decoding the PCS response
        """
        status_bucket: defaultdict[str, set[str]] = defaultdict(set)
        if not nodes:
            LOGGER.warning("status called without nodes; returning without action.")
            return status_bucket
        power_status_all = self.query(list(nodes))
        for power_status_entry in power_status_all['status']:
            xname = power_status_entry.get('xname')
            if not xname:
                LOGGER.warning("power status response contained item with no xname: %s",
                               power_status_entry)
                continue
            # If the returned xname has an error, it itself is the status regardless of
            # what the powerState field suggests. This is a major departure from how CAPMC
            # handled errors.
            if (error := power_status_entry.get("error")):
                status_bucket[error].add(xname)
                continue
            if (power_status := power_status_entry.get('powerState')):
                status_bucket[power_status.lower()].add(xname)
        return status_bucket

    def node_to_powerstate(self, nodes: Iterable[str]) -> dict[str, str]:
        """
        For an iterable of nodes <nodes>; return a dictionary that maps to the current power state
        for the node in question.
        """
        power_states: dict[str, str] = {}
        if not nodes:
            LOGGER.warning(
                "node_to_powerstate called without nodes; returning without action."
            )
            return power_states
        status_bucket = self.status(nodes)
        for pstatus, nodeset in status_bucket.items():
            for node in nodeset:
                power_states[node] = pstatus
        return power_states
