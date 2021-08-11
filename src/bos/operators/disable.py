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
from bos.operators.filters import BOSQuery, PowerState, StatesMatch, DesiredStateIsNone, OR

LOGGER = logging.getLogger('bos.operators.disable')


class DisableOperator(BaseOperator):
    """
    The Disable Operator marks components as complete and disables them:
    - Enabled in the BOS database.
    - and either
        - DesiredState = CurrentState
        - PowerState == On
    - or
        - DesiredState = None
        - PowerState == Off
    """

    @property
    def name(self):
        return 'Complete'

    # Filters
    @property
    def filters(self):
        return [
            BOSQuery(enabled=True),
            OR(
                [StatesMatch(), PowerState(state='on')],
                [DesiredStateIsNone(), PowerState(state='off')],
            )
        ]

    def _act(self, components):
        # This operator takes no actions external to BOS
        # This override must still exist to avoid the NotImplemented error
        pass

    def _update_database(self, components) -> None:
        # Override of the base method to add enabled=False
        super()._update_database(components=components, additional_fields={'enabled': False})


if __name__ == '__main__':
    main(DisableOperator)
