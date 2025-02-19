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
from typing import Unpack

from requests_retry_session import RequestsRetryAdapterArgs

from bos.common.clients.api_client import APIClient

from .components import ComponentEndpoint
from .sessions import SessionEndpoint
from .session_templates import SessionTemplateEndpoint

class BOSClient(APIClient):

    def __init__(self, **adapter_kwargs: Unpack[RequestsRetryAdapterArgs]):
        super().__init__(**adapter_kwargs)
        self._components: ComponentEndpoint | None = ComponentEndpoint(self.requests_session)
        self._sessions: SessionEndpoint | None = SessionEndpoint(self.requests_session)
        self._session_templates: SessionTemplateEndpoint | None = SessionTemplateEndpoint(self.requests_session)

    def _clear_endpoint_values(self) -> None:
        self._components = None
        self._sessions = None
        self._session_templates = None

    @property
    def components(self) -> ComponentEndpoint:
        if self._components is None:
            raise ValueError("Attempt to use uninitialized BOS components endpoint")
        return self._components

    @property
    def sessions(self) -> SessionEndpoint:
        if self._sessions is None:
            raise ValueError("Attempt to use uninitialized BOS sessions endpoint")
        return self._sessions

    @property
    def session_templates(self) -> SessionTemplateEndpoint:
        if self._session_templates is None:
            raise ValueError("Attempt to use uninitialized BOS session templates endpoint")
        return self._session_templates
