# Cray-provided base controllers for the Boot Orchestration Service
# Copyright 2019, Cray Inc. All Rights Reserved.

import etcd3
import logging

from bos.models.healthz import Healthz
from bos.dbclient import BosEtcdClient

LOGGER = logging.getLogger('bos.controllers.healthz')


def v1_get_healthz():
    """GET /v1/healthz

    Query BOS etcd for health status

    :rtype: Healthz
    """

    LOGGER.info('starting service healthz check')
    LOGGER.debug('in v1_get_healthz')

    # check etcd connectivity
    LOGGER.debug('checking etcd cluster access')
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
