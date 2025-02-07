#
# MIT License
#
# (C) Copyright 2021-2022, 2024-2025 Hewlett Packard Enterprise Development LP
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
import logging
from typing import Literal

from bos.common.utils import exc_type_msg
from bos.server.models.healthz import Healthz
from bos.server import redis_db_utils

DB = redis_db_utils.get_wrapper(db='options')

LOGGER = logging.getLogger(__name__)


def _get_db_status() -> str:
    available = False
    try:
        if DB.info():
            available = True
    except Exception as e:
        LOGGER.error(exc_type_msg(e))

    if available:
        return 'ok'
    return 'not_available'


def get_v2_healthz() -> tuple[Healthz, Literal[200]]:
    """GET /v2/healthz

    Query BOS etcd for health status

    :rtype: Healthz
    """
    LOGGER.debug("GET /v2/healthz invoked get_v2_healthz")
    return Healthz(
        db_status=_get_db_status(),
        api_status='ok',
    ), 200
