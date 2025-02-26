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

"""
Type annotation definitions for BOS components
"""
import copy
from typing import Required, TypedDict

from .general import BosDataRecord

class ComponentStatus(TypedDict, total=False):
    """
    #/components/schemas/V2ComponentStatus
    """
    phase: str
    status: str
    status_override: str

class BootArtifacts(TypedDict, total=True):
    """
    #/components/schemas/V2BootArtifacts
    """
    kernel: str
    kernel_parameters: str
    initrd: str

class TimestampedBootArtifacts(BosDataRecord, BootArtifacts, total=True):
    """
    When storing the boot artifacts in the database, there is an additional timestamp field
    """
    timestamp: str

class ComponentLastAction(TypedDict, total=False):
    """
    #/components/schemas/V2ComponentLastAction
    """
    action: str
    failed: bool
    last_updated: str

class ComponentEventStats(TypedDict, total=False):
    """
    #/components/schemas/V2ComponentEventStats
    """
    power_on_attempts: int
    power_off_graceful_attempts: int
    power_off_forceful_attempts: int

class BaseComponentState(TypedDict, total=False):
    """
    Common fields found in actual state, desired state, and staged state
    """
    boot_artifacts: BootArtifacts
    last_updated: str

class ComponentActualState(BaseComponentState, total=False):
    """
    #/components/schemas/V2ComponentActualState
    """
    bss_token: str

class ComponentDesiredState(BaseComponentState, total=False):
    """
    #/components/schemas/V2ComponentDesiredState
    """
    bss_token: str
    configuration: str

class ComponentStagedState(BaseComponentState, total=False):
    """
    #/components/schemas/V2ComponentStagedState
    """
    configuration: str
    session: str

def _update_component_state[C: (ComponentActualState,
                                ComponentDesiredState,
                                ComponentStagedState)](record: C, new_record_copy: C) -> None:
    """
    Perform in-place update of current record using data
    from new record. This is only called by update_component_record
    """
    if "boot_artifacts" in new_record_copy:
        new_data = new_record_copy.pop("boot_artifacts")
        if "boot_artifacts" in record:
            record["boot_artifacts"].update(new_data)
        else:
            record["boot_artifacts"] = new_data

    # The remaining fields can be merged the old-fashioned way
    record.update(new_record_copy)

class ComponentRecord(BosDataRecord, total=False):
    """
    #/components/schemas/V2Component
    """
    actual_state: ComponentActualState
    desired_state: ComponentDesiredState
    enabled: bool
    error: str
    event_stats: ComponentEventStats
    id: Required[str]
    last_action: ComponentLastAction
    retry_policy: int
    session: str
    staged_state: ComponentStagedState
    status: ComponentStatus

def update_component_record(record: ComponentRecord, new_record: ComponentRecord) -> None:
    """
    Perform in-place update of current record using data from new record.
    """
    # Make a copy, to avoid changing new_record in place
    new_record_copy = copy.deepcopy(new_record)

    # Merge the state dicts -- this is not done in a loop because mypy gets confused keeping track
    # of string literal values in loops
    if "actual_state" in new_record_copy:
        if "actual_state" in record:
            _update_component_state(record["actual_state"], new_record_copy.pop("actual_state"))
        else:
            record["actual_state"] = new_record_copy.pop("actual_state")

    if "desired_state" in new_record_copy:
        if "desired_state" in record:
            _update_component_state(record["desired_state"], new_record_copy.pop("desired_state"))
        else:
            record["desired_state"] = new_record_copy.pop("desired_state")

    if "staged_state" in new_record_copy:
        if "staged_state" in record:
            _update_component_state(record["staged_state"], new_record_copy.pop("staged_state"))
        else:
            record["staged_state"] = new_record_copy.pop("staged_state")

    # Next, merge the regular sub-dicts -- this is also not done in a loop, for the same reason as above
    if "last_action" in new_record_copy:
        if "last_action" in record:
            record["last_action"].update(new_record_copy.pop("last_action"))
        else:
            record["last_action"] = new_record_copy.pop("last_action")

    if "event_stats" in new_record_copy:
        if "event_stats" in record:
            record["event_stats"].update(new_record_copy.pop("event_stats"))
        else:
            record["event_stats"] = new_record_copy.pop("event_stats")

    if "status" in new_record_copy:
        if "status" in record:
            record["status"].update(new_record_copy.pop("status"))
        else:
            record["status"] = new_record_copy.pop("status")

    # The remaining fields can be merged the old-fashioned way
    record.update(new_record_copy)
