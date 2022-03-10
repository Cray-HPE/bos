# coding: utf-8
# Copyright 2019-2021 Hewlett Packard Enterprise Development LP
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
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# (MIT License)

from __future__ import absolute_import

from bos.server.controllers.v1.sessiontemplate import create_v1_sessiontemplate
from bos.server.controllers.v1.sessiontemplate import get_v1_sessiontemplate
from bos.server.controllers.v1.sessiontemplate import get_v1_sessiontemplates
from bos.server.controllers.v1.sessiontemplate import get_v1_sessiontemplatetemplate
from bos.server.controllers.v1.sessiontemplate import delete_v1_sessiontemplate

import connexion
import testtools
from unittest import mock
from connexion import problem
from connexion.lifecycle import ConnexionResponse


class TestSessiontemplateController(testtools.TestCase):
    """SessiontemplateController unit tests"""
    def test_create_v1_sessiontemplate(self):
        """Test case for create_v1_sessiontemplate

        Create a Session Template
        """
        with mock.patch('bos.server.controllers.v1.sessiontemplate.BosEtcdClient') as mocked_class:
            # with Flask(__name__).test_request_context():
            # Generate mocked request data that would normally come from
            # the http request.
            sample_template_create_req_data = {
                'name': 'foo',
            }
            with connexion.FlaskApp(__name__).app.test_request_context(json=sample_template_create_req_data):
                response, status_code = create_v1_sessiontemplate()
                mocked_class.return_value.__enter__.return_value.put.assert_called_once()
                self.assertEqual(status_code, 201)
                self.assertEqual(response.split('/')[2], sample_template_create_req_data['name'])

    def test_create_v1_sessiontemplate_with_data(self):
        """Test case for create_v1_sessiontemplate

        Create a Session Template with actual data
        Verify that the data returned is accurate
        """
        with mock.patch('bos.server.controllers.v1.sessiontemplate.BosEtcdClient') as mocked_class:
            # Generate mocked request data that would normally come from
            # the http request.
            sample_template_create_req_data = {
                "name": "bos-test",
                "boot_sets": {
                    "computes": {
                        "boot_ordinal": 1,
                        "ims_image_id": "88769f0a-f8fa-4253-846a-773c07e7e51f",
                        "kernel_parameters": "console=tty0 console=ttyS0,115200n8 selinux=0 rd.shell "
                                             "rd.net.timeout.carrier=40 rd.retry=40 ip=dhcp rd.neednet=1 "
                                             "crashkernel=256M "
                                             "htburl=https://10.2.100.50/apis/hbtd/hmi/v1/heartbeat k8s_gw=10.2.100.50",  # noqa: 501
                        "network": "nmn",
                        "node_list": [
                            "x0c0s0b0n0"
                        ],
                        "rootfs_provider": "ars",
                        "rootfs_provider_passthrough": ""
                    }
                },
                "cfs_branch": "master",
                "cfs_url": "https://api-gw-service-nmn.local/vcs/cray/config-management.git",
                "description": "Template for booting compute nodes, generated by the installation",
                "enable_cfs": True,
                "partition": "NA"
            }
            with connexion.FlaskApp(__name__).app.test_request_context(json=sample_template_create_req_data):
                # Call the controller method simulating a request
                response, status_code = create_v1_sessiontemplate()

                mocked_class.return_value.__enter__.return_value.put.assert_called_once()
                self.assertEqual(status_code, 201)
                self.assertEqual(response.split('/')[2], sample_template_create_req_data['name'])

    def test_get_v1_sessiontemplate_exists(self):
        """Test case for get_v1_sessiontemplate

        Get details for an existing session template
        """
        with mock.patch('bos.server.controllers.v1.sessiontemplate.BosEtcdClient') as mocked_class:
            db_response = '{"name": "test"}'.encode('utf-8'), None
            mocked_class.return_value.__enter__.return_value.get.return_value = db_response
            result, status = get_v1_sessiontemplate('test')
            self.assertEqual(200, status)
            self.assertEqual(result, {'name': 'test'})

    def test_get_v1_sessiontemplate_not_found(self):
        """Test case for get_v1_sessiontemplate

        Attempt to get details for a session template that does not exist
        """
        with mock.patch('bos.server.controllers.v1.sessiontemplate.BosEtcdClient') as mocked_class:
            db_response = ''.encode('utf-8'), None
            mocked_class.return_value.__enter__.return_value.get.return_value = db_response
            result = get_v1_sessiontemplate('test')
            self.assertIsInstance(result, ConnexionResponse, "Must return a 404 response.")
            self.assertEqual(result.status_code, 404)

    def test_get_v1_sessiontemplates(self):
        """Test case for get_v1_sessiontemplates

        List Session Templates
        """
        with mock.patch('bos.server.controllers.v1.sessiontemplate.BosEtcdClient') as mocked_class:
            db_response = []
            for st in 'abcd':
                json_string = '{"name": "st_%s", "boot_sets": {"set1": []}}' % (st)
                db_response.append((json_string.encode('utf-8'),
                                   'bogus_meta'))
            mocked_class.return_value.__enter__.return_value.get_prefix.return_value = db_response
            result, status = get_v1_sessiontemplates()
            self.assertEqual(200, status)
            self.assertEqual(len(result), 4)

    def test_get_v1_sessiontemplates_none_found(self):
        """Test case for get_v1_sessiontemplates

        List Session Templates
        """
        with mock.patch('bos.server.controllers.v1.sessiontemplate.BosEtcdClient') as mocked_class:
            db_response = []
            for st in '':
                json_string = '{"name": "st_%s", "boot_sets": {"set1": []}}' % (st)
                db_response.append((json_string.encode('utf-8'),
                                   'bogus_meta'))
            mocked_class.return_value.__enter__.return_value.get_prefix.return_value = db_response
            result, status = get_v1_sessiontemplates()
            self.assertEqual(200, status)
            self.assertEqual(len(result), 0)

    def test_delete_v1_sessiontemplate(self):
        """Test case for delete_v1_sessiontemplate

        Delete Session Template
        """
        template_to_delete = 'foo'
        with mock.patch('bos.server.controllers.v1.sessiontemplate.get_v1_sessiontemplate') as mocked_st_func:
            mocked_st_func.return_value = ({"name": template_to_delete, "boot_sets": {"set1": []}}, 200)
            with mock.patch('bos.server.controllers.v1.sessiontemplate.BosEtcdClient') as mocked_class:
                mocked_class.return_value.__enter__.return_value.delete.return_value = None
                _, status = delete_v1_sessiontemplate(template_to_delete)
                mocked_class.return_value.__enter__.return_value.delete.assert_called_once()
                self.assertEqual(status, 204)

    def test_delete_v1_sessiontemplate_not_found(self):
        """Test case for delete_v1_sessiontemplate

        Delete Session Template
        """
        template_to_delete = 'foo'
        with mock.patch('bos.server.controllers.v1.sessiontemplate.get_v1_sessiontemplate') as mocked_st_func:
            mocked_st_func.return_value = problem(404, 'oops', 'more oops')
            with mock.patch('bos.server.controllers.v1.sessiontemplate.BosEtcdClient') as mocked_class:
                status = delete_v1_sessiontemplate(template_to_delete)
                mocked_class.return_value.__enter__.return_value.delete.assert_not_called()
                self.assertEqual(status.status_code, 404)
                mocked_st_func.assert_called_once()

    def test_get_v1_sessiontemplatetemplate(self):
        """Test case for get_v1_sessiontemplatetemplate

        Get the example Session Template
        """
        result, status = get_v1_sessiontemplatetemplate()
        self.assertEqual(200, status)
        self.assertEqual(result["name"], 'name-your-template')


if __name__ == '__main__':
    import unittest
    unittest.main()
