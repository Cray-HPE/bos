#
# MIT License
#
# (C) Copyright 2021-2024 Hewlett Packard Enterprise Development LP
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
from collections import defaultdict
import logging
from requests.exceptions import HTTPError, ConnectionError

from bos.common.utils import requests_retry_session, PROTOCOL

SERVICE_NAME = 'cray-cfs-api'
BASE_ENDPOINT = "%s://%s/v2" % (PROTOCOL, SERVICE_NAME)
COMPONENTS_ENDPOINT = "%s/components" % BASE_ENDPOINT

LOGGER = logging.getLogger('bos.operators.utils.clients.cfs')

GET_BATCH_SIZE = 200
PATCH_BATCH_SIZE = 1000


def get_components(session=None, **kwargs):
    if not session:
        session = requests_retry_session()
    LOGGER.debug("GET %s with params=%s", COMPONENTS_ENDPOINT, kwargs)
    response = session.get(COMPONENTS_ENDPOINT, params=kwargs)
    LOGGER.debug("Response status code=%d, reason=%s, body=%s", response.status_code,
                 response.reason, response.text)
    try:
        response.raise_for_status()
    except HTTPError as err:
        LOGGER.error("Failed getting nodes from cfs: %s", err)
        raise
    component_list = response.json()
    LOGGER.debug("Returning %d components from CFS", len(component_list))
    return component_list


def patch_components(data, session=None):
    if not data:
        LOGGER.warning("patch_components called without data; returning without action.")
        return
    if not session:
        session = requests_retry_session()
    LOGGER.debug("PATCH %s with body=%s", COMPONENTS_ENDPOINT, data)
    response = session.patch(COMPONENTS_ENDPOINT, json=data)
    LOGGER.debug("Response status code=%d, reason=%s, body=%s", response.status_code,
                 response.reason, response.text)
    try:
        response.raise_for_status()
    except HTTPError as err:
        LOGGER.error("Failed asking CFS to configure nodes: %s", err)
        raise


def get_components_from_id_list(id_list):
    if not id_list:
        LOGGER.warning("get_components_from_id_list called without IDs; returning without action.")
        return []
    LOGGER.debug("get_components_from_id_list called with %d IDs", len(id_list))
    session = requests_retry_session()
    component_list = []
    while id_list:
        next_batch = id_list[:GET_BATCH_SIZE]
        next_comps = get_components(session=session, ids=','.join(next_batch))
        component_list.extend(next_comps)
        id_list = id_list[GET_BATCH_SIZE:]
    LOGGER.debug("get_components_from_id_list returning a total of %d components from CFS",
                 len(component_list))
    return component_list


def patch_desired_config(node_ids, desired_config, enabled=False, tags=None, clear_state=False):
    if not node_ids:
        LOGGER.warning("patch_desired_config called without IDs; returning without action.")
        return
    LOGGER.debug("patch_desired_config called on %d IDs with desired_config=%s enabled=%s tags=%s"
                 " clear_state=%s", len(node_ids), desired_config, enabled, tags, clear_state)
    session = requests_retry_session()
    node_patch = {
        'enabled': enabled,
        'desiredConfig': desired_config,
        'tags': tags if tags else {}
    }
    data={ "patch": node_patch, "filters": {} }
    if clear_state:
        node_patch['state'] = []
    while node_ids:
        data["filters"]["ids"] = ','.join(node_ids[:PATCH_BATCH_SIZE])
        patch_components(data=data, session=session)
        node_ids = node_ids[PATCH_BATCH_SIZE:]


def set_cfs(components, enabled, clear_state=False):
    if not components:
        LOGGER.warning("set_cfs called without components; returning without action.")
        return
    LOGGER.debug("set_cfs called on %d components with enabled=%s clear_state=%s", len(components),
                 enabled, clear_state)
    configurations = defaultdict(list)
    for component in components:
        config_name = component.get('desired_state', {}).get('configuration', '')
        bos_session = component.get('session')
        key = (config_name, bos_session)
        configurations[key].append(component['id'])
    for key, ids in configurations.items():
        config_name, bos_session = key
        patch_desired_config(ids, config_name, enabled=enabled,
                             tags={'bos_session': bos_session}, clear_state=clear_state)
