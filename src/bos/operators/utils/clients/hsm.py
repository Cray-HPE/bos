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
import json
import logging
import os
from collections import defaultdict
from requests.exceptions import HTTPError, ConnectionError
from urllib3.exceptions import MaxRetryError

from bos.common.utils import requests_retry_session, PROTOCOL

SERVICE_NAME = 'cray-smd'
BASE_ENDPOINT = "%s://%s/hsm/v2/" % (PROTOCOL, SERVICE_NAME)
ENDPOINT = os.path.join(BASE_ENDPOINT, 'State/Components/Query')
VERIFY = True

LOGGER = logging.getLogger('bos.operators.utils.clients.hsm')


class HWStateManagerException(Exception):
    """
    An error unique to interacting with the HWStateManager service;
    should the service be unable to fulfill a given request (timeout,
    no components, service 503s, etc.); this exception is raised. It is
    intended to be further subclassed for more specific kinds of errors
    in the future should they arise.
    """


def read_all_node_xnames():
    """
    Queries HSM for the full set of xname components that
    have been discovered; return these as a set.
    """
    session = requests_retry_session()
    endpoint = '%s/State/Components/' % (BASE_ENDPOINT)
    LOGGER.debug("GET %s", endpoint)
    try:
        response = session.get(endpoint)
    except ConnectionError as ce:
        LOGGER.error("Unable to contact HSM service: %s", ce)
        raise HWStateManagerException(ce) from ce
    LOGGER.debug("Response status code=%d, reason=%s, body=%s", response.status_code,
                 response.reason, response.text)
    try:
        response.raise_for_status()
    except (HTTPError, MaxRetryError) as hpe:
        LOGGER.error("Unexpected response from HSM: %s", response)
        raise HWStateManagerException(hpe) from hpe
    try:
        json_body = json.loads(response.text)
    except json.JSONDecodeError as jde:
        LOGGER.error("Non-JSON response from HSM: %s", response.text)
        raise HWStateManagerException(jde) from jde
    try:
        return set([component['ID'] for component in json_body['Components']
                    if component.get('Type', None) == 'Node'])
    except KeyError as ke:
        LOGGER.error("Unexpected API response from HSM")
        raise HWStateManagerException(ke) from ke


def get_components(node_list, enabled=None) -> dict[str,list[dict]]:
    """
    Get information for all list components HSM

    :return the HSM components
    :rtype Dictionary containing a 'Components' key whose value is a list
    containing each component, where each component is itself represented by a
    dictionary.

    Here is an example of the returned values.
    {
    "Components": [
        {
        "ID": "x3000c0s19b1n0",
        "Type": "Node",
        "State": "Ready",
        "Flag": "OK",
        "Enabled": true,
        "Role": "Compute",
        "NID": 1,
        "NetType": "Sling",
        "Arch": "X86",
        "Class": "River"
        },
        {
        "ID": "x3000c0s19b2n0",
        "Type": "Node",
        "State": "Ready",
        "Flag": "OK",
        "Enabled": true,
        "Role": "Compute",
        "NID": 1,
        "NetType": "Sling",
        "Arch": "X86",
        "Class": "River"
        }
    ]
    }
    """
    if not node_list:
        LOGGER.warning("hsm.get_components called with empty node list")
        return {'Components': []}
    session = requests_retry_session()
    try:
        payload = {'ComponentIDs': node_list}
        if enabled is not None:
            payload['enabled'] = [str(enabled)]
        LOGGER.debug("POST %s with body=%s", ENDPOINT, payload)
        response = session.post(ENDPOINT, json=payload)
        LOGGER.debug("Response status code=%d, reason=%s, body=%s", response.status_code,
                     response.reason, response.text)
        response.raise_for_status()
        components = json.loads(response.text)
    except (ConnectionError, MaxRetryError) as e:
        LOGGER.error("Unable to connect to HSM: {}".format(e))
        raise e
    except HTTPError as e:
        LOGGER.error("Unexpected response from HSM: {}".format(e))
        raise e
    except json.JSONDecodeError as e:
        LOGGER.error("Non-JSON response from HSM: {}".format(e))
        raise e
    return components


class Inventory(object):
    """
    Inventory handles the generation of a hardware inventory in a similar manner to how the
    dynamic inventory is generated for CFS.  To reduce the number of calls to HSM, everything is
    cached for repeated checks, stored both as overall inventory and separate group types to allow
    use in finding BOA's base list of nodes, and lazily loaded to prevent extra calls when no limit
    is used.
    """

    def __init__(self, partition=None):
        self._partition = partition  # Can be specified to limit to roles/components query
        self._inventory = None
        self._groups = None
        self._partitions = None
        self._roles = None
        self._session = None

    @property
    def groups(self):
        if self._groups is None:
            data = self.get('groups')
            groups = {}
            for group in data:
                groups[group['label']] = set(group.get('members', {}).get('ids', []))
            self._groups = groups
        return self._groups

    @property
    def partitions(self):
        if self._partitions is None:
            data = self.get('partitions')
            partitions = {}
            for partition in data:
                partitions[partition['name']] = set(partition.get('members', {}).get('ids', []))
            self._partitions = partitions
        return self._partitions

    @property
    def roles(self):
        if self._roles is None:
            params = {}
            if self._partition:
                params['partition'] = self._partition
            data = self.get('State/Components', params=params)
            roles = defaultdict(set)
            for component in data['Components']:
                role=''
                if 'Role' in component:
                    role = str(component['Role'])
                    roles[role].add(component['ID'])
                if 'SubRole' in component:
                    subrole = role + '_' + str(component['SubRole'])
                    roles[subrole].add(component['ID'])
            self._roles = roles
        return self._roles

    @property
    def inventory(self):
        if self._inventory is None:
            inventory = {}
            inventory.update(self.groups)
            inventory.update(self.partitions)
            inventory.update(self.roles)
            self._inventory = inventory
            LOGGER.info(self._inventory)
        return self._inventory

    def __contains__(self, key):
        return key in self.inventory

    def __getitem__(self, key):
        return self.inventory[key]

    def get(self, path, params=None):
        url = os.path.join(BASE_ENDPOINT, path)
        if self._session is None:
            self._session = requests_retry_session()
        try:
            LOGGER.debug("HSM Inventory: GET %s with params=%s", url, params)
            response = self._session.get(url, params=params, verify=VERIFY)
            LOGGER.debug("Response status code=%d, reason=%s, body=%s", response.status_code,
                         response.reason, response.text)
            response.raise_for_status()
        except HTTPError as err:
            LOGGER.error("Failed to get '{}': {}".format(url, err))
            raise
        try:
            return response.json()
        except ValueError:
            LOGGER.error("Couldn't parse a JSON response: {}".format(response.text))
            raise
