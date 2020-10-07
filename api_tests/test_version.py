# Version API test
# Copyright 2019, Cray Inc. All Rights Reserved.

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
