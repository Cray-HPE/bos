#!/usr/bin/env python
#
# MIT License
#
# (C) Copyright 2021-2026 Hewlett Packard Enterprise Development LP
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

from bos.common.tenant_utils import get_tenant_component_set
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
        sessions = self.bos_client.sessions.get_sessions(status = 'running')
        for session in sessions:
            if self._session_complete(session):
                self._mark_session_complete(session["name"], session.get("tenant"))

    def _session_complete(self, session: dict) -> bool:
        """
        Determines if the session is complete, using the following
        method:

        Finds every component that meets either of the following criteria:

        * It is enabled and its session field is set to the name of this session
        * Its staged_state.session field is set to the name of this session

        CASMCMS-9623: If this session is on behalf of a tenant, filter out any components that
        are not owned by the tenant (according to TAPMS).
        If this session is not run on behalf of a tenant, then no component filtering
        is done. See CASMCMS-9622 for issues that can arise from this.

        Returns True if no components are found (after the filter is applied, if applicable).
        Returns False otherwise.
        """
        session_id = session["name"]

        # Query BOS for all components that are enabled and have the session name in their
        # session field
        components = self.bos_client.components.get_components(session = session_id, enabled = True)

        # Query BOS for all components that have the session name in their staged_state.session
        # field, and append this to our previous list
        components += self.bos_client.components.get_components(staged_session = session_id)

        # If the above did not find any components, then we are done, before even worrying about
        # multi-tenancy. The session is complete.
        if not components:
            return True

        tenant = session.get("tenant")
        if not tenant:
            # This means the session is not run on behalf of a tenant, so just check if our
            # existing list is empty. If so, the session is complete.
            return not bool(components)

        # The BOS API does not support including this filtering as part of the earlier get
        # components request, so we do it here. We could get the tenant component list
        # first and then pass that list as a filter for the get request, but that could
        # potentially be a long list of IDs (possibly more than can be passed as a request
        # parameter). We could add logic to split long lists up into multiple API
        # requests, but at that point, the solution here is the cleaner option.

        # Get the component IDs owned by the tenant
        tenant_comp_ids: set[str] = get_tenant_component_set(tenant)

        # We already know the components list is not empty. The only way we can return
        # true is if no components in the list belongs to this tenant
        return all(comp["id"] not in tenant_comp_ids for comp in components)

    def _mark_session_complete(self, session_id, tenant):
        self.bos_client.sessions.update_session(session_id, tenant,
                                                { 'status': { 'status': 'complete',
                                                              'end_time': get_current_timestamp()
                                                            }})
        # This call causes the session status to saved in the database.
        self.bos_client.session_status.post_session_status(session_id, tenant)
        LOGGER.info('Session %s is complete', session_id)


if __name__ == '__main__':
    main(SessionCompletionOperator)
