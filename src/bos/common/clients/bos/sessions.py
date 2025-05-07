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
import logging
from typing import Unpack

from bos.common.types.sessions import Session, SessionFilter, SessionUpdate

from .base import (BaseBosGetItemEndpoint,
                   BaseBosGetItemsEndpoint,
                   BaseBosUpdateItemEndpoint,
                   BaseBosPostItemEndpoint,
                   BaseBosDeleteItemsEndpoint)

LOGGER = logging.getLogger(__name__)


class SessionEndpoint(
    BaseBosGetItemEndpoint[Session],
    BaseBosGetItemsEndpoint[SessionFilter, Session],
    BaseBosUpdateItemEndpoint[SessionUpdate, Session],
    BaseBosPostItemEndpoint[None, Session],
    BaseBosDeleteItemsEndpoint[SessionFilter]
):
    ENDPOINT = 'sessions'

    def get_session(self, session_id: str, tenant: str | None) -> Session:
        return self.get_item(session_id, tenant)

    def get_sessions(self, tenant: str | None=None,
                     **params: Unpack[SessionFilter]) -> list[Session]:
        return self.get_items(tenant=tenant, params=params)

    def update_session(self, session_id: str, tenant: str | None, data: SessionUpdate) -> Session:
        return self.update_item(session_id, tenant, data)

    def delete_sessions(self, tenant: str | None=None, **params: Unpack[SessionFilter]) -> None:
        self.delete_items(tenant=tenant, params=params)

    def post_session_status(self, session_id: str, tenant: str | None) -> Session:
        """
        Post information for a single BOS Session status.
        This basically saves the BOS Session status to the database.
        """
        return self.post_item(f'{session_id}/status', tenant, None)
