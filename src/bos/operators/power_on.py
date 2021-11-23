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

import bos.operators.utils.clients.capmc as capmc
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
                [TimeSinceLastAction(minutes=5)]  # TODO: Use configurable option
            ),
            HSMState(enabled=True),
            PowerState(state='off')
        ]

    def _act(self, components):
        configurations = defaultdict(list)
        for component in components:
            config_name = component.get('desiredState', {}).get('configuration', '')
            if not config_name:
                continue
            configurations[config_name].append(components['id'])
        for config_name, ids in configurations.items():
            cfs.set_configuration(ids, config_name)
            # TODO: Add BOS session id
        component_ids = [component['id'] for component in components]
        capmc.power(component_ids, state='on')
        return components


if __name__ == '__main__':
    main(PowerOnOperator)