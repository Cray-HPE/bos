#
# MIT License
#
# (C) Copyright 2019, 2021-2022 Hewlett Packard Enterprise Development LP
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
from bos.server.controllers.v1.session import get_v1_session, get_v1_sessions, delete_v1_session
from bos.server.controllers.v1.session import _get_boa_naming_for_session

from unittest import mock
import testtools
import unittest


class TestSessionController(testtools.TestCase):
    """SessionController integration test stubs"""

    def test_get_v1_session(self):
        with mock.patch('bos.server.controllers.v1.session.BosEtcdClient') as mocked_class:
            session_name = 'foo'
            db_response = [(session_name.encode('utf-8'), mock.MagicMock())]
            db_response[0][1].key.return_value = '//%s' % (session_name).encode('utf-8')
            mocked_class.return_value.__enter__.return_value.get_prefix.return_value = db_response
            result, status = get_v1_session(session_name)

            # Check the expected result and status.
            self.assertEqual(db_response[0][0].decode('utf-8'), list(result.values())[0])
            self.assertEqual(200, status)
            self.assertTrue(list(result.values())[0] == 'foo', "Results is the name of the session created.")

    def test_get_v1_session_not_found(self):
        """Test case for get_v1_session

        Check for the expected handling when the session is not found.
        """
        with mock.patch('bos.server.controllers.v1.session.BosEtcdClient') as mocked_class:
            session_name = 'foo'
            db_response = []
            mocked_class.return_value.__enter__.return_value.get_prefix.return_value = db_response
            result, status = get_v1_session(session_name)

            # Check the expected result and status.
            self.assertEqual(404, status)
            self.assertEqual(result, {}, "Nothing returned when not found.")

    def test_get_v1_sessions(self):
        """Test case for get_v1_sessions

        List Sessions
        """
        with mock.patch('bos.server.controllers.v1.session.BosEtcdClient') as mocked_class:
            db_responses = []
            for session_name in 'abcdefg':
                db_responses.append((session_name.encode('utf-8'), mock.MagicMock()))
                db_responses[-1][1].key.return_value = '//%s' % (session_name).encode('utf-8')
            mocked_class.return_value.__enter__.return_value.get_prefix.return_value = db_responses
            result, status = get_v1_sessions()
            self.assertEqual(len(result), len(db_responses))
            self.assertEqual(200, status)
            mocked_class.return_value.__enter__.return_value.get_prefix.assert_called_once()

    def test_get_v1_sessions_none(self):
        """Test case for get_v1_sessions

        List Sessions
        """
        with mock.patch('bos.server.controllers.v1.session.BosEtcdClient') as mocked_class:
            db_responses = []
            for session_name in '':
                db_responses.append((session_name.encode('utf-8'), mock.MagicMock()))
                db_responses[-1][1].key.return_value = '//%s' % (session_name).encode('utf-8')
            mocked_class.return_value.__enter__.return_value.get_prefix.return_value = db_responses
            result, status = get_v1_sessions()
            self.assertEqual(len(result), len(db_responses))
            self.assertEqual(200, status)
            mocked_class.return_value.__enter__.return_value.get_prefix.assert_called_once()

    def test_delete_v1_session(self):
        """Test case for delete_v1_sessiontemplate

        Delete Session
        """
        with mock.patch('bos.server.controllers.v1.session.BosEtcdClient') as mocked_class:
            mocked_class.return_value.__enter__.return_value.delete_prefix.return_value.deleted = 1
            result, status = delete_v1_session('test')
            self.assertEqual('', result)
            self.assertEqual(status, 204)

    def test_delete_v1_session_not_found(self):
        """Test case for delete_v1_sessiontemplate

        Delete a Session that does not exist
        """
        with mock.patch('bos.server.controllers.v1.session.BosEtcdClient') as mocked_class:
            mocked_class.return_value.__enter__.return_value.delete_prefix.return_value.deleted = 0
            result, status = delete_v1_session('test')
            self.assertEqual(status, 404)
            self.assertTrue('not found' in result)

    def test_boa_naming(self):
        # Check length and prefix on the session ID and BOA job name.
        session_id, boa_name = _get_boa_naming_for_session()
        self.assertTrue(len(session_id) <= 63)
        self.assertTrue(boa_name.startswith('boa-'))
        self.assertTrue(len(boa_name) <= 63)


if __name__ == '__main__':
    unittest.main()
