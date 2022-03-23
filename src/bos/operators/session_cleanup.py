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
from datetime import datetime, timedelta

from bos.common.utils import load_timestamp
from bos.operators.base import BaseOperator, main
from bos.operators.utils.clients.bos.options import options

LOGGER = logging.getLogger('bos.operators.session_cleanup')


class SessionCleanupOperator(BaseOperator):
    """
    The Session Completion Operator marks sessions complete when all components
    that are part of the session have been disabled.
    """
    def __init__(self):
        super().__init__()
        self._max_age = None

    @property
    def name(self):
        return 'SessionCleanup'

    @property
    def max_age(self):
        """
        A datetime value indicating the oldest possible time to keep
        any given completed session. This operator will remove completed
        sessions that are older than this date.
        """
        if self._max_age:
            return self._max_age
        delta = timedelta(seconds=options.cleanup_completed_session_age)
        self._max_age = datetime.now() - delta
        return self.max_age

    @property
    def disabled(self):
        """
        When users set the cleanup time to 0, no cleanup behavior is desired.
        """
        return not bool(options.cleanup_completed_session_age)

    # This operator overrides _run and does not use "filters" or "_act", but they are defined here
    # because they are abstract methods in the base class and must be implemented.
    @property
    def filters(self):
        return []

    def _act(self, components):
        return components

    def _run(self) -> None:
        """ A single pass of Session Cleanup. """
        sessions_to_delete = []

        # Obtain a new max age for deletion
        self._max_age = None
        options.update()

        # Exit early if configured so.
        if self.disabled:
            return

        for session in self.bos_client.sessions.get_sessions(status='complete'):
            session_end_time = load_timestamp(session['status']['end_time'])
            LOGGER.info(" ---> Comparison", session_end_time, self.max_age)
            if session_end_time < self.max_age:
                # This completed session has an age "younger" than our maximum
                # old age allowed; flag it for deletion.
                sessions_to_delete.append({'name': session['name']})
        if sessions_to_delete:
            LOGGER.info("Cleaning up completed session(s): "
                        ', '.join(sorted([session['name'] for session in sessions_to_delete])))
            self.bos_client.sessions.delete_sessions(sessions_to_delete)

if __name__ == '__main__':
    main(SessionCleanupOperator)
