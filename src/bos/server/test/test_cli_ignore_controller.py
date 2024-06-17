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

from bos.server.models.one_of_v2_components_update_v2_component_array import OneOfV2ComponentsUpdateV2ComponentArray  # noqa: E501
from bos.server.models.problem_details import ProblemDetails  # noqa: E501
from bos.server.models.unknownbasetype import UNKNOWN_BASE_TYPE  # noqa: E501
from bos.server.models.v2_component_array import V2ComponentArray  # noqa: E501
from bos.server.models.v2_session import V2Session  # noqa: E501
from bos.server.test import BaseTestCase


class TestCliIgnoreController(BaseTestCase):
    """CliIgnoreController integration test stubs"""

    def test_delete_v2_component(self):
        """Test case for delete_v2_component

        Delete a single component
        """
        headers = { 
        }
        response = self.client.open(
            '/apis/bos/v2/components/{component_id}'.format(component_id='component_id_example'),
            method='DELETE',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_patch_v2_components(self):
        """Test case for patch_v2_components

        Update a collection of components
        """
        unknown_base_type = bos.server.UNKNOWN_BASE_TYPE()
        headers = { 
        }
        response = self.client.open(
            '/apis/bos/v2/components',
            method='PATCH',
            headers=headers,
            data=json.dumps(unknown_base_type),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_put_v2_components(self):
        """Test case for put_v2_components

        Add or Replace a collection of components
        """
        v2_component_array = null
        headers = { 
        }
        response = self.client.open(
            '/apis/bos/v2/components',
            method='PUT',
            headers=headers,
            data=json.dumps(v2_component_array),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_save_v2_session_status(self):
        """Test case for save_v2_session_status

        Saves the current session to database
        """
        headers = { 
        }
        response = self.client.open(
            '/apis/bos/v2/sessions/{session_id}/status'.format(session_id='session_id_example'),
            method='POST',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
