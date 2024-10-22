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
from typing import overload, Literal, Optional, Required, TypedDict

from collections import defaultdict
from requests import HTTPError, ConnectionError
from requests import Session as RequestsSession
from urllib3.exceptions import MaxRetryError

from bos.common.types import JsonData, JsonDict
from bos.common.utils import compact_response_text, exc_type_msg, requests_retry_session, PROTOCOL

SERVICE_NAME = 'cray-smd'
BASE_ENDPOINT = f"{PROTOCOL}://{SERVICE_NAME}/hsm/v2/"
ENDPOINT = os.path.join(BASE_ENDPOINT, 'State/Components/Query')
VERIFY = True

LOGGER = logging.getLogger('bos.operators.utils.clients.hsm')


HsmComponentArch = Literal['ARM', 'Other', 'X86']


class HsmComponent(TypedDict, total=False):
    """
    We only list the fields that we care about here, since this is purely
    going to be used for type checking
    """
    Enabled: bool
    ID: Required[str]
    Role: str
    SubRole: str
    State: str
    Type: str
    Arch: HsmComponentArch


class HsmGroupMembers(TypedDict, total=False):
    """
    We only list the fields that we care about here, since this is purely
    going to be used for type checking
    """
    ids: list[str]


class HsmGroup(TypedDict, total=False):
    """
    We only list the fields that we care about here, since this is purely
    going to be used for type checking
    """
    label: Required[str]
    members: HsmGroupMembers


class HsmComponentsResponse(TypedDict):
    """
    Dictionary containing a 'Components' key whose value is a list
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
    Components: list[HsmComponent]


class HWStateManagerException(Exception):
    """
    An error unique to interacting with the HWStateManager service;
    should the service be unable to fulfill a given request (timeout,
    no components, service 503s, etc.); this exception is raised. It is
    intended to be further subclassed for more specific kinds of errors
    in the future should they arise.
    """


def read_all_node_xnames() -> set[str]:
    """
    Queries HSM for the full set of xname components that
    have been discovered; return these as a set.
    """
    session = requests_retry_session()
    endpoint = f'{BASE_ENDPOINT}/State/Components/'
    LOGGER.debug("GET %s", endpoint)
    try:
        response = session.get(endpoint)
    except ConnectionError as ce:
        LOGGER.error("Unable to contact HSM service: %s", exc_type_msg(ce))
        raise HWStateManagerException(ce) from ce
    LOGGER.debug("Response status code=%d, reason=%s, body=%s", response.status_code,
                 response.reason, compact_response_text(response.text))
    try:
        response.raise_for_status()
    except (HTTPError, MaxRetryError) as hpe:
        LOGGER.error("Unexpected response from HSM: %s (%s)", response, exc_type_msg(hpe))
        raise HWStateManagerException(hpe) from hpe
    try:
        json_body = json.loads(response.text)
    except json.JSONDecodeError as jde:
        LOGGER.error("Non-JSON response from HSM: %s", response.text)
        raise HWStateManagerException(jde) from jde
    try:
        return {component['ID'] for component in json_body['Components']
                    if component.get('Type', None) == 'Node'}
    except KeyError as ke:
        LOGGER.error("Unexpected API response from HSM: %s", exc_type_msg(ke))
        raise HWStateManagerException(ke) from ke


def get_components(node_list: list[str], enabled: Optional[bool]=None) -> HsmComponentsResponse:
    """
    Get information for all listed components in HSM

    :return the HSM components
    :rtype HsmComponentsResponse
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
                     response.reason, compact_response_text(response.text))
        response.raise_for_status()
        components = json.loads(response.text)
    except (ConnectionError, MaxRetryError) as e:
        LOGGER.error("Unable to connect to HSM: %s", exc_type_msg(e))
        raise e
    except HTTPError as e:
        LOGGER.error("Unexpected response from HSM: %s", exc_type_msg(e))
        raise e
    except json.JSONDecodeError as e:
        LOGGER.error("Non-JSON response from HSM: %s", exc_type_msg(e))
        raise e
    return components

NodeSetMapping = dict[str, set[str]]

class Inventory:
    """
    Inventory handles the generation of a hardware inventory in a similar manner to how the
    dynamic inventory is generated for CFS.  To reduce the number of calls to HSM, everything is
    cached for repeated checks, stored both as overall inventory and separate group types to allow
    use in finding BOS's base list of nodes, and lazily loaded to prevent extra calls when no limit
    is used.
    """

    def __init__(self, partition: Optional[str]=None) -> None:
        # partition can be specified to limit to roles/components query
        self._partition: Optional[str] = partition
        self._inventory: Optional[NodeSetMapping] = None
        self._groups: Optional[NodeSetMapping] = None
        self._partitions: Optional[NodeSetMapping] = None
        self._roles: Optional[NodeSetMapping] = None
        self._session: Optional[RequestsSession] = None

    @property
    def groups(self) -> NodeSetMapping:
        if self._groups is None:
            data = self.get('groups')
            groups = {}
            for group in data:
                groups[group['label']] = set(group.get('members', {}).get('ids', []))
            self._groups = groups
        return self._groups

    @property
    def partitions(self) -> NodeSetMapping:
        if self._partitions is None:
            data = self.get('partitions')
            partitions = {}
            for partition in data:
                partitions[partition['name']] = set(partition.get('members', {}).get('ids', []))
            self._partitions = partitions
        return self._partitions

    @property
    def roles(self) -> NodeSetMapping:
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
    def inventory(self) -> NodeSetMapping:
        if self._inventory is None:
            inventory = {}
            inventory.update(self.groups)
            inventory.update(self.partitions)
            inventory.update(self.roles)
            self._inventory = inventory
            LOGGER.info(self._inventory)
        return self._inventory

    def __contains__(self, key: str) -> bool:
        return key in self.inventory

    def __getitem__(self, key: str) -> set[str]:
        return self.inventory[key]

    @overload
    def get(self, path: Literal['groups'], params: Optional[JsonDict]=None) -> list[HsmGroup]:
        ...

    @overload
    def get(self, path: str, params: Optional[JsonDict]=None) -> JsonData:
        ...

    def get(self, path: str, params: Optional[JsonDict]=None) -> JsonData:
        url = os.path.join(BASE_ENDPOINT, path)
        if self._session is None:
            self._session = requests_retry_session()
        try:
            LOGGER.debug("HSM Inventory: GET %s with params=%s", url, params)
            response = self._session.get(url, params=params, verify=VERIFY)
            LOGGER.debug("Response status code=%d, reason=%s, body=%s", response.status_code,
                         response.reason, compact_response_text(response.text))
            response.raise_for_status()
        except HTTPError as err:
            LOGGER.error("Failed to get '%s': %s", url, exc_type_msg(err))
            raise
        try:
            return response.json()
        except ValueError:
            LOGGER.error("Couldn't parse a JSON response: %s", response.text)
            raise
