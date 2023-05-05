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
import json
import logging

from .base import BASE_ENDPOINT, log_call_errors
from bos.common.tenant_utils import get_new_tenant_header
from bos.common.utils import requests_retry_session

LOGGER = logging.getLogger('bos.operators.utils.clients.bos.sessions_status')


class SessionStatusEndpoint(object):
    ENDPOINT = 'sessions'

    def __init__(self):
        self.base_url = "%s/%s" % (BASE_ENDPOINT, self.ENDPOINT)

    @log_call_errors
    def get_session_status(self, session_id, tenant):
        """Get information for a single BOS item"""
        url = self.base_url + '/' + session_id + '/status'
        session = requests_retry_session()
        response = session.get(url, headers=get_new_tenant_header(tenant))
        response.raise_for_status()
        item = json.loads(response.text)
        return item

    @log_call_errors
    def post_session_status(self, session_id, tenant):
        """
        Post information for a single BOS Session status.
        This basically saves the BOS Session status to the database.
        """
        session = requests_retry_session()
        url = self.base_url + '/' + session_id + '/status'
        response = session.post(url, headers=get_new_tenant_header(tenant))
        response.raise_for_status()
        items = json.loads(response.text)
        return items
