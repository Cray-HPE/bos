#!/usr/bin/env python
#
# MIT License
#
# (C) Copyright 2021-2022 Hewlett Packard Enterprise Development LP
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
import copy
from datetime import timedelta
import logging
from typing import List, Type

from bos.common.utils import get_current_time, load_timestamp
from bos.operators.filters.base import BaseFilter, DetailsFilter, IDFilter, LocalFilter
from bos.operators.utils.clients.bos import BOSClient
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
    """Gets all components from BOS that match the kwargs """
    INITIAL: bool = True

    def __init__(self, **kwargs) -> None:
        """
        Init for the BOSQuery filter
        kwargs corresponds to arguments for the BOS get_components method
        """
        super().__init__()
        self.kwargs = kwargs
        self.bos_client = BOSClient()

    def _filter(self, _) -> List[dict]:
        return self.bos_client.components.get_components(**self.kwargs)


class HSMState(IDFilter):
    """ Returns all components that are in desired enabled state """

    def __init__(self, enabled: bool=None, ready: bool=None) -> None:
        super().__init__()
        self.enabled = enabled
        self.ready = ready

    def _filter(self, components: List[str]) -> List[str]:
        components = get_hsm_components(components, enabled=self.enabled)
        if self.ready is not None:
            return [component['ID'] for component in components['Components']
                    if (component['State'] == 'Ready') is self.ready]
        return [component['ID'] for component in components['Components']]


class NOT(LocalFilter):
    """ Returns the opposite of the given filter.  Use on local filters only."""

    def __init__(self, filter: Type[LocalFilter]) -> None:
        self.negated_filter = filter

    def _filter(self, components: List[dict]) -> List[dict]:
        return self.negated_filter._filter(components)

    def _match(self, components: dict):
        return not self.negated_filter._match(components)


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
        last_action_time = component.get('last_action', {}).get('last_updated')
        now = get_current_time()
        if not last_action_time or now > load_timestamp(last_action_time) + timedelta(**self.kwargs):
            return True
        return False


class LastActionIs(LocalFilter):
    """ Returns with the specified last action(s) """

    def __init__(self, actions: str) -> None:
        super().__init__()
        self.actions = actions.split(',')

    def _match(self, component: dict) -> bool:
        last_action = component.get('last_action', {}).get('action', '')
        if last_action in self.actions:
            return True
        return False


class BootArtifactStatesMatch(LocalFilter):
    """ Returns when current and desired kernel and image states match """

    def _match(self, component: dict) -> bool:
        desired_state = component.get('desired_state', {})
        actual_state = component.get('actual_state', {})
        desired_boot_state = desired_state.get('boot_artifacts', {})
        actual_boot_state = actual_state.get('boot_artifacts', {})
        for key in ['kernel', 'kernel_parameters', 'initrd']:
            if desired_boot_state.get(key, None) != actual_boot_state.get(key, None):
                return False
        return True


class DesiredConfigurationSetInCFS(LocalFilter):
    """ Returns when desired configuration is set in CFS """

    def __init__(self):
        self.cfs_components_dict = {}
        super().__init__()

    def _filter(self, components: List[dict]) -> List[dict]:
        component_ids = ','.join([component['id'] for component in components])
        cfs_components = get_cfs_components(ids=component_ids)
        self.cfs_components_dict = {component['id']: component for component in cfs_components}
        return super()._filter(components)

    def _match(self, component: dict, cfs_component: dict=None) -> bool:
        # The NOT filter class does not allow the cfs_component parameter to be passed
        # into this function. This necessitated passing the CFS components through the instance attribute
        # cfs_components_dict.
        # The status operator needs to pass in the cfs_component parameter because it is
        # not calling the _filter method which sets/updates eth cfs_components_dict attribute.
        desired_configuration = component.get('desired_state', {}).get('configuration')
        if cfs_component is None:
            set_configuration = self.cfs_components_dict[component['id']].get('desired_config')
        else:
            set_configuration = cfs_component.get('desired_config')
        return desired_configuration == set_configuration


class DesiredBootStateIsNone(LocalFilter):
    """ Returns when the desired state is None """

    def _match(self, component: dict) -> bool:
        desired_state = component.get('desired_state', {})
        desired_boot_state = desired_state.get('boot_artifacts', {})
        if not desired_boot_state or not any([bool(v) for v in desired_boot_state.values()]):
            return True
        return False


class DesiredBootStateIsOff(LocalFilter):
    """ Returns when the desired state has no kernel set """

    def _match(self, component: dict) -> bool:
        desired_state = component.get('desired_state', {})
        desired_boot_state = desired_state.get('boot_artifacts', {})
        if not desired_boot_state.get('kernel'):
            return True
        return False


class DesiredConfigurationIsNone(LocalFilter):
    """ Returns when the desired configuration is None """

    def _match(self, component: dict) -> bool:
        desired_state = component.get('desired_state', {})
        if not desired_state or not desired_state.get('configuration', ''):
            return True
        return False


class ActualStateAge(LocalFilter):
    """ Returns all components whose Actual Stage age is older than <age>, as set in kwargs. """

    def __init__(self, **kwargs) -> None:
        """
        Init for the ActualStateAge filter
        kwargs corresponds to arguments for datetime.timedelta
        """
        super().__init__()
        self.kwargs = kwargs

    def _match(self, component: dict) -> bool:
        last_updated = component.get('actual_state', {}).get('last_updated')
        now = get_current_time()
        if not last_updated or now > load_timestamp(last_updated) + timedelta(**self.kwargs):
            return True
        return False


class ActualBootStateIsNone(LocalFilter):
    """ Returns when the actual state is None """

    def _match(self, component: dict) -> bool:
        actual_state = component.get('actual_state', {})
        actual_boot_state = actual_state.get('boot_artifacts', {})
        if not actual_boot_state or not any([bool(v) for v in actual_boot_state.values()]):
            return True
        return False

