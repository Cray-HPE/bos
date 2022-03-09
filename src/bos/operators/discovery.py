#!/usr/bin/env python
#
# MIT License
#
# (C) Copyright 2022 Hewlett Packard Enterprise Development LP
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
import logging
import time
from typing import List, NoReturn, Set
from copy import copy

import bos.operators.utils.clients.capmc as capmc
from bos.operators.utils.clients.bos.options import options
from bos.operators.utils.clients.hsm import read_all_node_xnames, HWStateManagerException
from bos.operators.base import BaseOperator, main, _update_log_level
from bos.operators.filters import BOSQuery, HSMState
from bos.operators.utils.clients.bos.components import ComponentEndpoint

LOGGER = logging.getLogger(__name__)

BLANK_STATE = {'bootArtifacts': {'kernel': '',
                                 'kernel_parameters': '',
                                 'initrd': ''},
               'configuration': ''}
NEW_COMPONENT = {'id': None,
                 'actualState': BLANK_STATE,
                 'desiredState': BLANK_STATE,
                 'stagedState': {},
                 'lastAction': {'action': 'Newly Discovered',
                                'numAttempts': 1},
                 'enabled': False,
                 'error': '',
                 'session': ''}

class DiscoveryOperator(BaseOperator):
    """
    The Discovery operator periodically queries the set of components
    known by HSM and BOS and reconciles any missing entries. It does
    NOT remove any entries that do not exist, as we do not want to lose
    any records caused by transient loss or hardware swap actions.
    """

    @property
    def name(self):
        return "Discovery"

    # This operator overrides _run and does not use "filters" or "_act", but they are defined here
    # because they are abstract methods in the base class and must be implemented.
    @property
    def filters(self):
        return []

    def _act(self, components):
        return components

    def run(self) -> NoReturn:
        """
        The core method of the operator that periodically detects and acts on components.
        This includes updating the options and logging level, as well as exception handling and
        sleeping between passes.
        """
        while True:
            start_time = time.time()
            try:
                options.update()
                _update_log_level()
                self._run()
            except Exception as e:
                LOGGER.exception('Unhandled exception detected: {}'.format(e))
            try:
                sleep_time = options.discovery_frequency - (time.time() - start_time)
                if sleep_time > 0:
                    time.sleep(sleep_time)
            except Exception as e:
                LOGGER.exception('Unhandled exception getting polling frequency: {}'.format(e))
                time.sleep(5)  # A small sleep for when exceptions getting the polling frequency

    def _run(self) -> None:
        """
        A single iteration of discovery.
        """
        components_to_add = []
        for component in sorted(self.missing_components):
            LOGGER.debug("Processing new xname entity '%s'"%(component))
            new_component = copy(NEW_COMPONENT)
            new_component['id'] = component
            components_to_add.append(new_component)
        if not components_to_add:
            LOGGER.info("No new component(s) discovered.")
            return
        LOGGER.info("%s new component(s) from HSM." %(len(components_to_add)))
        ce = ComponentEndpoint()
        ce.put_components(components_to_add)
        LOGGER.info("%s new component(s) added to BOS!" %(len(components_to_add)))

    @property
    def bos_components(self) -> Set[str]:
        """
        The set of components currently known to BOS
        """
        components = set()
        for component in self.bos_client.components.get_components():
            components.add(component['id'])
        return components

    @property
    def hsm_xnames(self) -> Set[str]:
        """
        The set of components currently known to HSM State Manager
        """
        return read_all_node_xnames()

    @property
    def missing_components(self) -> Set[str]:
        """
        The set of components that need to be added to BOS.
        """
        return self.hsm_xnames - self.bos_components

if __name__ == '__main__':
    main(DiscoveryOperator)
