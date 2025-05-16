#!/usr/bin/env python
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

"""
Filter classes for BOS operators
"""

from collections.abc import Container, Iterable
import copy
from datetime import timedelta
import logging
import re
from typing import Unpack

from bos.common.clients.bos import BOSClient
from bos.common.clients.cfs import CFSClient, CfsComponentData
from bos.common.clients.hsm import HSMClient
from bos.common.types.components import (ComponentActualState,
                                         ComponentDesiredState,
                                         ComponentLastAction,
                                         ComponentRecord,
                                         GetComponentsFilter)
from bos.common.utils import get_current_time, load_timestamp
from bos.operators.filters.base import BaseFilter, DetailsFilter, IDFilter, LocalFilter

LOGGER = logging.getLogger(__name__)


# Usable filters
class OR(DetailsFilter):

    def __init__(self, filters_a: list[BaseFilter], filters_b: list[BaseFilter]) -> None:
        super().__init__()
        self.filters_a = filters_a
        self.filters_b = filters_b

    def filter_components(self, components: list[ComponentRecord]) -> list[ComponentRecord]:
        results_a = copy.deepcopy(components)
        for f in self.filters_a:
            results_a = f.filter(results_a)
        results_b = copy.deepcopy(components)
        for f in self.filters_b:
            results_b = f.filter(results_b)
        results_a_dict = {
            component['id']: component
            for component in results_a
        }
        results_b_dict = {
            component['id']: component
            for component in results_b
        }
        results = {**results_a_dict, **results_b_dict}
        return list(results.values())


class BOSQuery(DetailsFilter):
    """Gets all components from BOS that match the kwargs """
    INITIAL: bool = True

    def __init__(self, bos_client: BOSClient, **kwargs: Unpack[GetComponentsFilter]) -> None:
        """
        Init for the BOSQuery filter
        kwargs corresponds to arguments for the BOS get_components method
        """
        super().__init__()
        self.kwargs = kwargs
        self.bos_client = bos_client

    def filter_components(self, _: list[ComponentRecord]) -> list[ComponentRecord]:
        return self.bos_client.components.get_components(**self.kwargs)


class HSMState(IDFilter):
    """ Returns all components that are in specified state """

    def __init__(self,
                 hsm_client: HSMClient,
                 enabled: bool | None = None,
                 ready: bool | None = None) -> None:
        super().__init__()
        self.enabled = enabled
        self.ready = ready
        self.hsm_client = hsm_client

    def filter_component_ids(self, components: list[str]) -> list[str]:
        hsm_components = self.hsm_client.state_components.get_components(components,
                                                                         enabled=self.enabled)
        if self.ready is None:
            return [component['ID'] for component in hsm_components['Components']]
        return [
            component['ID'] for component in hsm_components['Components']
            if (component['State'] == 'Ready') is self.ready
        ]

    def filter_by_arch(self, nodes: Iterable[str], arch: Container[str]) -> list[str]:
        """
        Given a list of component names, query HSM for state information pertaining to arch.
        Components that match one of the arch values specified are returned as a list of
        component IDs. HSM components that do not have arch information are considered to be
        of type 'Unknown' for reasons of compatibility.
        args:
          components: a set of xnames
          arch: a set containing HSM archs as represented by strings
        returns:
          A list of xnames all matching one of the archs requested
        """
        components = self.hsm_client.state_components.get_components(
            list(nodes), enabled=self.enabled)
        return [
            component['ID'] for component in components['Components']
            if component.get('Arch', 'Unknown') in arch
        ]


class TimeSinceLastAction(LocalFilter):
    """ Returns all components whose last actions was over some time ago """

    def __init__(self, seconds: float, negate: bool = False) -> None:
        """
        Init for the TimeSinceLastAction filter
        seconds corresponds to arguments for datetime.timedelta
        """
        super().__init__(negate=negate)
        self.seconds = seconds

    def component_match(self, component: ComponentRecord) -> bool:
        last_action_time = component.get('last_action', ComponentLastAction()).get('last_updated')
        if not last_action_time:
            return True
        now = get_current_time()
        if now > load_timestamp(last_action_time) + timedelta(seconds=self.seconds):
            return True
        return False


class LastActionIs(LocalFilter):
    """ Returns with the specified last action(s) """

    def __init__(self, actions: str, negate: bool = False) -> None:
        super().__init__(negate=negate)
        self.actions = actions.split(',')

    def component_match(self, component: ComponentRecord) -> bool:
        last_action = component.get('last_action', ComponentLastAction()).get('action', '')
        if last_action in self.actions:
            return True
        return False


