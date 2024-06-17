#
# MIT License
#
# (C) Copyright 2024 Hewlett Packard Enterprise Development LP
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

# coding: utf-8

from __future__ import absolute_import
import unittest

from flask import json
from six import BytesIO

from bos.server.models.problem_details import ProblemDetails  # noqa: E501
from bos.server.models.v2_apply_staged_components import V2ApplyStagedComponents  # noqa: E501
from bos.server.models.v2_apply_staged_status import V2ApplyStagedStatus  # noqa: E501
from bos.server.test import BaseTestCase


class TestApplystagedController(BaseTestCase):
    """ApplystagedController integration test stubs"""

    def test_post_v2_apply_staged(self):
        """Test case for post_v2_apply_staged

        Start a staged session for the specified components
        """
        v2_apply_staged_components = {
  "xnames" : [ "xnames", "xnames" ]
}
        headers = { 
        }
        response = self.client.open(
            '/apis/bos/v2/applystaged',
            method='POST',
            headers=headers,
            data=json.dumps(v2_apply_staged_components),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
