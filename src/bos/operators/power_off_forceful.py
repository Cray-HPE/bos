#!/usr/bin/env python
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
BOS component forceful power off operator
"""

import logging

from bos.common.clients.bos.options import options
from bos.common.types.components import ComponentRecord
from bos.common.values import Action, Status
from bos.operators.base import BaseActionOperator, main
from bos.operators.filters import TimeSinceLastAction
from bos.operators.filters.base import BaseFilter

LOGGER = logging.getLogger(__name__)


class ForcefulPowerOffOperator(BaseActionOperator):
    """
    The Forceful Power-Off Operator tells pcs to power-off nodes if:
    - Enabled in the BOS database and the status is power_off_gracefully of power_off_forcefully
    - Enabled in HSM
    """

    action = Action.power_off_forcefully
    retry_attempt_field = "power_off_forceful_attempts"

    # Filters
    @property
    def filters(self) -> list[BaseFilter]:
        return [
            self.BOSQuery(enabled=True,
                          status=','.join([
                              Status.power_off_forcefully_called,
                              Status.power_off_gracefully_called
                          ])),
            TimeSinceLastAction(seconds=options.max_power_off_wait_time),
            self.HSMState(),
        ]

    def _act(self, components: list[ComponentRecord]) -> list[ComponentRecord]:
        if components:
            component_ids = [component['id'] for component in components]
            self.client.pcs.transitions.force_off(component_ids)
        return components


if __name__ == '__main__':
    main(ForcefulPowerOffOperator)
