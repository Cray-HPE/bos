#
# MIT License
#
# (C) Copyright 2025 Hewlett Packard Enterprise Development LP
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
SessionTemplateDBWrapper class
"""

from bos.common.types.templates import SessionTemplate, update_template_record

from .defs import Databases
from .tenant_aware_dbwrapper import TenantAwareDBWrapper

class SessionTemplateDBWrapper(TenantAwareDBWrapper[SessionTemplate]):
    """
    Wrapper for session templates database
    """

    def __init__(self) -> None:
        super().__init__()
        self.tenant_aware_patch = self._tenant_aware_patch

    @property
    def db_id(self) -> Databases:
        return Databases.SESSION_TEMPLATES

    @classmethod
    def _patch_data(cls, data: SessionTemplate, new_data: SessionTemplate) -> None:
        update_template_record(data, new_data)
