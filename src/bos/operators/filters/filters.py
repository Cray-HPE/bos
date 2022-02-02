#!/usr/bin/env python
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

import copy
from datetime import datetime, timedelta
from dateutil import parser
import logging
from typing import List, Type

from bos.operators.filters.base import BaseFilter, DetailsFilter, IDFilter, LocalFilter
from bos.operators.utils.clients.bos import BOSClient
from bos.operators.utils.clients.capmc import status as get_power_state
from bos.operators.utils.clients.cfs import get_components as get_cfs_components
from bos.operators.utils.clients.hsm import get_components as get_hsm_components


LOGGER = logging.getLogger('bos.operators.filters.filters')


# Usable filters
class OR(DetailsFilter):
    def __init__(self, filters_a, filters_b) -> None:
        super().__init__()
        self.filters_a: List[Type[BaseFilter]] = filters_a
        self.filters_b: List[Type[BaseFilter]] = filters_b

    def _filter(self, components: List[dict]) -> List[dict]:
        results_a = copy.deepcopy(components)
        for f in self.filters_a:
            results_a = f.filter(results_a)
        results_b = copy.deepcopy(components)
        for f in self.filters_b:
            results_b = f.filter(results_b)
        results_a_dict = {component['id']: component for component in results_a}
        results_b_dict = {component['id']: component for component in results_b}
        results = {**results_a_dict, **results_b_dict}
        return list(results.values())


class BOSQuery(DetailsFilter):
    """git Gets all components from BOS that match the kwargs """
    INITIAL: bool = True

    def __init__(self, **kwargs) -> None:
        """
        Init for the BOSQuery filter
        kwargs corresponds to arguments for the BOS get_components method
        """
        super().__init__()
        self.kwargs = kwargs
        self.bos_client = BOSClient()

    def _filter(self, components=None) -> List[dict]:
        return self.bos_client.components.get_components(**self.kwargs)


class HSMState(IDFilter):
    """ Returns all components that are in desired enabled state """
    def __init__(self, enabled: bool = None, ready: bool = None) -> None:
        super().__init__()
        self.enabled = enabled
        self.ready = ready

    def _filter(self, components: List[str]) -> List[str]:
        components = get_hsm_components(components, enabled=self.enabled)
        if self.ready is not None:
            return [component['ID'] for component in components['Components']
                    if (component['State'] == 'Ready') is self.ready]
        return [component['ID'] for component in components['Components']]


class PowerState(IDFilter):
    """ Returns all components that are in desired power state """
    def __init__(self, state: str = 'on') -> None:
        super().__init__()
        self.state = state

    def _filter(self, components: List[str]) -> List[str]:
        # Address CASMCMS-7804: Once that Jira is resolved, uncomment this line
        # and delete the one below it.
        # response, _, _ = get_power_state(components, filtertype='show_{}'.format(self.state))
        response, _, _ = get_power_state(components)
        return response[self.state]


class ConfigurationStatus(IDFilter):
    """ Returns all components that are in desired configuration status """
    def __init__(self, status: str = 'configured') -> None:
        super().__init__()
        self.status = status

    def _filter(self, components: List[str]) -> List[str]:
        components = get_cfs_components(ids=components, status=self.status)
        return [component['id'] for component in components]


class NOT(LocalFilter):
    """ Returns the opposite of the given filter.  Use on local filters only."""
    def __init__(self, filter: Type[LocalFilter]) -> None:
        self.negated_filter = filter

    def _match(self, component: dict):
        return not self.negated_filter._match(component)


class TimeSinceLastAction(LocalFilter):
    """ Returns all components whose last actions was over some time ago """
    def __init__(self, **kwargs) -> None:
        """
        Init for the TimeSinceLastAction filter
        kwargs corresponds to arguments for datetime.timedelta
        """
        super().__init__()
        self.kwargs = kwargs

    def _match(self, component: dict) -> bool:
        last_action_time = component.get('lastAction', {}).get('lastUpdated')
        now = datetime.utcnow()
        if not last_action_time or now > parser.parse(last_action_time) + timedelta(**self.kwargs):
            return True
        return False


class LastActionIs(LocalFilter):
    """ Returns with the specified last action(s) """
    def __init__(self, actions: str) -> None:
        super().__init__()
        self.actions = actions.split(',')

    def _match(self, component: dict) -> bool:
        last_action = component.get('lastAction', {}).get('action', '')
        if last_action in self.actions:
            return True
        return False


class BootArtifactStatesMatch(LocalFilter):
    """ Returns when current and desired kernel and image states match """
    # TODO: Use the bss token to make this comparison
    def _match(self, component: dict) -> bool:
        desired_state = component.get('desiredState', {})
        current_state = component.get('currentState', {})
        desired_boot_state = desired_state.get('bootArtifacts', {})
        current_boot_state = current_state.get('bootArtifacts', {})
        for key in ['kernel', 'kernel_parameters', 'initrd']:
            if desired_boot_state.get(key, None) != current_boot_state.get(key, None):
                return False
        return True


class DesiredConfigurationSetInCFS(DetailsFilter):
    """ Returns when desired configuration is set in CFS """
    def _filter(self, components: List[dict]) -> List[dict]:
        cfs_components = get_cfs_components(ids=components)
        cfs_components_dict = {component['id']: component for component in cfs_components}

        matching_components = []
        for component in components:
            if self._match(component, cfs_components_dict[component['id']]):
                matching_components.append(component)
        return matching_components

    def _match(self, component: dict, cfs_component: dict) -> bool:
        desired_configuration = component.get('desiredState', {}).get('configuration')
        set_configuration = cfs_component.get('desiredConfig')
        return desired_configuration == set_configuration


class DesiredBootStateIsNone(LocalFilter):
    """ Returns when the desired state is None """
    def _match(self, component: dict) -> bool:
        desired_state = component.get('desiredState', {})
        desired_boot_state = desired_state.get('bootArtifacts', {})
        if not desired_boot_state or not all([bool(v) for v in desired_boot_state.values()]):
            return True
        return False


class DesiredConfigurationIsNone(LocalFilter):
    """ Returns when the desired configuration is None """
    def _match(self, component: dict) -> bool:
        desired_state = component.get('desiredState', {})
        if not desired_state or not desired_state.get('configuration', ''):
            return True
        return False
