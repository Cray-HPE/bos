# coding: utf-8

# Copyright 2019, 2021 Hewlett Packard Enterprise Development LP
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
import unittest
from unittest import mock

from bos.api.models.healthz import Healthz  # noqa: E501
from bos.api.models.problem_details import ProblemDetails  # noqa: E501
from bos.controllers.v1.healthz import v1_get_healthz


class TestHealthzController(unittest.TestCase):
    """HealthzController integration test stubs"""

    def test_v1_get_healthz(self):
        """Test case for v1_get_healthz

        Get API health
        """
        with mock.patch('bos.controllers.v1.healthz.BosEtcdClient') as mocked_class:
            mocked_class.return_value.__enter__.return_value.get.return_value = ('ok'.encode('utf-8'), 'metadata')  # noqa: E501
            healthz, response_code = v1_get_healthz()
            self.assertEqual(response_code, 200, "Response code tests as healthy")
            self.assertIsInstance(healthz, Healthz, "Proper response verified")

    def test_v1_get_healthz_unhealthy(self):
        """Test case for v1_get_healthz

        Get API health
        """
        with mock.patch('bos.controllers.v1.healthz.BosEtcdClient') as mocked_class:
            mocked_class.return_value.__enter__.return_value.get.return_value = ('so_sick'.encode('utf-8'), 'metadata')  # noqa: E501
            healthz, response_code = v1_get_healthz()
            self.assertEqual(response_code, 503, "Response code tests as unhealthy")
            self.assertIsInstance(healthz, Healthz, "Proper response verified")


if __name__ == '__main__':
    unittest.main()
