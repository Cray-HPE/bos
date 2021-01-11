# coding: utf-8
# Copyright 2019, Cray Inc.  All Rights Reserved.

from __future__ import absolute_import

from flask import json
from six import BytesIO

from bos.models.problem_details import ProblemDetails  # noqa: E501
from bos.models.version import Version  # noqa: E501
from bos.test import BaseTestCase
from bos.controllers.base import root_get

from nose.tools import nottest


class TestVersionController(BaseTestCase):
    """VersionController integration test stubs"""

    @nottest
    def test_get_version(self):
        """Test case for get_version

        API version
        """
        response = self.client.open(
            '/apis/bos/v1',
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    @nottest
    def test_get_versions(self):
        """Test case for get_versions

        API versions
        """
        response = self.client.open(
            '/apis/bos/',
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()
