# Version API test
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

import pytest

from .lib import common


@pytest.mark.repogettests
@pytest.mark.smoke
def test_get_version():
    r = common.create_session().get(
        common.get_service_url('v1'))
    assert r.status_code == 200, \
        "expected 200 received {} with data\n{}".format(
            r.status_code, r.text)


def test_get_version_major_number():
    r = common.create_session().get(
        common.get_service_url('v1'))
    assert (r.status_code, int(r.json()['major'])) == (200, 1), \
        "expected (200 ,1) received ({},{})".format(r.status_code,
                                                    int(r.json()['major']))


def test_get_version_minor_number():
    r = common.create_session().get(
        common.get_service_url('v1'))
    assert (r.status_code, int(r.json()['minor'])) == (200, 0), \
        "expected (200 ,0) received ({},{})".format(r.status_code,
                                                    int(r.json()['minor']))


def test_get_version_patch_number():
    r = common.create_session().get(
        common.get_service_url('v1'))
    assert (r.status_code, int(r.json()['patch'])) == (200, 0), \
        "expected (200 ,0) received ({},{})".format(r.status_code,
                                                    int(r.json()['patch']))
