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
from typing import Literal, Required, TypedDict, cast, get_args

#/components/schemas/V2ComponentPhase
ComponentPhaseStr = Literal['powering_on', 'powering_off', 'configuring', '']

COMPONENT_PHASE_STR: frozenset[ComponentPhaseStr] = frozenset(get_args(ComponentPhaseStr))

ComponentStatusStr = Literal['power_on_pending', 'power_on_called', 'power_off_pending',
                          'power_off_gracefully_called', 'power_off_forcefully_called',
                          'configuring', 'stable', 'failed', 'on_hold']

class ComponentStatus(TypedDict, total=False):
    """
    #/components/schemas/V2ComponentStatus
    """
    phase: ComponentPhaseStr
    status: str
    status_override: str

class BootArtifacts(TypedDict, total=False):
    """
    #/components/schemas/V2BootArtifacts
    """
    kernel: Required[str]
    kernel_parameters: Required[str]
    initrd: Required[str]
    timestamp: str

ComponentActionStr = Literal['actual_state_cleanup', 'apply_staged', 'newly_discovered',
                             'powering_off_forcefully', 'powering_off_gracefully', 'powering_on',
                             'session_setup']

class ComponentLastAction(TypedDict, total=False):
    """
    #/components/schemas/V2ComponentLastAction
    """
    action: ComponentActionStr
    failed: bool
    last_updated: str

ComponentEventStatsAttemptFields = Literal['power_on_attempts',
                                           'power_off_graceful_attempts',
                                           'power_off_forceful_attempts']

# #/components/schemas/V2ComponentEventStats
type ComponentEventStats = dict[ComponentEventStatsAttemptFields, int]

class BaseComponentState(TypedDict, total=False):
    """
    Common fields found in actual state, desired state, and staged state
    """
    boot_artifacts: BootArtifacts
    last_updated: str

class ComponentActualState(BaseComponentState, TypedDict, total=False):
    """
    #/components/schemas/V2ComponentActualState
    """
    bss_token: str

class ComponentDesiredState(BaseComponentState, TypedDict, total=False):
    """
    #/components/schemas/V2ComponentDesiredState
    """
    bss_token: str
    configuration: str

class ComponentStagedState(BaseComponentState, TypedDict, total=False):
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

class RequiredIdField(TypedDict, total=True):
    id: str

class OptionalIdField(TypedDict, total=False):
    id: str

class BaseComponentData(TypedDict, total=False):
    actual_state: ComponentActualState
    desired_state: ComponentDesiredState
    enabled: bool
    error: str
    event_stats: ComponentEventStats
    last_action: ComponentLastAction
    retry_policy: int
    session: str
    staged_state: ComponentStagedState
    status: ComponentStatus

CompDictFields = Literal["actual_state", "desired_state", "staged_state", "last_action",
                         "event_stats", "status"]

COMP_DICT_FIELDS: frozenset[CompDictFields] = frozenset(get_args(CompDictFields))

class ComponentData(BaseComponentData, OptionalIdField):
    """
    #/components/schemas/V2Component
    """

class ComponentRecord(BaseComponentData, RequiredIdField):
    """
    #/components/schemas/V2ComponentWithId
    """

class ComponentUpdateIdFilter(TypedDict, total=False):
    """
    #/components/schemas/V2ComponentsFilterByIds
    """
    ids: Required[str]
    session: Literal[""] | None

class ComponentUpdateSessionFilter(TypedDict, total=True):
    """
    #/components/schemas/V2ComponentsFilterBySession
    """
    ids: Literal[""] | None
    session: Required[str]

class ComponentUpdateFilter(TypedDict, total=True):
    """
    #/components/schemas/V2ComponentsUpdate
    """
    patch: ComponentData
    filters: ComponentUpdateIdFilter | ComponentUpdateSessionFilter

def update_component_record(
    record: ComponentRecord, new_record: ComponentData | ComponentRecord
) -> None:
    """
    Perform in-place update of current record using data from new record.
    """
    # Make a copy, to avoid changing new_record in place
    # Cast it as ComponentData, since that will just have the effect of making the 'id' field
    # optional
    new_rec_copy = cast(ComponentData, copy.deepcopy(new_record))

    # Pop the 'id' field, if present
    new_rec_copy.pop("id", None)

    for field in COMP_DICT_FIELDS.intersection(new_rec_copy):

        if field not in record:
            record[field] = new_rec_copy.pop(field)
            continue

        # We have to break out the fields into separate cases, to help out poor mypy
        match field:
            case "actual_state":
                _update_component_state(record["actual_state"], new_rec_copy.pop("actual_state"))
            case "desired_state":
                _update_component_state(record["desired_state"], new_rec_copy.pop("desired_state"))
            case "staged_state":
                _update_component_state(record["staged_state"], new_rec_copy.pop("staged_state"))
            case "last_action":
                record["last_action"].update(new_rec_copy.pop("last_action"))
            case "event_stats":
                record["event_stats"].update(new_rec_copy.pop("event_stats"))
            case "status":
                record["status"].update(new_rec_copy.pop("status"))

    # The remaining fields can be merged the old-fashioned way
    record.update(new_rec_copy)

class ApplyStagedComponents(TypedDict, total=False):
    """
    #/components/schemas/V2ApplyStagedComponents
    """
    xnames: list[str]

class ApplyStagedStatus(TypedDict, total=False):
    """
    #/components/schemas/V2ApplyStagedStatus
    """
    failed: list[str]
    ignored: list[str]
    succeeded: list[str]

class GetComponentsFilter(TypedDict, total=False):
    """
    Filters that can be specified when doing a GET to /v2/components
    """
    ids: str
    session: str
    staged_session: str
    enabled: bool
    phase: ComponentPhaseStr
    status: str
    start_after_id: str
    page_size: int

class ComponentBulkUpdateParams(TypedDict, total=False):
    """
    Parameters that can be specified when doing a bulk component patch
    """
    skip_bad_ids: bool
