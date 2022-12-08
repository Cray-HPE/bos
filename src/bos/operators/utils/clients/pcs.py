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
import requests
import json
from collections import defaultdict

from bos.operators.utils import requests_retry_session, PROTOCOL

SERVICE_NAME = 'power-control'
POWER_CONTROL_VERSION = 'v1'
ENDPOINT = "%s://%s//%s" % (PROTOCOL, SERVICE_NAME, POWER_CONTROL_VERSION)
TRANSITION_ENDPOINT = "%s/transitions"

LOGGER = logging.getLogger('bos.operators.utils.clients.pcs')


class PowerControlException(Exception):
    """
    Interaction with CAPMC resulted in a known failure.
    """


class PowerControlSyntaxException(Exception):
    """
    A class of error raised when interacting with PCS in an unsupported way.
    """


class PowerControlTimeoutException(PowerControlException):
    """
    Raised when a call to PowerControl exceeded total time to complete.
    """


def _power_status(xname=None, power_state_filter=None, management_state_filter=None,
                  session=None):
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
    endpoint = '%s/power-status' % (ENDPOINT)
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
    response = session.get(endpoint, params=params)
    try:
        response.raise_for_status()
        if not response.ok:
            raise PowerControlException("Non-2XX response to power_status query: response %s: %s" %(response.status_c))
    except requests.exceptions.HTTPError as err:
        raise PowerControlException(err) from err
    try:
        power_status_all = response.json()
    except json.JSONDecodeError as jde:
        raise PowerControlException(jde) from jde
    return power_status_all


def status(nodes, session=None, **kwargs):
    """
    For a given iterable of nodes, represented by xnames, query PCS for
    the power status. Return a dictionary of nodes that have
    been bucketed by status.

    Args:
      nodes (list): Nodes to get status for
      session (session object): An already instantiated session
      kwargs: Any additional args used for filtering when calling _power_status.
        This can be useful if you want to limit your search to only available or unavailable nodes,
        and allows a more future proof way of handling arguments to PCS as a catch-all parameter.

    Returns:
      status_dict (dict): Keys are different states; values are a literal set of nodes.
        Nodes with errors associated with them are saved with the error value as a
        status key.

    Raises:
      PowerControlException: Any non-nominal response from PCS.
      JSONDecodeError: Error decoding the PCS response
    """
    session = session or requests_retry_session()
    power_status_all = _power_status(xname=list(nodes), session=session, **kwargs)
    status_bucket = defaultdict(set)
    for power_status in power_status_all:
        # IF the returned xname has an error, it itself is the status regardless of
        # what the powerState field suggests.
        xname = power_status['xname']
        if power_status['error']:
            status_bucket[power_status['error']].add(xname)
            continue
        status_bucket['powerState'].add(xname)
    return status_bucket

def _transition_create(xnames, operation, task_deadline_minutes=None, deputy_key=None, session=None):
    """
    Interact with PCS to create a request to transition one or more xnames. The transition
    operation indicates what the desired operation should be, which is a string value containing
    one or more of the supported transition names for the given hardware, e.g. 'on', 'off', or 'force-off'.

    Once created, one of two responses are returned. A 2XX response results in a transition_start_output
    object, or, an invalid request results in a 4XX and subsequent raised PCS exception.

    Args:
        xnames: an iteratble of xnames
        operation: A string/enum for what the nodes should transition to
        task_deadline_minutes: How long should PCS operate on the nodes to bring them to complete the operation;
          typecast to an integer value.
        deputy_key: An optional string value that can be used to further handle instructing PCS to perform
          state transitions on behalf of a known existing reservation.
        session: An already existing session to use with PCS, if any

    Returns:
        A transition_start_output object, which is a record for the transition that was created. The most important
        field of which is the 'transitionID' value, which allows subsequent follow-on to the created request.

    Raises:
        PowerControlException: Any non-nominal response from PCS, typically as a result of an unexpected payload
          response, or a failure to create a transition record.
    """
    session = session or requests_retry_session()
    operation = operation.lower()
    try:
        assert operation in set('on', 'off', 'soft-off', 'soft-restart', 'hard-restart', 'init', 'force_off')
    except AssertionError:
        raise PowerControlSyntaxException("Operation '%s' is not supported or implemented." %(operation))
    params = {'location': []}
    if task_deadline_minutes:
        params['taskDeadlineMinutes'] = int(task_deadline_minutes)
    for xname in xnames:
        reserved_location = {'xname': xname}
        if deputy_key:
            reserved_location['deputyKey'] = deputy_key
        params['location'].append(reserved_location)
    response = session.post(TRANSITION_ENDPOINT, json=params)
    try:
        response.raise_for_status()
        if not response.ok:
            raise PowerControlException("Non-2XX response to power_status query: response %s: %s" %(response.status_c))
    except requests.exceptions.HTTPError as err:
        raise PowerControlException(err) from err
    try:
        transition_start_output = response.json()
    except json.decoder.JSONDecodeError as jde:
        raise PowerControlException(jde) from jde
    return transition_start_output

