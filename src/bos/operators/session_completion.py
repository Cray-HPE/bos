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
from bos.operators.utils.clients.bos.components import get_components
from bos.operators.utils.clients.bos.sessions import get_sessions, update_session

LOGGER = logging.getLogger('bos.operators.session_complete')


class SessionCompletionOperator(BaseOperator):
    """
    The Session Completion Operator marks sessions complete when all components
    that are part of the session have been disabled.
    """

    @property
    def name(self):
        return 'SessionCompletion'

    def _run(self) -> None:
        """ A single pass of complete sessions """
        sessions = self._get_incomplete_sessions()
        for session in sessions:
            components = self._get_incomplete_components(session)
            if not components:
                self._mark_session_complete(session)

    @staticmethod
    def _get_incomplete_sessions():
        return get_sessions(status='running')

    @staticmethod
    def _get_incomplete_components(session_id):
        return get_components(session=session_id, enabled=True)

    @staticmethod
    def _mark_session_complete(session_id):
        update_session(session_id, {'status': {'status': 'complete'}})
        LOGGER.info('Session {} is complete'.format(session_id))


if __name__ == '__main__':
    main(SessionCompletionOperator)
