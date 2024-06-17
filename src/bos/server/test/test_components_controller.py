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
from bos.server.models.v2_component import V2Component  # noqa: E501
from bos.server.models.v2_component_array import V2ComponentArray  # noqa: E501
from bos.server.test import BaseTestCase


class TestComponentsController(BaseTestCase):
    """ComponentsController integration test stubs"""

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

    def test_get_v2_component(self):
        """Test case for get_v2_component

        Retrieve the state of a single component
        """
        headers = { 
        }
        response = self.client.open(
            '/apis/bos/v2/components/{component_id}'.format(component_id='component_id_example'),
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_v2_components(self):
        """Test case for get_v2_components

        Retrieve the state of a collection of components
        """
        query_string = [('ids', 'ids_example'),
                        ('session', 'session_example'),
                        ('staged_session', 'staged_session_example'),
                        ('enabled', True),
                        ('phase', 'phase_example'),
                        ('status', 'status_example')]
        headers = { 
        }
        response = self.client.open(
            '/apis/bos/v2/components',
            method='GET',
            headers=headers,
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_patch_v2_component(self):
        """Test case for patch_v2_component

        Update a single component
        """
        v2_component = {
  "event_stats" : {
    "power_off_forceful_attempts" : 1,
    "power_on_attempts" : 0,
    "power_off_graceful_attempts" : 6
  },
  "session" : "session",
  "actual_state" : {
    "last_updated" : "2019-07-28T03:26:00Z",
    "bss_token" : "bss_token",
    "boot_artifacts" : {
      "kernel" : "kernel",
      "kernel_parameters" : "kernel_parameters",
      "initrd" : "initrd"
    }
  },
  "desired_state" : {
    "last_updated" : "2019-07-28T03:26:00Z",
    "configuration" : "configuration",
    "bss_token" : "bss_token",
    "boot_artifacts" : {
      "kernel" : "kernel",
      "kernel_parameters" : "kernel_parameters",
      "initrd" : "initrd"
    }
  },
  "id" : "id",
  "last_action" : {
    "last_updated" : "2019-07-28T03:26:00Z",
    "action" : "action",
    "failed" : true
  },
  "retry_policy" : 1,
  "error" : "error",
  "enabled" : true,
  "staged_state" : {
    "last_updated" : "2019-07-28T03:26:00Z",
    "configuration" : "configuration",
    "session" : "session",
    "boot_artifacts" : {
      "kernel" : "kernel",
      "kernel_parameters" : "kernel_parameters",
      "initrd" : "initrd"
    }
  },
  "status" : {
    "phase" : "phase",
    "status_override" : "status_override",
    "status" : "status"
  }
}
        headers = { 
        }
        response = self.client.open(
            '/apis/bos/v2/components/{component_id}'.format(component_id='component_id_example'),
            method='PATCH',
            headers=headers,
            data=json.dumps(v2_component),
            content_type='application/json')
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

    def test_put_v2_component(self):
        """Test case for put_v2_component

        Add or Replace a single component
        """
        v2_component = {
  "event_stats" : {
    "power_off_forceful_attempts" : 1,
    "power_on_attempts" : 0,
    "power_off_graceful_attempts" : 6
  },
  "session" : "session",
  "actual_state" : {
    "last_updated" : "2019-07-28T03:26:00Z",
    "bss_token" : "bss_token",
    "boot_artifacts" : {
      "kernel" : "kernel",
      "kernel_parameters" : "kernel_parameters",
      "initrd" : "initrd"
    }
  },
  "desired_state" : {
    "last_updated" : "2019-07-28T03:26:00Z",
    "configuration" : "configuration",
    "bss_token" : "bss_token",
    "boot_artifacts" : {
      "kernel" : "kernel",
      "kernel_parameters" : "kernel_parameters",
      "initrd" : "initrd"
    }
  },
  "id" : "id",
  "last_action" : {
    "last_updated" : "2019-07-28T03:26:00Z",
    "action" : "action",
    "failed" : true
  },
  "retry_policy" : 1,
  "error" : "error",
  "enabled" : true,
  "staged_state" : {
    "last_updated" : "2019-07-28T03:26:00Z",
    "configuration" : "configuration",
    "session" : "session",
    "boot_artifacts" : {
      "kernel" : "kernel",
      "kernel_parameters" : "kernel_parameters",
      "initrd" : "initrd"
    }
  },
  "status" : {
    "phase" : "phase",
    "status_override" : "status_override",
    "status" : "status"
  }
}
        headers = { 
        }
        response = self.client.open(
            '/apis/bos/v2/components/{component_id}'.format(component_id='component_id_example'),
            method='PUT',
            headers=headers,
            data=json.dumps(v2_component),
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


if __name__ == '__main__':
    unittest.main()
