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
from bos.server.models.v2_session import V2Session  # noqa: E501
from bos.server.models.v2_session_array import V2SessionArray  # noqa: E501
from bos.server.models.v2_session_create import V2SessionCreate  # noqa: E501
from bos.server.models.v2_session_extended_status import V2SessionExtendedStatus  # noqa: E501
from bos.server.test import BaseTestCase


class TestSessionsController(BaseTestCase):
    """SessionsController integration test stubs"""

    def test_delete_v2_session(self):
        """Test case for delete_v2_session

        Delete session by id
        """
        headers = { 
        }
        response = self.client.open(
            '/apis/bos/v2/sessions/{session_id}'.format(session_id='session_id_example'),
            method='DELETE',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_delete_v2_sessions(self):
        """Test case for delete_v2_sessions

        Delete multiple sessions.
        """
        query_string = [('min_age', 'min_age_example'),
                        ('max_age', 'max_age_example'),
                        ('status', 'status_example')]
        headers = { 
        }
        response = self.client.open(
            '/apis/bos/v2/sessions',
            method='DELETE',
            headers=headers,
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_v2_session(self):
        """Test case for get_v2_session

        Get session details by id
        """
        headers = { 
        }
        response = self.client.open(
            '/apis/bos/v2/sessions/{session_id}'.format(session_id='session_id_example'),
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_v2_session_status(self):
        """Test case for get_v2_session_status

        Get session extended status information by id
        """
        headers = { 
        }
        response = self.client.open(
            '/apis/bos/v2/sessions/{session_id}/status'.format(session_id='session_id_example'),
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_v2_sessions(self):
        """Test case for get_v2_sessions

        List sessions
        """
        query_string = [('min_age', 'min_age_example'),
                        ('max_age', 'max_age_example'),
                        ('status', 'status_example')]
        headers = { 
        }
        response = self.client.open(
            '/apis/bos/v2/sessions',
            method='GET',
            headers=headers,
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_patch_v2_session(self):
        """Test case for patch_v2_session

        Update a single session
        """
        v2_session = {
  "include_disabled" : true,
  "template_name" : "my-session-template",
  "components" : "components",
  "stage" : true,
  "name" : "name",
  "limit" : "limit",
  "operation" : "boot",
  "status" : {
    "start_time" : "start_time",
    "end_time" : "end_time",
    "error" : "error",
    "status" : "pending"
  }
}
        headers = { 
        }
        response = self.client.open(
            '/apis/bos/v2/sessions/{session_id}'.format(session_id='session_id_example'),
            method='PATCH',
            headers=headers,
            data=json.dumps(v2_session),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_post_v2_session(self):
        """Test case for post_v2_session

        Create a session
        """
        v2_session_create = {
  "include_disabled" : false,
  "template_name" : "my-session-template",
  "stage" : false,
  "name" : "session-20190728032600",
  "limit" : "limit",
  "operation" : "boot"
}
        headers = { 
        }
        response = self.client.open(
            '/apis/bos/v2/sessions',
            method='POST',
            headers=headers,
            data=json.dumps(v2_session_create),
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
