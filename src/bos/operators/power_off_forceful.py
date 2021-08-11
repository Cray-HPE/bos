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

import logging

import bos.operators.utils.clients.capmc as capmc
from bos.operators.base import BaseOperator, main
from bos.operators.filters import BOSQuery, HSMState, PowerState, TimeSinceLastAction, LastActionIs, StatesMatch, NOT

LOGGER = logging.getLogger('bos.operators.forceful_power_off')


class ForcefulPowerOffOperator(BaseOperator):
    """
    The Forceful Power-Off Operator tells capmc to power-off nodes if:
    - Enabled in the BOS database.
    - DesiredState != CurrentState
    - LastAction = Graceful-Power-Off or Forceful-Power-Off
    - TimeSinceLastAction > wait time (default 5 minutes)
    - Enabled in HSM
    - Powered on.
    """

    @property
    def name(self):
        return 'Forceful-Power-Off'

    # Filters
    @property
    def filters(self):
        return [
            BOSQuery(enabled=True),
            NOT(StatesMatch()),
            LastActionIs('Graceful-Power-Off,Forceful-Power-Off'),
            TimeSinceLastAction(minutes=5),  # TODO: Use configurable option
            HSMState(enabled=True),
            PowerState(state='on')
        ]

    def _act(self, components):
        component_ids = [component['id'] for component in components]
        capmc.power(component_ids, state='off', force=True)
        return components


if __name__ == '__main__':
    main(ForcefulPowerOffOperator)
