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

import sys
sys.path.append("..")

#from bos.server.models.problem_details import ProblemDetails  # noqa: E501
#from bos.server.models.v2_session_template import V2SessionTemplate  # noqa: E501
#from bos.server.models.v2_session_template_array import V2SessionTemplateArray  # noqa: E501
from bos.server.test import BaseTestCase


class TestSessiontemplatesController(BaseTestCase):
    """SessiontemplatesController integration test stubs"""

    def test_delete_v2_sessiontemplate(self):
        """Test case for delete_v2_sessiontemplate

        Delete a session template
        """
        headers = { 
        }
        response = self.client.open(
            '/apis/bos/v2/sessiontemplates/{session_template_id}'.format(session_template_id='session_template_id_example'),
            method='DELETE',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_v2_sessiontemplates(self):
        """Test case for get_v2_sessiontemplates

        List session templates
        """
        headers = { 
        }
        response = self.client.open(
            '/apis/bos/v2/sessiontemplates',
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_v2_sessiontemplatetemplate(self):
        """Test case for get_v2_sessiontemplatetemplate

        Get an example session template.
        """
        headers = { 
        }
        response = self.client.open(
            '/apis/bos/v2/sessiontemplatetemplate',
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_patch_v2_sessiontemplate(self):
        """Test case for patch_v2_sessiontemplate

        Update a session template
        """
        v2_session_template = {
  "cfs" : {
    "configuration" : "configuration"
  },
  "boot_sets" : {
    "key" : {
      "path" : "path",
      "cfs" : {
        "configuration" : "configuration"
      },
      "node_roles_groups" : [ "node_roles_groups", "node_roles_groups" ],
      "rootfs_provider" : "rootfs_provider",
      "name" : "name",
      "etag" : "etag",
      "kernel_parameters" : "kernel_parameters",
      "node_list" : [ "node_list", "node_list" ],
      "type" : "type",
      "rootfs_provider_passthrough" : "rootfs_provider_passthrough",
      "node_groups" : [ "node_groups", "node_groups" ]
    }
  },
  "name" : "cle-1.0.0",
  "description" : "description",
  "enable_cfs" : true,
  "links" : [ {
    "rel" : "rel",
    "href" : "href"
  }, {
    "rel" : "rel",
    "href" : "href"
  } ]
}
        headers = { 
        }
        response = self.client.open(
            '/apis/bos/v2/sessiontemplates/{session_template_id}'.format(session_template_id='session_template_id_example'),
            method='PATCH',
            headers=headers,
            data=json.dumps(v2_session_template),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_put_v2_sessiontemplate(self):
        """Test case for put_v2_sessiontemplate

        Create session template
        """
        v2_session_template = {
  "cfs" : {
    "configuration" : "configuration"
  },
  "boot_sets" : {
    "key" : {
      "path" : "path",
      "cfs" : {
        "configuration" : "configuration"
      },
      "node_roles_groups" : [ "node_roles_groups", "node_roles_groups" ],
      "rootfs_provider" : "rootfs_provider",
      "name" : "name",
      "etag" : "etag",
      "kernel_parameters" : "kernel_parameters",
      "node_list" : [ "node_list", "node_list" ],
      "type" : "type",
      "rootfs_provider_passthrough" : "rootfs_provider_passthrough",
      "node_groups" : [ "node_groups", "node_groups" ]
    }
  },
  "name" : "cle-1.0.0",
  "description" : "description",
  "enable_cfs" : true,
  "links" : [ {
    "rel" : "rel",
    "href" : "href"
  }, {
    "rel" : "rel",
    "href" : "href"
  } ]
}
        headers = { 
        }
        response = self.client.open(
            '/apis/bos/v2/sessiontemplates/{session_template_id}'.format(session_template_id='session_template_id_example'),
            method='PUT',
            headers=headers,
            data=json.dumps(v2_session_template),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
