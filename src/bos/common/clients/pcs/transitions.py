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
from collections.abc import Iterable
import logging
from typing import cast

from .base import BasePcsEndpoint
from .exceptions import PowerControlComponentsEmptyException, PowerControlSyntaxException
from .types import (is_power_operation,
                    PowerOperation,
                    ReservedLocation,
                    TransitionCreate,
                    TransitionStartOutput)

LOGGER = logging.getLogger(__name__)


class TransitionsEndpoint(BasePcsEndpoint):
    ENDPOINT = 'transitions'

    def _transition_create(self,
                           xnames: Iterable[str],
                           operation: PowerOperation,
                           task_deadline_minutes: int|None,
                           deputy_key: str|None) -> TransitionStartOutput:
        """
        Interact with PCS to create a request to transition one or more xnames. The transition
        operation indicates what the desired operation should be, which is a string value
        containing one or more of the supported transition names for the given hardware, e.g. 'on',
        'off', or 'force-off'.

        Once created, one of two responses are returned. A 2XX response results in a
        transition_start_output object, or, an invalid request results in a 4XX and subsequent
        raised PCS exception.

        Args:
            xnames: an iterable of xnames
            operation: A string/enum for what the nodes should transition to
            task_deadline_minutes: How long should PCS operate on the nodes to bring them to
              complete the operation; typecast to an integer value.
            deputy_key: An optional string value that can be used to further handle instructing PCS
              to perform state transitions on behalf of a known existing reservation.
            session: An already existing session to use with PCS, if any

        Returns:
            A transition_start_output object, which is a record for the transition that was
            created. The most important field of which is the 'transitionID' value, which allows
            subsequent follow-on to the created request.

        Raises:
            PowerControlException: Any non-nominal response from PCS, typically as a result of an
              unexpected payload response, or a failure to create a transition record.
            PowerControlComponentsEmptyException: No xnames specified
        """
        if not xnames:
            raise PowerControlComponentsEmptyException(
                f"_transition_create called with no xnames! (operation={operation})"
            )
        if not is_power_operation(operation):
            raise PowerControlSyntaxException(
                f"Operation '{operation}' is not supported or implemented."
            )
        params: TransitionCreate = {'location': [], 'operation': operation}
        if task_deadline_minutes:
            params['taskDeadlineMinutes'] = int(task_deadline_minutes)
        for xname in xnames:
            reserved_location: ReservedLocation = {'xname': xname}
            if deputy_key:
                reserved_location['deputyKey'] = deputy_key
            params['location'].append(reserved_location)
        return cast(TransitionStartOutput, self.post(json=params))

    def power_on(self, xnames: Iterable[str], task_deadline_minutes: int|None=1,
                 deputy_key: str|None=None) -> TransitionStartOutput:
        """
        Wrapper for calling _transition_create to power on a node
        """
        return self._transition_create(operation='On', xnames=xnames,
                                       task_deadline_minutes=task_deadline_minutes,
                                       deputy_key=deputy_key)


    def soft_off(self, xnames: Iterable[str], task_deadline_minutes: int|None=1,
                 deputy_key: str|None=None) -> TransitionStartOutput:
        """
        Wrapper for calling _transition_create to soft power off a node
        """
        return self._transition_create(operation='Soft-Off', xnames=xnames,
                                       task_deadline_minutes=task_deadline_minutes,
                                       deputy_key=deputy_key)

    def force_off(self, xnames: Iterable[str], task_deadline_minutes: int|None=1,
                  deputy_key: str|None=None) -> TransitionStartOutput:
        """
        Wrapper for calling _transition_create to force power off a node
        """
        return self._transition_create(operation='Force-Off', xnames=xnames,
                                       task_deadline_minutes=task_deadline_minutes,
                                       deputy_key=deputy_key)
