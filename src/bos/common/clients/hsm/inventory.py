#
# MIT License
#
# (C) Copyright 2021-2025 Hewlett Packard Enterprise Development LP
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

from .client import HSMClient

LOGGER = logging.getLogger(__name__)


class Inventory:
    """
    Inventory handles the generation of a hardware inventory in a similar manner to how the
    dynamic inventory is generated for CFS.  To reduce the number of calls to HSM, everything is
    cached for repeated checks, stored both as overall inventory and separate group types to allow
    use in finding BOS's base list of nodes, and lazily loaded to prevent extra calls when no limit
    is used.
    """

    def __init__(self, hsm_client: HSMClient, partition=None):
        self._partition = partition  # Can be specified to limit to roles/components query
        self._inventory = None
        self._groups = None
        self._partitions = None
        self._roles = None
        self.hsm_client = hsm_client

    @property
    def groups(self):
        if self._groups is None:
            data = self.hsm_client.groups.list()
            groups = {}
            for group in data:
                groups[group['label']] = set(
                    group.get('members', {}).get('ids', []))
            self._groups = groups
        return self._groups

    @property
    def partitions(self):
        if self._partitions is None:
            data = self.hsm_client.partitions.list()
            partitions = {}
            for partition in data:
                partitions[partition['name']] = set(
                    partition.get('members', {}).get('ids', []))
            self._partitions = partitions
        return self._partitions

    @property
    def roles(self):
        if self._roles is None:
            params = {}
            if self._partition:
                params['partition'] = self._partition
            data = self.hsm_client.state_components.list(params=params)
            roles = defaultdict(set)
            for component in data['Components']:
                role = ''
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
