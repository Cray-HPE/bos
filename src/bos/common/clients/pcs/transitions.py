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
import logging

from .base import BasePcsEndpoint
from .exceptions import PowerControlComponentsEmptyException, PowerControlSyntaxException

LOGGER = logging.getLogger(__name__)


class TransitionsEndpoint(BasePcsEndpoint):
    ENDPOINT = 'transitions'

    def transition_create(self,
                          xnames,
                          operation,
                          task_deadline_minutes=None,
                          deputy_key=None):
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
        try:
            assert operation in {
                'On', 'Off', 'Soft-Off', 'Soft-Restart', 'Hard-Restart',
                'Init', 'Force-Off'
            }
        except AssertionError as err:
            raise PowerControlSyntaxException(
                f"Operation '{operation}' is not supported or implemented."
            ) from err
        params = {'location': [], 'operation': operation}
        if task_deadline_minutes:
            params['taskDeadlineMinutes'] = int(task_deadline_minutes)
        for xname in xnames:
            reserved_location = {'xname': xname}
            if deputy_key:
                reserved_location['deputyKey'] = deputy_key
            params['location'].append(reserved_location)
        return self.post(json=params)

    def power_on(self, nodes, task_deadline_minutes=1, **kwargs):
        """
        Sends a request to PCS for transitioning nodes in question to a powered on state.
        Returns: A JSON parsed object response from PCS, which includes the created request ID.
        """
        if not nodes:
            raise PowerControlComponentsEmptyException(
                "power_on called with no nodes!")
        return self.transition_create(
            xnames=nodes,
            operation='On',
            task_deadline_minutes=task_deadline_minutes,
            **kwargs)

    def power_off(self, nodes, task_deadline_minutes=1, **kwargs):
        """
        Sends a request to PCS for transitioning nodes in question to a powered off state
        (graceful).
        Returns: A JSON parsed object response from PCS, which includes the created request ID.
        """
        if not nodes:
            raise PowerControlComponentsEmptyException(
                "power_off called with no nodes!")
        return self.transition_create(
            xnames=nodes,
            operation='Off',
            task_deadline_minutes=task_deadline_minutes,
            **kwargs)

    def soft_off(self, nodes, task_deadline_minutes=1, **kwargs):
        """
        Sends a request to PCS for transitioning nodes in question to a powered off state
        (graceful).
        Returns: A JSON parsed object response from PCS, which includes the created request ID.
        """
        if not nodes:
            raise PowerControlComponentsEmptyException(
                "soft_off called with no nodes!")
        return self.transition_create(
            xnames=nodes,
            operation='Soft-Off',
            task_deadline_minutes=task_deadline_minutes,
            **kwargs)

    def force_off(self, nodes, task_deadline_minutes=1, **kwargs):
        """
        Sends a request to PCS for transitioning nodes in question to a powered off state
        (forceful).
        Returns: A JSON parsed object response from PCS, which includes the created request ID.
        """
        if not nodes:
            raise PowerControlComponentsEmptyException(
                "force_off called with no nodes!")
        return self.transition_create(
            xnames=nodes,
            operation='Force-Off',
            task_deadline_minutes=task_deadline_minutes,
            **kwargs)
