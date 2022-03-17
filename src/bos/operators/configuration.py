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
from collections import defaultdict
import logging

import bos.operators.utils.clients.cfs as cfs
from bos.operators.base import BaseOperator, main
from bos.operators.filters import BOSQuery, DesiredConfigurationIsNone, DesiredConfigurationSetInCFS, \
    BootArtifactStatesMatch, NOT

LOGGER = logging.getLogger('bos.operators.configuration')


class ConfigurationOperator(BaseOperator):
    """
    The Configure Operator sets the desired configuration in CFS if:
    - Enabled in the BOS database.
    - DesiredConfiguration != None
    - DesiredConfiguration != SetConfiguration

    Additional filters are applied before the action.
    BOS enables the node in CFS if:
    - DesiredState == CurrentState

    otherwise BOS disables the node in CFS.
    """

    @property
    def name(self):
        # The Configuration step can take place at any time before power-on.
        # This step is therefore outside the normal boot flow and the name is
        # left empty so this step is not recorded to the component data.
        return ''

    # Filters
    @property
    def filters(self):
        return [
            BOSQuery(enabled=True),
            NOT(DesiredConfigurationIsNone()),
            NOT(DesiredConfigurationSetInCFS())
        ]

    def _act(self, components):
        self._set_cfs(components)
        return components

    @staticmethod
    def _set_cfs(components):
        configurations = defaultdict(list)
        for component in components:
            config_name = component.get('desired_state', {}).get('configuration', '')
            if not config_name:
                continue
            bos_session = component.get('session')
            enabled = False
            if BootArtifactStatesMatch._match(component):
                # BOS won't reboot the node.  Configure now rather than waiting for a reboot.
                enabled = True
            key = (config_name, enabled, bos_session)
            configurations[key].append(components['id'])
        for key, ids in configurations.items():
            config_name, enabled, bos_session = key
            cfs.patch_desired_config(ids, config_name, enabled=enabled,
                                     tags={'bos_session': bos_session})


if __name__ == '__main__':
    main(ConfigurationOperator)