class BootArtifactStatesMatch(LocalFilter):
    """ Returns when current and desired kernel and image states match """

    def component_match(self, component: ComponentRecord) -> bool:
        desired_state = component.get('desired_state', ComponentDesiredState())
        actual_state = component.get('actual_state', ComponentActualState())
        desired_boot_state = desired_state.get('boot_artifacts')
        actual_boot_state = actual_state.get('boot_artifacts')
        if desired_boot_state is None:
            return actual_boot_state is None
        if actual_boot_state is None:
            return False
        # Both are not None
        for key in ['kernel', 'initrd']:
            if desired_boot_state.get(key) != actual_boot_state.get(key):
                return False
        # Filter out kernel parameters that dynamically change.
        actual_kernel_parameters = self._sanitize_kernel_parameters(
            actual_boot_state.get('kernel_parameters', None))
        desired_kernel_parameters = self._sanitize_kernel_parameters(
            desired_boot_state.get('kernel_parameters', None))

        if actual_kernel_parameters != desired_kernel_parameters:
            return False

        return True

    def _sanitize_kernel_parameters(self, parameter_string: str | None) -> str | None:
        """
        Filter out kernel parameters that dynamically change from session to session and
        should not be used for comparison.
        * spire_join_token

        Returns:
        A parameter string without the dynamic parameters or None if the string is None
        """
        if not parameter_string:
            return None
        return re.sub(r'(^\\s)+spire_join_token=[\S]*', '', parameter_string)


class DesiredConfigurationSetInCFS(LocalFilter):
    """ Returns when desired configuration is set in CFS """

    def __init__(self, cfs_client: CFSClient, negate: bool = False) -> None:
        super().__init__(negate=negate)
        self.cfs_components_dict: dict[str, CfsComponentData] = {}
        self.cfs_client = cfs_client

    def filter_components(self, components: list[ComponentRecord]) -> list[ComponentRecord]:
        component_ids = [component['id'] for component in components]
        cfs_components = self.cfs_client.components.get_components_from_id_list(
            id_list=component_ids)
        self.cfs_components_dict = {
            component['id']: component
            for component in cfs_components
        }
        matches = LocalFilter.filter_components(self, components)
        # Clear this, so there are no lingering side-effects of running this method.
        self.cfs_components_dict = {}
        return matches

    def component_match(self, component: ComponentRecord,
                        cfs_component: CfsComponentData | None = None) -> bool:
        # There are two ways to communicate the cfs_component to this method.
        # First: cfs_component input variable
        # Second: cfs_component_dict instance attribute
        #
        # The reason for the second input method is the NOT filter class does
        # not allow the cfs_component parameter to be passed into this function.
        # This necessitated passing the CFS components through the instance attribute
        # cfs_components_dict.
        # However, the status operator needs to pass in the cfs_component parameter
        # (i.e. the first method) because it is not calling the _filter method
        # which sets/updates the cfs_components_dict attribute.
        desired_configuration = component.get('desired_state',
                                              ComponentDesiredState()).get('configuration')
        if cfs_component is None:
            set_configuration = self.cfs_components_dict[component['id']].get(
                'desired_config')
        else:
            set_configuration = cfs_component.get('desired_config')
        return desired_configuration == set_configuration


class DesiredBootStateIsNone(LocalFilter):
    """ Returns when the desired state is None """

    def component_match(self, component: ComponentRecord) -> bool:
        desired_state = component.get('desired_state', ComponentDesiredState())
        desired_boot_state = desired_state.get('boot_artifacts')
        if not desired_boot_state or not any(
                bool(v) for v in desired_boot_state.values()):
            return True
        return False


class DesiredBootStateIsOff(LocalFilter):
    """ Returns when the desired state has no kernel set """

    def component_match(self, component: ComponentRecord) -> bool:
        desired_state = component.get('desired_state', ComponentDesiredState())
        desired_boot_state = desired_state.get('boot_artifacts')
        if not desired_boot_state or not desired_boot_state.get('kernel'):
            return True
        return False


class DesiredConfigurationIsNone(LocalFilter):
    """ Returns when the desired configuration is None """

    def component_match(self, component: ComponentRecord) -> bool:
        desired_state = component.get('desired_state', ComponentDesiredState())
        if not desired_state or not desired_state.get('configuration', ''):
            return True
        return False


class ActualStateAge(LocalFilter):
    """ Returns all components whose Actual State age is older than <age> seconds. """

    def __init__(self, seconds: float, negate: bool = False) -> None:
        """
        Init for the ActualStateAge filter
        seconds corresponds to arguments for datetime.timedelta
        """
        super().__init__(negate=negate)
        self.seconds = seconds

    def component_match(self, component: ComponentRecord) -> bool:
        last_updated = component.get('actual_state', ComponentActualState()).get('last_updated')
        if not last_updated:
            return True
        now = get_current_time()
        if now > load_timestamp(last_updated) + timedelta(seconds=self.seconds):
            return True
        return False


class ActualBootStateIsSet(LocalFilter):
    """ Returns when the actual state has any non-timestamp fields set """

    def component_match(self, component: ComponentRecord) -> bool:
        actual_state_boot_artifacts = component.get('actual_state', {}).get(
            'boot_artifacts', {})
        # The timestamp field doesn't count as a set record we particularly care about
        if 'timestamp' in actual_state_boot_artifacts:
            del actual_state_boot_artifacts['timestamp']
        return any(bool(v) for v in actual_state_boot_artifacts.values())
