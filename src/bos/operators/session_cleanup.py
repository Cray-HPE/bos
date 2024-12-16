#!/usr/bin/env python
#
# MIT License
#
# (C) Copyright 2021-2022, 2024 Hewlett Packard Enterprise Development LP
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
import re

from bos.operators.base import BaseOperator, main
from bos.common.clients.bos.options import options

LOGGER = logging.getLogger(__name__)


class SessionCleanupOperator(BaseOperator):
    """
    The Session Completion Operator marks sessions complete when all components
    that are part of the session have been disabled.
    """

    @property
    def name(self):
        return 'SessionCleanup'

    @property
    def disabled(self):
        """
        When users set the cleanup time to 0, no cleanup behavior is desired.
        """
        options_stripped = re.sub('[^0-9]', '',
                                  options.cleanup_completed_session_ttl)
        return not bool(int(options_stripped))

    # This operator overrides _run and does not use "filters" or "_act", but they are defined here
    # because they are abstract methods in the base class and must be implemented.
    @property
    def filters(self):
        return []

    def _act(self, components):
        return components

    def _run(self) -> None:
        """ A single pass of Session Cleanup. """
        # Obtain a set of options in case this is now disabled
        options.update()

        # Exit early if configured so.
        if self.disabled:
            return

        self.client.bos.sessions.delete_sessions(
            **{
                'status': 'complete',
                'min_age': options.cleanup_completed_session_ttl
            })


if __name__ == '__main__':
    main(SessionCleanupOperator)
