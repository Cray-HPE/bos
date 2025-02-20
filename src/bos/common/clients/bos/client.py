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
from dataclasses import dataclass

from bos.common.clients.api_client import APIClient

from .components import ComponentEndpoint
from .sessions import SessionEndpoint
from .session_templates import SessionTemplateEndpoint

@dataclass
class BosEndpoints:
    components: ComponentEndpoint | None = None
    sessions: SessionEndpoint | None = None
    session_templates: SessionTemplateEndpoint | None = None

class BOSClient(APIClient[BosEndpoints]):

    @property
    def _init_endpoints(self) -> BosEndpoints:
        return BosEndpoints()

    @property
    def components(self) -> ComponentEndpoint:
        if self._endpoints.components is None:
            self._endpoints.components = ComponentEndpoint(self.requests_session)
        return self._endpoints.components

    @property
    def sessions(self) -> SessionEndpoint:
        if self._endpoints.sessions is None:
            self._endpoints.sessions = SessionEndpoint(self.requests_session)
        return self._endpoints.sessions

    @property
    def session_templates(self) -> SessionTemplateEndpoint:
        if self._endpoints.session_templates is None:
            self._endpoints.session_templates = SessionTemplateEndpoint(self.requests_session)
        return self._endpoints.session_templates
