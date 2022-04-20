#!/usr/bin/env python
#
# MIT License
#
# (C) Copyright 2022 Hewlett Packard Enterprise Development LP
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
import logging

from bos.common.values  import Phase, Status, Action
from bos.operators.base import BaseOperator, main
from bos.operators.filters import DesiredBootStateIsOff, BootArtifactStatesMatch,\
    DesiredConfigurationIsNone, DesiredConfigurationSetInCFS, LastActionIs, TimeSinceLastAction
from bos.operators.utils.clients.bos.options import options
from bos.operators.utils.clients.capmc import status as get_power_states
from bos.operators.utils.clients.cfs import get_components as get_cfs_components

LOGGER = logging.getLogger('bos.operators.status')


class StatusOperator(BaseOperator):
    """
    The Status Operator monitors and sets the phase for all components.
    Also disables stable components if necessary and sets some status overrides.
    """
    def __init__(self):
        super().__init__()
        # Reuse filter code
        self.desired_boot_state_is_off = DesiredBootStateIsOff()._match
        self.boot_artifact_states_match = BootArtifactStatesMatch()._match
        self.desired_configuration_is_none = DesiredConfigurationIsNone()._match
        self.desired_configuration_set_in_cfs = DesiredConfigurationSetInCFS()._match
        self.last_action_is_power_on = LastActionIs(Action.power_on)._match
        self.power_on_wait_time_elapsed = TimeSinceLastAction(minutes=options.max_power_on_wait_time)._match

    @property
    def name(self):
        """ Unused for the status operator """
        return ''

    # This operator overrides _run and does not use "filters" or "_act", but they are defined here
    # because they are abstract methods in the base class and must be implemented.
    @property
    def filters(self):
        return []

    def _act(self, components):
        return components

    def _run(self) -> None:
        """ A single pass of detecting and acting on components  """
        components = self.bos_client.components.get_components(enabled=True)
        component_ids = [component['id'] for component in components]
        power_states = self._get_power_states(component_ids)
        cfs_states = self._get_cfs_components(','.join(component_ids))
        updated_components = []
        for component in components:
            updated_component = self._check_status(
                component, power_states.get(component['id']), cfs_states.get(component['id']))
            if updated_component:
                updated_components.append(updated_component)
        if not updated_components:
            LOGGER.debug('No components require status updates')
            return
        LOGGER.info('Found {} components that require status updates'.format(len(updated_components)))
        self.bos_client.components.update_components(updated_components)

    @staticmethod
    def _get_power_states(component_ids):
        power_data, _, _ = get_power_states(component_ids)
        power_states = {}
        for state in ['on', 'off']:
            for component_id in power_data.get(state, []):
                power_states[component_id] = state
        return power_states

    @staticmethod
    def _get_cfs_components(component_ids):
        cfs_data = get_cfs_components(ids=component_ids)
        cfs_states = {}
        for component in cfs_data:
            cfs_states[component['id']] = component
        return cfs_states

    def _check_status(self, component, power_state, cfs_component):
        phase, override, disable, error = self._get_status(component, power_state, cfs_component)
        updated_component = {
            'id': component['id'],
            'status': {
                'status_override': '',
            }
        }
        update = False
        if phase != component.get('status', {}).get('phase', ''):
            updated_component['status']['phase'] = phase
            update = True
        if override != component.get('status', {}).get('status_override', ''):
            updated_component['status']['status_override'] = override
            update = True
        if disable and options.disable_components_on_completion:
            updated_component['enabled'] = False
            update = True
        if error:
            updated_component['error'] = error
            update = True
        if update:
            return updated_component
        return None

    def _get_status(self, component, power_state, cfs_component):
        """
        Disabling for successful completion should return an empty phase
        Disabling for a failure should return the phase that failed
        Override is used for status information that cannot be determined using only
            internal BOS information, such as a failed configuration state.
        """
        phase = ''
        override = ''
        disable = False
        error = ''

        status_data = component.get('status', {})
        if status_data.get('status') == Status.failed:
            disable = True  # Failed state - the aggregated status if "failed"
        if power_state == 'off':
            if self.desired_boot_state_is_off(component):
                phase = Phase.none
                disable = True  # Successful state - desired and actual state are off
            else:
                phase = Phase.powering_on
        elif power_state == 'on':
            if self.desired_boot_state_is_off(component):
                phase = Phase.powering_off
            elif self.boot_artifact_states_match(component):
                if not self.desired_configuration_set_in_cfs(component, cfs_component):
                    phase = Phase.configuring
                elif self.desired_configuration_is_none(component, cfs_component):
                    phase = Phase.none
                    disable = True  # Successful state - booted with the correct artifacts, no configuration necessary
                else:
                    cfs_status = cfs_component.get('configurationStatus')
                    if cfs_status == 'configured':
                        phase = Phase.none
                        disable = True  # Successful state - booted with the correct artifacts and configured
                    elif cfs_status == 'failed':
                        phase = Phase.configuring
                        disable = True  # Failed state - configuration failed
                        override = Status.failed
                        error = 'cfs configuration failed'
                    elif cfs_status == 'pending':
                        phase = Phase.configuring
                    else:
                        phase = Phase.configuring
                        disable = True  # Failed state - configuration is no longer set
                        override = Status.failed
                        error = 'cfs is not reporting a valid configuration status for this component'
            else:
                if self.last_action_is_power_on(component) and not self.power_on_wait_time_elapsed(component):
                    phase = Phase.powering_on
                else:
                    # Includes both power-off for restarts and ready-recovery scenario
                    phase = Phase.powering_off
        else:
            disable = True  # Failed state - configuration is no longer set
            override = Status.failed
            error = 'capmc is not reporting a valid power state for this component'

        return phase, override, disable, error


if __name__ == '__main__':
    main(StatusOperator)
