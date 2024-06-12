# coding: utf-8

from __future__ import absolute_import
import unittest

from flask import json
from six import BytesIO

from bos.server.models.problem_details import ProblemDetails  # noqa: E501
from bos.server.models.v2_options import V2Options  # noqa: E501
from bos.server.test import BaseTestCase


class TestOptionsController(BaseTestCase):
    """OptionsController integration test stubs"""

    def test_get_v2_options(self):
        """Test case for get_v2_options

        Retrieve the BOS service options
        """
        headers = { 
        }
        response = self.client.open(
            '/apis/bos/v2/options',
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_patch_v2_options(self):
        """Test case for patch_v2_options

        Update BOS service options
        """
        v2_options = {
  "clear_stage" : true,
  "component_actual_state_ttl" : "component_actual_state_ttl",
  "disable_components_on_completion" : true,
  "cleanup_completed_session_ttl" : "cleanup_completed_session_ttl",
  "logging_level" : "logging_level",
  "max_power_on_wait_time" : 1,
  "max_power_off_wait_time" : 5,
  "max_boot_wait_time" : 6,
  "polling_frequency" : 5,
  "default_retry_policy" : 1,
  "discovery_frequency" : 0
}
        headers = { 
        }
        response = self.client.open(
            '/apis/bos/v2/options',
            method='PATCH',
            headers=headers,
            data=json.dumps(v2_options),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
