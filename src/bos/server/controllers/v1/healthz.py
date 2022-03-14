#
# MIT License
#
# (C) Copyright 2019-2022 Hewlett Packard Enterprise Development LP
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
# Cray-provided base controllers for the Boot Orchestration Service

import etcd3
import logging

from bos.server.models.healthz import Healthz as Healthz
from bos.server.dbclient import BosEtcdClient

LOGGER = logging.getLogger('bos.server.controllers.v1.healthz')


def v1_get_healthz():
    """GET /v1/healthz

    Query BOS etcd for health status

    :rtype: Healthz
    """
    # check etcd connectivity
    with BosEtcdClient() as bec:
        bec.put('health', 'ok')
        value, _ = bec.get('health')
        if value.decode('utf-8') != 'ok':
            return Healthz(etcd_status='Failed to read from cluster',
                           api_status='Not Ready'), 503
    return Healthz(
        etcd_status='ok',
        api_status='ok',
    ), 200
