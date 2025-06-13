#!/usr/bin/env python
#
# MIT License
#
# (C) Copyright 2022-2025 Hewlett Packard Enterprise Development LP
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
BOS component status operator
"""

from dataclasses import dataclass
import logging
from typing import Literal

from bos.common.clients.bos.options import options
from bos.common.clients.cfs.types import CfsComponentData
from bos.common.types.components import (ComponentLastAction,
                                         ComponentRecord,
                                         ComponentStatus)
from bos.common.values import (Action,
                               ComponentPhaseStr,
                               ComponentStatusStr,
                               Phase,
                               Status,
                               EMPTY_ACTUAL_STATE)
from bos.operators.base import BaseOperator, main
from bos.operators.filters import (BootArtifactStatesMatch,
                                   DesiredBootStateIsOff,
                                   DesiredConfigurationIsNone,
                                   LastActionIs,
                                   TimeSinceLastAction)
from bos.operators.filters.base import BaseFilter

LOGGER = logging.getLogger(__name__)

@dataclass
class _StatusData:
    """
    To simplify passing status data around inside StatusOperator
    """
    phase: ComponentPhaseStr = Phase.none
    override: ComponentStatusStr | Literal[''] = ''
    disable: bool = False
    error: str = ''
    action_failed: bool = False


class StatusOperator(BaseOperator):
    """
    The Status Operator monitors and sets the phase for all components.
    Also disables stable components if necessary and sets some status overrides.
    """

    def __init__(self) -> None:
        super().__init__()
        # Reuse filter code
        self.desired_boot_state_is_off = DesiredBootStateIsOff().component_match
        self.boot_artifact_states_match = BootArtifactStatesMatch().component_match
        self.desired_configuration_is_none = DesiredConfigurationIsNone().component_match
        self.last_action_is_power_on = LastActionIs(Action.power_on).component_match
        self.boot_wait_time_elapsed = TimeSinceLastAction(
            seconds=options.max_boot_wait_time).component_match
        self.power_on_wait_time_elapsed = TimeSinceLastAction(
            seconds=options.max_power_on_wait_time).component_match

    def desired_configuration_set_in_cfs(self, component: ComponentRecord,
                                         cfs_component: CfsComponentData | None = None) -> bool:
        """
        Shortcut to DesiredConfigurationSetInCFS._match method
        """
        return self.DesiredConfigurationSetInCFS().component_match(component=component,
                                                                   cfs_component=cfs_component)

    # This operator overrides _run and does not use "filters" or "_act", but they are defined here
    # because they are abstract methods in the base class and must be implemented.
    @property
    def filters(self) -> list[BaseFilter]:
        return []

    def _act(self, components: list[ComponentRecord]) -> list[ComponentRecord]:
        return components

    def _run(self) -> None:
        """ A single pass of detecting and acting on components  """
        components = self.client.bos.components.get_components(enabled=True)
        if not components:
            LOGGER.debug('No enabled components found')
            return
        LOGGER.debug('Found %d components that require action',
                     len(components))
        for chunk in self._chunk_components(components):
            self._run_on_chunk(chunk)

    def _run_on_chunk(self, components: list[ComponentRecord]) -> None:
        """
        Acts on a chunk of components
        """
        LOGGER.debug("Processing %d components", len(components))
        component_ids = [component['id'] for component in components]
        power_states = self.client.pcs.power_status.node_to_powerstate(
            component_ids)
        cfs_states = self._get_cfs_components()
        updated_components = []
        # Recreate these filters to pull in the latest options values
        self.boot_wait_time_elapsed = TimeSinceLastAction(
            seconds=options.max_boot_wait_time).component_match
        self.power_on_wait_time_elapsed = TimeSinceLastAction(
            seconds=options.max_power_on_wait_time).component_match
        for component in components:
            updated_component = self._check_status(
                component, power_states.get(component['id']),
                cfs_states.get(component['id']))
            if updated_component:
                updated_components.append(updated_component)
        if not updated_components:
            LOGGER.debug('No components require status updates')
            return
        LOGGER.info('Found %d components that require status updates',
                    len(updated_components))
        LOGGER.debug('Updated components: %s', updated_components)
        self.client.bos.components.update_components(updated_components)

    def _get_cfs_components(self) -> dict[str, CfsComponentData]:
        """
        Gets all the components from CFS.
        We used to get only the components of interest, but that caused an HTTP request
        that was longer than uwsgi could handle when the number of nodes was very large.
        Requesting all components means none need to be specified in the request.
        """
        cfs_data = self.client.cfs.components.get_components()
        cfs_states: dict[str, CfsComponentData] = {}
        for component in cfs_data:
            cfs_states[component['id']] = component
        return cfs_states

    def _check_status(self, component: ComponentRecord, power_state: str|None,
                      cfs_component: CfsComponentData|None) -> ComponentRecord | None:
        """
        Calculate the component's current status based upon its power state and CFS configuration
        state. If its status differs from the status in the database, return this information.
        """
        if power_state and cfs_component:
            new_status = self._calculate_status(component, power_state, cfs_component)
        else:
            # If the component cannot be found in pcs or cfs
            new_status = _StatusData(override=Status.on_hold, disable=True)
            if not power_state or power_state == 'undefined':
                new_status.error = 'Component information was not returned by pcs'
            elif not cfs_component:
                new_status.error = 'Component information was not returned by cfs'

        return _updated_component(component, new_status)

    def _calculate_status(self, component: ComponentRecord, power_state: str,
                          cfs_component: CfsComponentData) -> _StatusData:
        """
        Calculate a component's status based on its current state, power state, and
        CFS state.

        Disabling for successful completion should return an empty phase
        Disabling for a failure should return the phase that failed
        Override is used for status information that cannot be determined using only
            internal BOS information, such as a failed configuration state.
        """
        calculated_status = _StatusData()

        status_data = component.get('status', ComponentStatus())
        if status_data.get('status') == Status.failed:
            calculated_status.disable = True  # Failed state - the aggregated status if "failed"
            calculated_status.override = Status.failed

        if power_state == 'off':
            self._calculate_status_power_state_off(component, calculated_status)
            return calculated_status

        if self.desired_boot_state_is_off(component):
            calculated_status.phase = Phase.powering_off
            return calculated_status

        if self.boot_artifact_states_match(component):
            self._calculate_status_not_power_off_boot_artifacts_match(component, cfs_component,
                                                                      calculated_status)
            return calculated_status

        if self.last_action_is_power_on(component) and not self.boot_wait_time_elapsed(component):
            calculated_status.phase = Phase.powering_on
            return calculated_status

        # Includes both power-off for restarts and ready-recovery scenario
        calculated_status.phase = Phase.powering_off
        return calculated_status

    def _calculate_status_power_state_off(self, component: ComponentRecord,
                                          calculated_status: _StatusData) -> None:
        """
        Helper function for _calculate_status, called when the power_state is "off"
        """
        if self.desired_boot_state_is_off(component):
            calculated_status.phase = Phase.none
            calculated_status.disable = True  # Successful state - desired and actual state are off
            return
        if self.last_action_is_power_on(component) and self.power_on_wait_time_elapsed(component):
            calculated_status.action_failed = True
        calculated_status.phase = Phase.powering_on


    def _calculate_status_not_power_off_boot_artifacts_match(
        self,
        component: ComponentRecord,
        cfs_component: CfsComponentData,
        calculated_status: _StatusData
    ) -> None:
        """
        Helper function for _calculate_status, called when all of the following are true:
        - the power_state is not "off",
        - the desired power state is not "off"
        - self.boot_artifact_states_match(component) is True
        """
        if not self.desired_configuration_set_in_cfs(component, cfs_component):
            calculated_status.phase = Phase.configuring
            return

        if self.desired_configuration_is_none(component):
            # Successful state - booted with the correct artifacts,
            # no configuration necessary
            calculated_status.phase = Phase.none
            calculated_status.disable = True
            return

        cfs_status = cfs_component.get('configuration_status', '').lower()
        match cfs_status:
            case 'configured':
                # Successful state - booted with the correct artifacts and configured
                calculated_status.phase = Phase.none
                calculated_status.disable = True
            case 'failed':
                # Failed state - configuration failed
                calculated_status.phase = Phase.configuring
                calculated_status.disable = True
                calculated_status.override = Status.failed
                calculated_status.error = 'cfs configuration failed'
            case 'pending':
                calculated_status.phase = Phase.configuring
            case _:
                # Failed state - configuration is no longer set
                calculated_status.phase = Phase.configuring
                calculated_status.disable = True
                calculated_status.override = Status.failed
                calculated_status.error = ('cfs is not reporting a valid configuration status for '
                                           f'this component: {cfs_status}')


def _updated_component(comp: ComponentRecord, new_status: _StatusData) -> ComponentRecord | None:
    """
    Helper function for _check_status method
    """
    updated_component: ComponentRecord = {
        'id': comp['id'],
        'status': ComponentStatus(status_override=new_status.override or '')
    }
    update = _check_phase(new_status.phase, comp, updated_component)
    if new_status.override != comp.get('status', ComponentStatus()).get('status_override', ''):
        update = True
    if new_status.disable:
        updated_component['enabled'] = False
        update = True
    if new_status.error and new_status.error != comp.get('error', ''):
        updated_component['error'] = new_status.error
        update = True
    af = new_status.action_failed
    if af and af != comp.get('last_action', ComponentLastAction()).get('failed', False):
        updated_component['last_action'] = ComponentLastAction(failed=True)
        update = True
    if update:
        return updated_component
    return None


def _check_phase(phase: ComponentPhaseStr, component: ComponentRecord,
                 updated_component: ComponentRecord) -> bool:
    """
    Sets fields in update_component based on the phase and current component data
    Returns boolean to indicate if update_component was modified.
    """
    previous_phase = component.get('status', ComponentStatus()).get('phase', Phase.none)
    if phase == previous_phase:
        return False
    if phase == Phase.none:
        # The current event has completed.  Reset the event stats
        updated_component['event_stats'] = {
            "power_on_attempts": 0,
            "power_off_graceful_attempts": 0,
            "power_off_forceful_attempts": 0
        }
    if previous_phase == Phase.powering_off:
        # Powering off has been completed.  The actual state can be cleared.
        updated_component['actual_state'] = EMPTY_ACTUAL_STATE
    updated_component['status']['phase'] = phase
    return True


if __name__ == '__main__':
    main(StatusOperator)
