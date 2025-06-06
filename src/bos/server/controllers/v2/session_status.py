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
SessionStatusData class
"""

from collections import defaultdict, Counter
from typing import NamedTuple

from bos.common.types.components import ComponentPhaseStr, ComponentRecord, COMPONENT_PHASE_STR
from bos.common.types.session_extended_status import (SessionExtendedStatus,
                                                      SessionExtendedStatusErrorComponents,
                                                      SessionExtendedStatusPhases,
                                                      SessionExtendedStatusTiming)
from bos.common.types.sessions import Session as SessionRecordT
from bos.common.utils import (cached_property,
                              get_current_time,
                              load_timestamp)
from bos.common.values import Phase, Status
from bos.server.controllers.v2.components import get_v2_components_data


MAX_COMPONENTS_IN_ERROR_DETAILS = 10


class _CompCounts(NamedTuple):
    phases: defaultdict[ComponentPhaseStr,int]
    successful: int
    failed: int


class SessionStatusData:
    def __init__(self, session_id: str, tenant_id: str | None, session: SessionRecordT) -> None:
        self._session_id = session_id
        self._tenant_id = tenant_id
        self._session = session

    @property
    def session_extended_status(self) -> SessionExtendedStatus:
        return SessionExtendedStatus(
            managed_components_count=self.num_components,
            phases=self.session_extended_status_phases,
            percent_staged=round(self.staged_percent, 2),
            percent_successful=round(self.successful_percent, 2),
            percent_failed=round(self.failed_percent, 2),
            error_summary=self.component_errors,
            status=self.session["status"]["status"],
            timing=self.session_extended_status_timing)

    @property
    def session_extended_status_timing(self) -> SessionExtendedStatusTiming:
        return SessionExtendedStatusTiming(start_time=self.start_time,
                                           end_time=self.end_time,
                                           duration=self.duration)

    @property
    def session_extended_status_phases(self) -> SessionExtendedStatusPhases:
        return SessionExtendedStatusPhases(
            percent_complete=round(self.complete_percent, 2),
            percent_powering_on=round(self.phase_percents[Phase.powering_on], 2),
            percent_powering_off=round(self.phase_percents[Phase.powering_off], 2),
            percent_configuring=round(self.phase_percents[Phase.configuring], 2)
        )

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def tenant_id(self) -> str | None:
        return self._tenant_id

    @property
    def session(self) -> SessionRecordT:
        return self._session

    @cached_property
    def components(self) -> list[ComponentRecord]:
        return get_v2_components_data(session=self.session_id, tenant=self.tenant_id)

    @cached_property
    def staged_components(self) -> list[ComponentRecord]:
        return get_v2_components_data(staged_session=self.session_id, tenant=self.tenant_id)

    @cached_property
    def num_components(self) -> int:
        return len(self.components) + len(self.staged_components)

    @cached_property
    def _component_phase_success_fail_counts(self) -> _CompCounts:
        phase_counts: defaultdict[ComponentPhaseStr,int] = defaultdict(int)
        num_successful = 0
        num_failed = 0
        for c in self.components:
            c_status = c.get("status")
            if not c_status:
                continue
            match c_status.get("status"):
                case Status.stable:
                    num_successful += 1
                case Status.failed:
                    num_failed += 1
            if not c.get('enabled'):
                continue
            if c_status.get("status_override") == Status.on_hold:
                continue
            if (phase := c_status.get('phase')) is not None:
                phase_counts[phase] += 1
        return _CompCounts(phases=phase_counts, successful=num_successful, failed=num_failed)

    @property
    def phase_counts(self) -> defaultdict[ComponentPhaseStr,int]:
        return self._component_phase_success_fail_counts.phases

    @property
    def successful_count(self) -> int:
        return self._component_phase_success_fail_counts.successful

    @property
    def failed_count(self) -> int:
        return self._component_phase_success_fail_counts.failed

    @property
    def complete_count(self) -> int:
        return self.successful_count + self.failed_count

    @property
    def staged_count(self) -> int:
        return len(self.staged_components)

    @cached_property
    def phase_percents(self) -> dict[ComponentPhaseStr,float]:
        phase_counts = self.phase_counts
        num_components = self.num_components
        if num_components:
            return { phase: phase_counts[phase] * 100.0 / num_components
                     for phase in COMPONENT_PHASE_STR }
        return { phase: 0.0 for phase in COMPONENT_PHASE_STR }

    @property
    def successful_percent(self) -> float:
        if self.num_components:
            return self.successful_count * 100.0 / self.num_components
        return 0.0

    @property
    def failed_percent(self) -> float:
        if self.num_components:
            return self.failed_count * 100.0 / self.num_components
        return 0.0

    @property
    def complete_percent(self) -> float:
        if self.num_components:
            return self.complete_count * 100.0 / self.num_components
        return 0.0

    @property
    def staged_percent(self) -> float:
        if self.num_components:
            return self.staged_count * 100.0 / self.num_components
        return 0.0

    @cached_property
    def component_errors(self) -> dict[str, SessionExtendedStatusErrorComponents]:
        """
        Returns a mapping from error messages, to a SessionExtendedStatusErrorComponents
        object reflecting the components with that error.
        """
        comp_errs_data: defaultdict[str, set[str]] = defaultdict(set)
        for component in self.components:
            if (error_str := component.get('error')):
                comp_errs_data[error_str].add(component['id'])
        comp_errs: dict[str, SessionExtendedStatusErrorComponents] = {}
        for error, component_ids in comp_errs_data.items():
            component_list = ','.join(
                list(component_ids)[:MAX_COMPONENTS_IN_ERROR_DETAILS])
            if len(component_ids) > MAX_COMPONENTS_IN_ERROR_DETAILS:
                component_list += '...'
            comp_errs[error] = SessionExtendedStatusErrorComponents(count=len(component_ids),
                                                                    list=component_list)
        return comp_errs

    @cached_property
    def start_time(self) -> str:
        return self.session['status']['start_time']

    @cached_property
    def end_time(self) -> str|None:
        return self.session['status'].get('end_time')

    @property
    def duration(self) -> str:
        if (end_time := self.end_time):
            return str(load_timestamp(end_time) - load_timestamp(self.start_time))
        return str(get_current_time() - load_timestamp(self.start_time))
