#!/usr/bin/env python
#
# MIT License
#
# (C) Copyright 2021-2022 Hewlett Packard Enterprise Development LP
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

from bos.common.values import Action, Status
from bos.operators.utils.clients.capmc import disable_based_on_error_xname_on_off, power
from bos.operators.base import BaseOperator, main
from bos.operators.filters import BOSQuery, HSMState

LOGGER = logging.getLogger('bos.operators.power_off_graceful')


class GracefulPowerOffOperator(BaseOperator):
    """
    - Enabled in the BOS database and the status is power_off_pending
    - Enabled in HSM
    """

    retry_attempt_field = "power_off_graceful_attempts"

    @property
    def name(self):
        return Action.power_off_gracefully

    # Filters
    @property
    def filters(self):
        return [
            BOSQuery(enabled=True, status=Status.power_off_pending),
            HSMState(enabled=True),
        ]

    def _act(self, components):
        component_ids = [component['id'] for component in components]
        errors = power(component_ids, state='off', force=False)
        # Update any nodes with errors they encountered
        if errors.nodes_in_error:
            for node in errors.nodes_in_error:
                for component in components:
                    if node == component['id']:
                        index = components.index(component)
                        error = errors.nodes_in_error[node].error_message
                        components[index]['error'] = error
                        components[index]['enabled'] = disable_based_on_error_xname_on_off(error)
                        break
        return components


if __name__ == '__main__':
    main(GracefulPowerOffOperator)
