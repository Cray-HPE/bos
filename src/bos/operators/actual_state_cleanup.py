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
BOS component actual state cleanup operator
"""

import logging

from bos.common.clients.bos.options import options
from bos.common.utils import duration_to_timedelta
from bos.common.types.components import ComponentRecord
from bos.common.values import Action, EMPTY_ACTUAL_STATE
from bos.operators.base import BaseActionOperator, main
from bos.operators.filters import ActualStateAge, ActualBootStateIsSet
from bos.operators.filters.base import BaseFilter

LOGGER = logging.getLogger(__name__)


class ActualStateCleanupOperator(BaseActionOperator):
    """
    The ActualStateCleanupOperator is responsible for identifying components that have
    an expired actual state set (from boot artifacts). Typically this can happen when
    a node is NMI'd, the node management network goes down, or there is an otherwise
    undetected kernel panic that prevents system services from reporting in, a user
    has booted an operating system that does not have the bos-state-reporter, or
    any other event preventing periodic actual state reporting, eventually
    a node's actual booted state can no longer be trusted. This operator's job is to
    zero the actual booted state record when the configured TTL has expired.
    """

    action = Action.actual_state_cleanup

    # Filters
    @property
    def filters(self) -> list[BaseFilter]:
        return [
            self.BOSQuery(),
            ActualBootStateIsSet(),
            ActualStateAge(seconds=duration_to_timedelta(
                options.component_actual_state_ttl).total_seconds())
        ]

    def _act(self, components: list[ComponentRecord]) -> list[ComponentRecord]:
        data: list[ComponentRecord] = [
            ComponentRecord(id=component['id'], actual_state=EMPTY_ACTUAL_STATE)
            for component in components
        ]
        if data:
            LOGGER.info('Found %d components that require updates', len(data))
            LOGGER.debug('Calling to update with payload: %s', data)
            self.client.bos.components.update_components(data)
        return components


if __name__ == '__main__':
    main(ActualStateCleanupOperator)
