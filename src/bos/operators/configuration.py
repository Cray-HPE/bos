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
import logging

from bos.common.values import Status
from bos.operators.base import BaseOperator, main
from bos.operators.filters import BOSQuery, NOT

LOGGER = logging.getLogger(__name__)


class ConfigurationOperator(BaseOperator):
    """
    The Configure Operator sets the desired configuration in CFS if:
    - Enabled in the BOS database and the current phase is configuring
    - DesiredConfiguration != SetConfiguration
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
            BOSQuery(enabled=True, status=Status.configuring),
            NOT(self.DesiredConfigurationSetInCFS)
        ]

    def _act(self, components):
        if components:
            self.client.cfs.components.set_cfs(components, enabled=True)
        return components


if __name__ == '__main__':
    main(ConfigurationOperator)
