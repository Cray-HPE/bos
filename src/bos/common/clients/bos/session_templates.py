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

from .base import BaseBosTenantAwareEndpoint

LOGGER = logging.getLogger(__name__)


class SessionTemplateEndpoint(BaseBosTenantAwareEndpoint):
    ENDPOINT = 'sessiontemplates'

    def get_session_template(self, session_template_id, tenant):
        return self.get_item(session_template_id, tenant)

    def get_session_templates(self, **kwargs):
        return self.get_items(**kwargs)

    def update_session_template(self, session_template_id, tenant, data):
        return self.update_item(session_template_id, tenant, data)

    def update_session_templates(self, data):
        raise Exception("Session templates don't support a bulk update")
