#!/usr/bin/env python
#
# MIT License
#
# (C) Copyright 2021-2023 Hewlett Packard Enterprise Development LP
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

from bos.common.utils import get_current_timestamp
from bos.operators.base import BaseOperator, main

LOGGER = logging.getLogger('bos.operators.session_completion')


class SessionCompletionOperator(BaseOperator):
    """
    The Session Completion Operator marks sessions complete when all components
    that are part of the session have been disabled.
    """

    @property
    def name(self):
        return 'SessionCompletion'

    # This operator overrides _run and does not use "filters" or "_act", but they are defined here
    # because they are abstract methods in the base class and must be implemented.
    @property
    def filters(self):
        return []

    def _act(self, components):
        return components

    def _run(self) -> None:
        """ A single pass of complete sessions """
        sessions = self._get_incomplete_sessions()
        for session in sessions:
            components = self._get_incomplete_components(session["name"])
            if not components:
                self._mark_session_complete(session["name"], session.get("tenant"))

    def _get_incomplete_sessions(self):
        return self.bos_client.sessions.get_sessions(status = 'running')

    def _get_incomplete_components(self, session_id):
        components = self.bos_client.components.get_components(session = session_id, enabled = True)
        components += self.bos_client.components.get_components(staged_session = session_id)
        return components

    def _mark_session_complete(self, session_id, tenant):
        self.bos_client.sessions.update_session(session_id, tenant, {'status': {'status': 'complete',
                                                                        'end_time': get_current_timestamp()}})
        # This call causes the session status to saved in the database.
        self.bos_client.session_status.post_session_status(session_id, tenant)
        LOGGER.info('Session {} is complete'.format(session_id))


if __name__ == '__main__':
    main(SessionCompletionOperator)
