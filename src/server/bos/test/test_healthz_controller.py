# coding: utf-8

# Copyright 2019, Cray Inc. All Rights Reserved.

from __future__ import absolute_import
import unittest
from unittest import mock

from bos.models.healthz import Healthz  # noqa: E501
from bos.models.problem_details import ProblemDetails  # noqa: E501
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
