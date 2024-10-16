#
# MIT License
#
# (C) Copyright 2023-2024 Hewlett Packard Enterprise Development LP
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

# This client wrapper is derived from the PCS source spec, as provided by:
#       https://github.com/Cray-HPE/hms-power-control/blob/develop/api/swagger.yaml

import logging
import json
from typing import Iterable, Optional

from collections import defaultdict

from requests import HTTPError
from requests import Session as RequestsSession

from bos.common.types import JsonDict
from bos.common.utils import compact_response_text, requests_retry_session, PROTOCOL

SERVICE_NAME = 'cray-power-control'
POWER_CONTROL_VERSION = 'v1'
ENDPOINT = f"{PROTOCOL}://{SERVICE_NAME}"
POWER_STATUS_ENDPOINT = f'{ENDPOINT}/power-status'
TRANSITION_ENDPOINT = f"{ENDPOINT}/transitions"

LOGGER = logging.getLogger('bos.operators.utils.clients.pcs')


class PowerControlException(Exception):
    """
    Interaction with PCS resulted in a known failure.
    """


class PowerControlSyntaxException(Exception):
    """
    A class of error raised when interacting with PCS in an unsupported way.
    """


class PowerControlTimeoutException(PowerControlException):
    """
    Raised when a call to PowerControl exceeded total time to complete.
    """


class PowerControlComponentsEmptyException(Exception):
    """
    Raised when one of the PCS utility functions that requires a non-empty
    list of components is passed an empty component list. This will only
    happen in the case of a programming bug.

    This exception is not raised for functions that require a node list
    but that are able to return a sensible object to the caller that
    indicates nothing has been done. For example, the status function.
    This exception is instead used for functions that will fail if they run
    with an empty node list, but which cannot return an appropriate
    "no-op" value to the caller.
    """

def _power_status(xname: Optional[str]=None, power_state_filter: Optional[str]=None,
                  management_state_filter: Optional[str]=None,
                  session: Optional[RequestsSession]=None) -> JsonDict:
    """
    This is the one to one implementation to the underlying power control get query.
    For reasons of compatibility with existing calls into older power control APIs,
    existing functions call into this function to preserve the existing functionality
    already implemented.

    Users may specify one of three filters, and a power_status_all (PCS defined schema)
    is returned. Users may elect to use a previously generated session in order to query
    the results. If not, the default requests retry session will be generated.

    Per the spec, a power_status_all is returned. power_status_all is an array of power
    statuses.
    """
    session = session or requests_retry_session()
    params = {}
    if xname:
        params['xname'] = xname
    if power_state_filter:
        assert power_state_filter.lower() in set(['on','off','undefined'])
        params['powerStateFilter'] = power_state_filter.lower()
    if management_state_filter:
        assert management_state_filter in set(['available', 'unavailable'])
        params['managementStateFilter'] = management_state_filter.lower()
    # PCS added the POST option for this endpoint in app version 2.3.0
    # (chart versions 2.0.8 and 2.1.5)
    LOGGER.debug("POST %s with body=%s", POWER_STATUS_ENDPOINT, params)
    response = session.post(POWER_STATUS_ENDPOINT, json=params)
    LOGGER.debug("Response status code=%d, reason=%s, body=%s", response.status_code,
                 response.reason, compact_response_text(response.text))
    try:
        response.raise_for_status()
        if not response.ok:
            raise PowerControlException(f"Non-2XX response ({response.status_code}) to "
                                        f"power_status query; {response.reason} "
                                        f"{compact_response_text(response.text)}")
    except HTTPError as err:
        raise PowerControlException(err) from err
    try:
        return response.json()
    except json.JSONDecodeError as jde:
        raise PowerControlException(jde) from jde

def status(nodes: Iterable[str], session: Optional[RequestsSession]=None,
           **kwargs) -> dict[str, set[str]]:
    """
    For a given iterable of nodes, represented by xnames, query PCS for
    the power status. Return a dictionary of nodes that have
    been bucketed by status.

    Args:
      nodes (list): Nodes to get status for
      session (session object): An already instantiated session
      kwargs: Any additional args used for filtering when calling _power_status.
        This can be useful if you want to limit your search to only available or unavailable nodes,
        and allows a more future-proof way of handling arguments to PCS as a catch-all parameter.

    Returns:
      status_dict (dict): Keys are different states; values are a literal set of nodes.
        Nodes with errors associated with them are saved with the error value as a
        status key.

    Raises:
      PowerControlException: Any non-nominal response from PCS.
      JSONDecodeError: Error decoding the PCS response
    """
    status_bucket = defaultdict(set)
    if not nodes:
        LOGGER.warning("status called without nodes; returning without action.")
        return status_bucket
    session = session or requests_retry_session()
    power_status_all = _power_status(xname=list(nodes), session=session, **kwargs)
    for power_status_entry in power_status_all['status']:
        # If the returned xname has an error, it itself is the status regardless of
        # what the powerState field suggests. This is a major departure from how CAPMC
        # handled errors.
        xname = power_status_entry.get('xname', '')
        if power_status_entry['error']:
            status_bucket[power_status_entry['error']].add(xname)
            continue
        power_status = power_status_entry.get('powerState', '').lower()
        if not all([power_status, xname]):
            continue
        status_bucket[power_status].add(xname)
    return status_bucket

def node_to_powerstate(nodes: Iterable[str], session: Optional[RequestsSession]=None,
                       **kwargs) -> dict[str,str]
    """
    For an iterable of nodes <nodes>; return a dictionary that maps to the current power state for
    the node in question.
    """
    power_states = {}
    if not nodes:
        LOGGER.warning("node_to_powerstate called without nodes; returning without action.")
        return power_states
    session = session or requests_retry_session()
    status_bucket = status(nodes, session, **kwargs)
    for pstatus, nodeset in status_bucket.items():
        for node in nodeset:
            power_states[node] = pstatus
    return power_states

