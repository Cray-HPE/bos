#!/usr/bin/env python
#
# MIT License
#
# (C) Copyright 2022-2025 Hewlett Packard Enterprise Development LP
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
BOS component discovery operator
"""

import logging

from bos.common.types.components import ComponentRecord, ComponentStagedState
from bos.common.values import Action, EMPTY_ACTUAL_STATE, EMPTY_DESIRED_STATE
from bos.operators.base import BaseActionOperator, main
from bos.operators.filters.base import BaseFilter

LOGGER = logging.getLogger(__name__)


class DiscoveryOperator(BaseActionOperator):
    """
    The Discovery operator periodically queries the set of components
    known by HSM and BOS and reconciles any missing entries. It does
    NOT remove any entries that do not exist, as we do not want to lose
    any records caused by transient loss or hardware swap actions.
    """

    action = Action.newly_discovered
    frequency_option = "discovery_frequency"

    def _new_component(self, component_id: str) -> ComponentRecord:
        """
        Return a new component record for the specified ID
        """
        return ComponentRecord(
            id=component_id,
            actual_state=EMPTY_ACTUAL_STATE,
            desired_state=EMPTY_DESIRED_STATE,
            staged_state=ComponentStagedState(),
            last_action=self._component_last_action,
            enabled=False,
            error='',
            session='')

    # This operator overrides _run and does not use "filters" or "_act", but they are defined here
    # because they are abstract methods in the base class and must be implemented.
    @property
    def filters(self) -> list[BaseFilter]:
        return []

    def _act(self, components: list[ComponentRecord]) -> list[ComponentRecord]:
        return components

    def _run(self) -> None:
        """
        A single iteration of discovery.
        """
        missing_component_ids = self.missing_components
        if not missing_component_ids:
            LOGGER.debug("No new components discovered.")
            return
        LOGGER.debug("Processing new xname entities: %s", missing_component_ids)
        components_to_add = [self._new_component(comp_id) for comp_id in missing_component_ids]
        LOGGER.info("%d new component(s) from HSM.", len(components_to_add))
        for chunk in self._chunk_components(components_to_add):
            self.client.bos.components.put_components(chunk)
            LOGGER.info("%d new component(s) added to BOS!", len(chunk))

    @property
    def bos_components(self) -> set[str]:
        """
        The set of component IDs currently known to BOS
        """
        components = set()
        for component in self.client.bos.components.get_components():
            components.add(component['id'])
        return components

    @property
    def hsm_xnames(self) -> set[str]:
        """
        The set of component IDs currently known to HSM State Manager
        """
        return self.client.hsm.state_components.read_all_node_xnames()

    @property
    def missing_components(self) -> list[str]:
        """
        The sorted list of component IDs that need to be added to BOS.
        """
        return sorted(self.hsm_xnames - self.bos_components)


if __name__ == '__main__':
    main(DiscoveryOperator)
