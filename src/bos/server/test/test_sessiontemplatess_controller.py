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
from bos.server.models.v2_session_template import V2SessionTemplate  # noqa: E501
from bos.server.test import BaseTestCase


class TestSessiontemplatessController(BaseTestCase):
    """SessiontemplatessController integration test stubs"""

    def test_get_v2_sessiontemplate(self):
        """Test case for get_v2_sessiontemplate

        Get session template by id
        """
        headers = { 
        }
        response = self.client.open(
            '/apis/bos/v2/sessiontemplates/{session_template_id}'.format(session_template_id='session_template_id_example'),
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_validate_v2_sessiontemplate(self):
        """Test case for validate_v2_sessiontemplate

        Validate the session template by id
        """
        headers = { 
        }
        response = self.client.open(
            '/apis/bos/v2/sessiontemplatesvalid/{session_template_id}'.format(session_template_id='session_template_id_example'),
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
