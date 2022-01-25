# Copyright 2021-2022 Hewlett Packard Enterprise Development LP
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
import logging
from requests.exceptions import HTTPError, ConnectionError

from bos.operators.utils import requests_retry_session, PROTOCOL

SERVICE_NAME = 'cray-cfs-api'
BASE_ENDPOINT = "%s://%s/v2" % (PROTOCOL, SERVICE_NAME)
COMPONENTS_ENDPOINT = "%s/components" % BASE_ENDPOINT

LOGGER = logging.getLogger('bos.operators.utils.clients.cfs')

PATCH_BATCH_SIZE = 1000


def get_components(session=None, **kwargs):
    if not session:
        session = requests_retry_session()
    response = session.get(COMPONENTS_ENDPOINT, params=kwargs)
    try:
        response.raise_for_status()
    except HTTPError as err:
        LOGGER.error("Failed getting nodes from cfs: %s", err)
        raise
    return response.json()


def patch_components(data, session=None):
    if not session:
        session = requests_retry_session()
    response = session.patch(COMPONENTS_ENDPOINT, json=data)
    try:
        response.raise_for_status()
    except HTTPError as err:
        LOGGER.error("Failed asking CFS to configure nodes: %s", err)
        raise


def patch_desired_config(node_ids, desired_config, enabled=False, tags=None):
    session = requests_retry_session()
    data = []
    if not tags:
        tags = {}
    for node_id in node_ids:
        data.append({
            'id': node_id,
            'enabled': enabled,
            'desiredConfig': desired_config,
            'tags': tags
        })
        if len(data) >= PATCH_BATCH_SIZE:
            patch_components(data, session=session)
            data = []
    if data:
        patch_components(data, session=session)
