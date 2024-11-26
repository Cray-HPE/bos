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
import threading

from bos.common.utils import RetrySessionManager

from .components import ComponentEndpoint
from .sessions import SessionEndpoint
from .session_templates import SessionTemplateEndpoint
from .sessions_status import SessionStatusEndpoint


class BOSClient(RetrySessionManager):

    def __init__(self):
        self._components = None
        self._sessions = None
        self._session_status = None
        self._session_templates = None

    @property
    def components(self) -> ComponentEndpoint:
        if self._components is None:
            self._components = ComponentEndpoint(self.session)
        return self._components

    @property
    def sessions(self) -> SessionEndpoint:
        if self._sessions is None:
            self._sessions = SessionEndpoint(self.session)
        return self._sessions

    @property
    def session_status(self) -> SessionStatusEndpoint:
        if self._session_status is None:
            self._session_status = SessionStatusEndpoint(self.session)
        return self._session_status

    @property
    def session_templates(self) -> SessionTemplateEndpoint:
        if self._session_templates is None:
            self._session_templates = SessionTemplateEndpoint(self.session)
        return self._session_templates

    def __exit__(self, exc_type, exc_val, exc_tb):
        super().__exit__(exc_type, exc_val, exc_tb)
        self._components = None
        self._sessions = None
        self._session_status = None
        self._session_templates = None
