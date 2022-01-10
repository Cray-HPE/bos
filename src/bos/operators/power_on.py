#!/usr/bin/env python
# Copyright 2021 Hewlett Packard Enterprise Development LP
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
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# (MIT License)

from collections import defaultdict
import logging

import bos.operators.utils.clients.bss as bss
import bos.operators.utils.clients.capmc as capmc
import bos.operators.utils.clients.cfs as cfs
from bos.operators.utils.clients.bos.options import options
from bos.operators.base import BaseOperator, main
from bos.operators.filters import BOSQuery, HSMState, PowerState, TimeSinceLastAction, LastActionIs, DesiredStateIsNone, NOT, OR

LOGGER = logging.getLogger('bos.operators.power_on')


class PowerOnOperator(BaseOperator):
    """
    The Power-On Operator tells capmc to power-on nodes if:
    - Enabled in the BOS database.
    - DesiredState != None
    - LastAction != Power-On OR TimeSinceLastAction > wait time (default 5 minutes)
    - Enabled in HSM
    - Powered off.
    """

    @property
    def name(self):
        return 'Power-On'

    # Filters
    @property
    def filters(self):
        return [
            BOSQuery(enabled=True),
            NOT(DesiredStateIsNone()),
            OR(
                # If the last action was power-on, wait before retrying
                [NOT(LastActionIs('Power-On'))],
                [TimeSinceLastAction(seconds=options.max_component_wait_time)]
            ),
            HSMState(enabled=True),
            PowerState(state='off')
        ]

    def _act(self, components):
        self._set_cfs(components)
        self._set_bss(components)
        component_ids = [component['id'] for component in components]
        capmc.power(component_ids, state='on')
        return components

    @staticmethod
    def _set_cfs(components):
        configurations = defaultdict(list)
        for component in components:
            config_name = component.get('desiredState', {}).get('configuration', '')
            if not config_name:
                continue
            bos_session = component.get('session')
            key = (config_name, bos_session)
            configurations[key].append(components['id'])
        for key, ids in configurations.items():
            config_name, bos_session = key
            cfs.patch_desired_config(ids, config_name,
                                     tags={'bos_session': bos_session})

    @staticmethod
    def _set_bss(components):
        parameters = defaultdict(set)
        for component in components:
            boot_artifacts = component.get('desiredState', {}).get('bootArtifacts', {})
            kernel = boot_artifacts.get('kernel')
            kernel_parameters = boot_artifacts.get('kernel_parameters')
            initrd = boot_artifacts.get('initrd')
            if not any([kernel, kernel_parameters, initrd]):
                continue
            key = (kernel, kernel_parameters, initrd)
            parameters[key].add(components['id'])
        for key, nodes in parameters.items():
            kernel, kernel_parameters, initrd = key
            bss.set_bss(node_set=nodes, kernel_params=kernel,
                        kernel=kernel_parameters, initrd=initrd)

    @staticmethod
    def _set_bss(components):
        parameters = defaultdict(set)
        for component in components:
            boot_artifacts = component.get('desiredState', {}).get('bootArtifacts', {})
            kernel = boot_artifacts.get('kernel')
            kernel_parameters = boot_artifacts.get('kernel_parameters')
            initrd = boot_artifacts.get('initrd')
            if not any([kernel, kernel_parameters, initrd]):
                continue
            key = (kernel, kernel_parameters, initrd)
            parameters[key].add(components['id'])
        for key, nodes in parameters.items():
            kernel, kernel_parameters, initrd = key
            bss.set_bss(node_set=nodes, kernel_params=kernel_parameters,
                        kernel=kernel, initrd=initrd)

if __name__ == '__main__':
    main(PowerOnOperator)
