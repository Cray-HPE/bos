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
BOS session completion operator
"""

import logging

from bos.common.clients.bos import BOSClient
from bos.common.types.components import ComponentRecord
from bos.common.types.sessions import Session, SessionStatus, SessionUpdate
from bos.common.utils import get_current_timestamp
from bos.operators.base import BaseOperator, main
from bos.operators.filters.base import BaseFilter

LOGGER = logging.getLogger(__name__)


class SessionCompletionOperator(BaseOperator):
    """
    The Session Completion Operator marks sessions complete when all components
    that are part of the session have been disabled.
    """

    @property
    def name(self) -> str:
        return 'SessionCompletion'

    # This operator overrides _run and does not use "filters" or "_act", but they are defined here
    # because they are abstract methods in the base class and must be implemented.
    @property
    def filters(self) -> list[BaseFilter]:
        return []

    def _act(self, components: list[ComponentRecord]) -> list[ComponentRecord]:
        return components

    def _run(self) -> None:
        """ A single pass of complete sessions """
        sessions = self._get_incomplete_sessions()
        for session in sessions:
            components = self._get_incomplete_components(session["name"])
            if not components:
                mark_session_complete(session_id=session["name"],
                                      tenant=session.get("tenant"),
                                      bos_client=self.client.bos)

    def _get_incomplete_sessions(self) -> list[Session]:
        return self.client.bos.sessions.get_sessions(status='running')

    def _get_incomplete_components(self, session_id: str) -> list[ComponentRecord]:
        components = self.client.bos.components.get_components(
            session=session_id, enabled=True)
        components += self.client.bos.components.get_components(
            staged_session=session_id)
        return components


# CASMCMS-9288: This function is not a method of the operator class, because it is also called
# by the session setup operator
def mark_session_complete(session_id: str, tenant: str | None, bos_client: BOSClient,
                          err: str | None=None) -> None:
    """
    Update the session to mark it complete and set the end time. If an error message is specified,
    include that as well.
    Save the session status to the database.
    """
    session_status = SessionStatus(status='complete', end_time=get_current_timestamp())
    if err is not None:
        session_status["error"] = err
    patch_data = SessionUpdate(status=session_status)
    bos_client.sessions.update_session(session_id, tenant, patch_data)
    # This call causes the session status to saved in the database.
    bos_client.sessions.post_session_status(session_id, tenant)
    LOGGER.info('Session %s is complete', session_id)


if __name__ == '__main__':
    main(SessionCompletionOperator)
