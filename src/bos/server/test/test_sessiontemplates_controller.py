# coding: utf-8

from __future__ import absolute_import
import unittest

from flask import json
from six import BytesIO

from bos.server.models.problem_details import ProblemDetails  # noqa: E501
from bos.server.models.v2_session_template import V2SessionTemplate  # noqa: E501
from bos.server.models.v2_session_template_array import V2SessionTemplateArray  # noqa: E501
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
