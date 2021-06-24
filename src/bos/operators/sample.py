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

from bos.operators.base import BaseOperator, main
from bos.operators.filters import BOSQuery, HSMEnabled, PowerState, TimeSinceLastAction, OR, LastActionIs

LOGGER = logging.getLogger('bos.operators.sample')


class SampleOperator(BaseOperator):
    """
    This sample operator logs components that meet the following conditions once every 5 minutes:
    - Enabled in the BOS database.
    - At least one of the following is true
        - lastAction was at least 5 minutes ago and the last action was Sample or was blank
        - lastAction was at least 10 minutes ago and the last action was Boot or was Configure
    - Enabled in HSM
    - Powered on.
    """

    @property
    def name(self):
        return 'Sample'

    # Filters
    @property
    def filters(self):
        return [
            BOSQuery(enabled=True),
            OR(
                [LastActionIs('Sample,'), TimeSinceLastAction(minutes=5)],
                [LastActionIs('Boot,Configure'), TimeSinceLastAction(minutes=10)]
            ),
            HSMEnabled(),
            PowerState(state='on')
        ]

    def _act(self, components):
        for component in components:
            LOGGER.info('Sample action for {}'.format(component['id']))
        return components


if __name__ == '__main__':
    main(SampleOperator)
