# Copyright 2021 Hewlett Packard Enterprise Development LP
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
import json
import logging
import os
from collections import defaultdict
from requests.exceptions import HTTPError, ConnectionError
from urllib3.exceptions import MaxRetryError

from bos.operators.utils import requests_retry_session, PROTOCOL

SERVICE_NAME = 'cray-smd'
BASE_ENDPOINT = "%s://%s/hsm/v2/" % (PROTOCOL, SERVICE_NAME)
ENDPOINT = os.path.join(BASE_ENDPOINT, 'State/Components/Query')
VERIFY = True

LOGGER = logging.getLogger('bos.operators.utils.clients.hsm')


def get_components(node_list, enabled=None):
    """Get information for all list components HSM"""
    session = requests_retry_session()
    try:
        payload = {'ComponentIDs': node_list}
        if enabled is not None:
            payload['enabled'] = [str(enabled)]
        response = session.post(ENDPOINT, json=payload)
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
                if 'Role' in component:
                    roles[component['Role']].add(component['ID'])
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
            response = self._session.get(url, params=params, verify=VERIFY)
            response.raise_for_status()
        except HTTPError as err:
            LOGGER.error("Failed to get '{}': {}".format(url, err))
            raise
        try:
            return response.json()
        except ValueError:
            LOGGER.error("Couldn't parse a JSON response: {}".format(response.text))
            raise