def parse_response(response):
    """
    Takes a CAPMC power action JSON response and process it for partial
    communication errors. This function is used in booting as well as
    shutdown, so it has been abstracted to one place in order to avoid
    duplication.

    This function has the side effect of categorizing and logging errors
    by error condition encountered.

    # Here is an example of what a partially successful shutdown looks like, since it isn't captured
    # in the documentation particularly well.
    # {"e":-1,"err_msg":"Errors encountered with 1/1 Xnames issued On","xnames":[{"xname":"x3000c0s19b3n0","e":-1,"err_msg":"NodeBMC Communication Error"}]}

    This function returns a set of nodes (in our case, almost always, xnames)
    that did not receive the requested call for action. Upstream calling
    functions may decide what to do with that information.

    Returns
      failed_nodes (set): A set of the nodes that failed
      reasons_for_failure (dict): A dictionary containing the nodes (values)
                                  suffering from errors (keys)
    """
    failed_nodes = set()
    reasons_for_failure = defaultdict(list)
    if 'e' not in response or response['e'] == 0:
        # All nodes received the requested action; happy path
        return failed_nodes, reasons_for_failure
    LOGGER.warning("CAPMC responded with e code '%s'", response['e'])
    if 'err_msg' in response:
        LOGGER.warning("err_msg: %s", response['err_msg'])
    if 'undefined' in response:
        failed_nodes |= set(response['undefined'])
    if 'xnames' in response:
        for xname_dict in response['xnames']:
            xname = xname_dict['xname']
            err_msg = xname_dict['err_msg']
            reasons_for_failure[err_msg].append(xname)
        # Report back all reasons for failure
        for err_msg, nodes in sorted(reasons_for_failure.items()):
            node_count = len(nodes)
            if node_count <= 5:
                LOGGER.warning("\t%s: %s", err_msg, ', '.join(sorted(nodes)))
            else:
                LOGGER.warning("\t%s: %s nodes", err_msg, node_count)
        # Collect all failed nodes.
        for nodes in reasons_for_failure.values():
            failed_nodes |= set(nodes)
    return failed_nodes, reasons_for_failure


def power(nodes, state, force = True, session = None, cont = True, reason = "BOS: Powering nodes"):
    """
    Sets a node to a power state using CAPMC; returns a set of nodes that were unable to achieve
    that state.

    It is important to note that CAPMC will respond with a 200 response, even if it fails
    to power the node to the desired state.

    Args:
      nodes (list): Nodes to power on
      state (string): Power state: off or on
      force (bool): Should the power off be forceful (True) or not forceful (False)
      session (Requests.session object): A Requests session instance
      cont (bool): Request that the API continues the requested operation when one
        or more of the requested components fails their action.

    Returns:
      failed (set): the nodes that failed to enter the desired power state
      boot_errors (dict): A dictionary containing the nodes (values)
                          suffering from errors (keys)

    Raises:
      ValueError: if state is neither 'off' nor 'on'
    """
    if not nodes:
        LOGGER.warning("power called without nodes; returning without action.")
        return set(), {}

    valid_states = ["off", "on"]
    state = state.lower()
    if state not in valid_states:
        raise ValueError("State must be one of {} not {}".format(valid_states, state))

    session = session or requests_retry_session()
    prefix, output_format = node_type(nodes)
    power_endpoint = '%s/%s_%s' % (ENDPOINT, prefix, state)

    if state == "on":
        json_response = call(power_endpoint, nodes, output_format, cont, reason)
    elif state == "off":
        json_response = call(power_endpoint, nodes, output_format, cont, reason, force = force)

    failed_nodes, errors = parse_response(json_response)
    return failed_nodes, errors

def call(endpoint, nodes, node_format = 'xnames', cont = True, reason = "None given", session = None, **kwargs):
    '''
    This function makes a call to the Cray Advanced Platform Monitoring and Control (CAPMC)
    Args:
        endpoint: CAPMC endpoint to interact with
        nodes: The nodes to ask CAPMC to operate on
        node_format: Either xnames or ids;  The payload needs to have the correct key
    kwargs**:
        Additional command line arguments that can be passed in by resulting calls for additional
        flexibility when interacting with CAPMC; these are appended in a key:value sense
        to the payload body.
    Raises:
        requests.exceptions.HTTPError -- when an HTTP error occurs

    Returns: The parsed JSON response from the JSON based API.
    '''
    payload = {'reason': reason,
               node_format: list(nodes),
               'continue': cont}
    session = session or requests_retry_session()
    if kwargs:
        payload.update(kwargs)
    try:
        resp = session.post(endpoint, verify = False, json = payload)
        resp.raise_for_status()
    except requests.exceptions.HTTPError as err:
        LOGGER.error("Failed interacting with Cray Advanced Platform Monitoring and Control "
                     "(CAPMC): %s", err)
        LOGGER.error(resp.text)
        raise
    try:
        return json.loads(resp.text)
    except json.JSONDecodeError as jde:
        raise CapmcException("Non-json response from CAPMC: %s" % (resp.text)) from jde
