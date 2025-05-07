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
import logging

from bos.common.types.components import ComponentRecord
from bos.common.values import Action, Status
from bos.operators.base import BaseOperator, main
from bos.operators.filters.base import BaseFilter

LOGGER = logging.getLogger(__name__)


class GracefulPowerOffOperator(BaseOperator):
    """
    - Enabled in the BOS database and the status is power_off_pending
    - Enabled in HSM
    """

    retry_attempt_field = "power_off_graceful_attempts"

    @property
    def name(self) -> str:
        return Action.power_off_gracefully

    # Filters
    @property
    def filters(self) -> list[BaseFilter]:
        return [
            self.BOSQuery(enabled=True, status=Status.power_off_pending),
            self.HSMState(),
        ]

    def _act(self, components: list[ComponentRecord]) -> list[ComponentRecord]:
        if components:
            component_ids = [component['id'] for component in components]
            self.client.pcs.transitions.soft_off(component_ids)
        return components


if __name__ == '__main__':
    main(GracefulPowerOffOperator)
