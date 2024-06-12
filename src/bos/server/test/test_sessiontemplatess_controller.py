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