def _transition_create(xnames: Iterable[str], operation: str,
                       task_deadline_minutes: Optional[int]=None, deputy_key: Optional[str]=None,
                       session: Optional[RequestsSession]=None) -> JsonDict:
    """
    Interact with PCS to create a request to transition one or more xnames. The transition
    operation indicates what the desired operation should be, which is a string value containing
    one or more of the supported transition names for the given hardware, e.g. 'on', 'off', or
    'force-off'.

    Once created, one of two responses are returned. A 2XX response results in a
    transition_start_output object, or, an invalid request results in a 4XX and subsequent
    raised PCS exception.

    Args:
        xnames: an iterable of xnames
        operation: A string/enum for what the nodes should transition to
        task_deadline_minutes: How long should PCS operate on the nodes to bring them to complete
          the operation; typecast to an integer value.
        deputy_key: An optional string value that can be used to further handle instructing PCS
          to perform state transitions on behalf of a known existing reservation.
        session: An already existing session to use with PCS, if any

    Returns:
        A transition_start_output object, which is a record for the transition that was created.
        The most important field of which is the 'transitionID' value, which allows subsequent
        follow-on to the created request.

    Raises:
        PowerControlException: Any non-nominal response from PCS, typically as a result of an
          unexpected payload response, or a failure to create a transition record.
        PowerControlComponentsEmptyException: No xnames specified
    """
    if not xnames:
        raise PowerControlComponentsEmptyException(
                f"_transition_create called with no xnames! (operation={operation})")
    session = session or requests_retry_session()
    try:
        assert operation in {'On', 'Off', 'Soft-Off', 'Soft-Restart', 'Hard-Restart', 'Init',
                             'Force-Off'}
    except AssertionError as err:
        raise PowerControlSyntaxException(
                f"Operation '{operation}' is not supported or implemented.") from err
    params = {'location': [], 'operation': operation}
    if task_deadline_minutes:
        params['taskDeadlineMinutes'] = int(task_deadline_minutes)
    for xname in xnames:
        reserved_location = {'xname': xname}
        if deputy_key:
            reserved_location['deputyKey'] = deputy_key
        params['location'].append(reserved_location)
    LOGGER.debug("POST %s with body=%s", TRANSITION_ENDPOINT, params)
    response = session.post(TRANSITION_ENDPOINT, json=params)
    LOGGER.debug("Response status code=%d, reason=%s, body=%s", response.status_code,
                 response.reason, compact_response_text(response.text))
    try:
        response.raise_for_status()
        if not response.ok:
            raise PowerControlException(f"Non-2XX response ({response.status_code}) to "
                                        f"{operation} power transition creation; "
                                        f"{response.reason} "
                                        f"{compact_response_text(response.text)}")

    except HTTPError as err:
        raise PowerControlException(err) from err
    try:
        return response.json()
    except json.decoder.JSONDecodeError as jde:
        raise PowerControlException(jde) from jde


def power_on(nodes: Iterable[str], session: Optional[RequestsSession]=None,
             task_deadline_minutes: Optional[int]=1, **kwargs) -> JsonDict:
    """
    Sends a request to PCS for transitioning nodes in question to a powered on state.
    Returns: A JSON parsed object response from PCS, which includes the created request ID.
    """
    if not nodes:
        raise PowerControlComponentsEmptyException("power_on called with no nodes!")
    session = session or requests_retry_session()
    return _transition_create(xnames=nodes, operation='On',
                              task_deadline_minutes=task_deadline_minutes,
                              session=session, **kwargs)

def power_off(nodes: Iterable[str], session: Optional[RequestsSession]=None,
              task_deadline_minutes=: Optional[int]=1, **kwargs) -> JsonDict:
    """
    Sends a request to PCS for transitioning nodes in question to a powered off state (graceful).
    Returns: A JSON parsed object response from PCS, which includes the created request ID.
    """
    if not nodes:
        raise PowerControlComponentsEmptyException("power_off called with no nodes!")
    session = session or requests_retry_session()
    return _transition_create(xnames=nodes, operation='Off',
                              task_deadline_minutes=task_deadline_minutes,
                              session=session, **kwargs)

def soft_off(nodes: Iterable[str], session: Optional[RequestsSession]=None,
             task_deadline_minutes: Optional[int]=1, **kwargs) -> JsonDict:
    """
    Sends a request to PCS for transitioning nodes in question to a powered off state (graceful).
    Returns: A JSON parsed object response from PCS, which includes the created request ID.
    """
    if not nodes:
        raise PowerControlComponentsEmptyException("soft_off called with no nodes!")
    session = session or requests_retry_session()
    return _transition_create(xnames=nodes, operation='Soft-Off',
                              task_deadline_minutes=task_deadline_minutes,
                              session=session, **kwargs)

def force_off(nodes: Iterable[str], session: Optional[RequestsSession]=None,
              task_deadline_minutes: Optional[int]=1, **kwargs) -> JsonDict:
    """
    Sends a request to PCS for transitioning nodes in question to a powered off state (forceful).
    Returns: A JSON parsed object response from PCS, which includes the created request ID.
    """
    if not nodes:
        raise PowerControlComponentsEmptyException("force_off called with no nodes!")
    session = session or requests_retry_session()
    return _transition_create(xnames=nodes, operation='Force-Off',
                              task_deadline_minutes=task_deadline_minutes,
                              session=session, **kwargs)
