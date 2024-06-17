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

#from bos.server.models.healthz import Healthz  # noqa: E501
#from bos.server.models.one_of_v2_components_update_v2_component_array import OneOfV2ComponentsUpdateV2ComponentArray  # noqa: E501
#from bos.server.models.problem_details import ProblemDetails  # noqa: E501
#from bos.server.models.unknownbasetype import UNKNOWN_BASE_TYPE  # noqa: E501
#from bos.server.models.v2_apply_staged_components import V2ApplyStagedComponents  # noqa: E501
#from bos.server.models.v2_apply_staged_status import V2ApplyStagedStatus  # noqa: E501
#from bos.server.models.v2_component import V2Component  # noqa: E501
#from bos.server.models.v2_component_array import V2ComponentArray  # noqa: E501
#from bos.server.models.v2_options import V2Options  # noqa: E501
#from bos.server.models.v2_session import V2Session  # noqa: E501
#from bos.server.models.v2_session_array import V2SessionArray  # noqa: E501
#from bos.server.models.v2_session_create import V2SessionCreate  # noqa: E501
#from bos.server.models.v2_session_extended_status import V2SessionExtendedStatus  # noqa: E501
#from bos.server.models.v2_session_template import V2SessionTemplate  # noqa: E501
#from bos.server.models.v2_session_template_array import V2SessionTemplateArray  # noqa: E501
#from bos.server.models.version import Version  # noqa: E501
from bos.server.test import BaseTestCase


class TestV2Controller(BaseTestCase):
    """V2Controller integration test stubs"""

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

    def test_get_v2(self):
        """Test case for get_v2

        Get API version
        """
        headers = { 
        }
        response = self.client.open(
            '/apis/bos/v2',
            method='GET',
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

    def test_get_v2_healthz(self):
        """Test case for get_v2_healthz

        Get service health details
        """
        headers = { 
        }
        response = self.client.open(
            '/apis/bos/v2/healthz',
            method='GET',
            headers=headers)
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

    def test_get_version_v2(self):
        """Test case for get_version_v2

        Get API version
        """
        headers = { 
        }
        response = self.client.open(
            '/apis/bos/v2/version',
            method='GET',
            headers=headers)
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
