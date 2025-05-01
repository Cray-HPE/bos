#
# MIT License
#
# (C) Copyright 2025 Hewlett Packard Enterprise Development LP
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
from typing import Literal, Required, TypedDict, get_args
from typing_extensions import TypeIs

PowerState = Literal['off', 'on', 'undefined']
ManagementState = Literal['available', 'unavailable']

PowerOperation = Literal['On', 'Off', 'Soft-Off', 'Soft-Restart', 'Hard-Restart', 'Init',
                         'Force-Off']

# This fancy footwork lets us construct a frozenset of the string values from the previous
# definition, allowing us to avoid duplicating it.
POWER_OPERATIONS: frozenset[PowerOperation] = frozenset(get_args(PowerOperation))

def is_power_operation(string: str) -> TypeIs[PowerOperation]:
    return string in POWER_OPERATIONS

class ReservedLocation(TypedDict, total=False):
    """
    https://github.com/Cray-HPE/hms-power-control/blob/master/api/swagger.yaml
    '#/components/schemas/reserved_location'
    """
    xname: Required[str]
    deputyKey: str

class TransitionCreate(TypedDict, total=False):
    """
    https://github.com/Cray-HPE/hms-power-control/blob/master/api/swagger.yaml
    '#/components/schemas/transition_create'
    """
    # Per the PCS spec, none of these fields are required, but we mark them as required here
    # because we always want to specify them
    operation: Required[PowerOperation]
    location: Required[list[ReservedLocation]]
    taskDeadlineMinutes: int

class TransitionStartOutput(TypedDict, total=False):
    """
    https://github.com/Cray-HPE/hms-power-control/blob/master/api/swagger.yaml
    '#/components/schemas/transition_start_output'
    """
    transitionID: str
    operation: PowerOperation

class PowerStatusGet(TypedDict, total=False):
    """
    https://github.com/Cray-HPE/hms-power-control/blob/master/api/swagger.yaml
    '#/components/schemas/power_status_get'
    """
    xname: list[str]
    powerStateFilter: PowerState
    managementStateFilter: ManagementState

class PowerStatus(TypedDict, total=False):
    """
    https://github.com/Cray-HPE/hms-power-control/blob/master/api/swagger.yaml
    '#/components/schemas/power_status'
    """
    xname: str
    powerState: PowerState
    managementState: ManagementState
    error: str | None
    supportedPowerTransitions: list[PowerOperation]
    lastUpdated: str

class PowerStatusAll(TypedDict, total=False):
    """
    https://github.com/Cray-HPE/hms-power-control/blob/master/api/swagger.yaml
    '#/components/schemas/power_status_all'
    """
    status: list[PowerStatus]
