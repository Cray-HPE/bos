# coding: utf-8

from __future__ import absolute_import
import unittest

from flask import json
from six import BytesIO

from bos.server.models.problem_details import ProblemDetails  # noqa: E501
from bos.server.models.v2_apply_staged_components import V2ApplyStagedComponents  # noqa: E501
from bos.server.models.v2_apply_staged_status import V2ApplyStagedStatus  # noqa: E501
from bos.server.test import BaseTestCase


class TestApplystagedController(BaseTestCase):
    """ApplystagedController integration test stubs"""

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


if __name__ == '__main__':
    unittest.main()
