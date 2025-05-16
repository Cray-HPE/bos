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

"""
BOS component configuration operator
"""

import logging

from bos.common.types.components import ComponentRecord
from bos.common.values import Status
from bos.operators.base import BaseOperator, main
from bos.operators.filters.base import BaseFilter

LOGGER = logging.getLogger(__name__)


class ConfigurationOperator(BaseOperator):
    """
    The Configure Operator sets the desired configuration in CFS if:
    - Enabled in the BOS database and the current phase is configuring
    - DesiredConfiguration != SetConfiguration

    The Configuration step can take place at any time before power-on.
    Because this step is therefore outside the normal boot flow, it does not
    inherit from BaseActionOperator, so it is not recorded to the component data.
    """

    # Filters
    @property
    def filters(self) -> list[BaseFilter]:
        return [
            self.BOSQuery(enabled=True, status=Status.configuring),
            self.DesiredConfigurationSetInCFS(negate=True)
        ]

    def _act(self, components: list[ComponentRecord]) -> list[ComponentRecord]:
        if components:
            self.client.cfs.components.set_cfs(components, enabled=True)
        return components


if __name__ == '__main__':
    main(ConfigurationOperator)
