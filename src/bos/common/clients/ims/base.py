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
from abc import ABC

from bos.common.clients.endpoints import BaseEndpoint

from .defs import BASE_ENDPOINT as BASE_IMS_ENDPOINT


class BaseImsEndpoint(BaseEndpoint, ABC):
    """
    This base class provides generic access to the IMS API.
    The individual endpoint needs to be overridden for a specific endpoint.
    """
    BASE_ENDPOINT = BASE_IMS_ENDPOINT

    def get_item(self, item_id: str):
        """Get information for a single IMS item"""
        return self.get(uri=item_id)

    def update_item(self, item_id: str, data):
        """Update information for a single IMS item"""
        return self.patch(uri=item_id, json=data)
