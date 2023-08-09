#
# MIT License
#
# (C) Copyright 2021-2022 Hewlett Packard Enterprise Development LP
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
import re
from collections import defaultdict

from bos.operators.utils import requests_retry_session, PROTOCOL

SERVICE_NAME = 'cray-capmc'
CAPMC_VERSION = 'v1'
ENDPOINT = "%s://%s/capmc/%s" % (PROTOCOL, SERVICE_NAME, CAPMC_VERSION)

LOGGER = logging.getLogger('bos.operators.utils.clients.capmc')


CAPMC_HANDLED_ERROR_STRINGS = ['invalid/duplicate xnames',
                       'xnames not found',
                       'disabled or not found',
                       'xnames role blocked',
                       'xnames role blocked/not found']

class CapmcException(Exception):
    """
    Interaction with CAPMC resulted in a known failure.
    """


class CapmcTimeoutException(CapmcException):
    """
    Raised when a call to CAPMC exceeded total time to complete.
    """


def status(nodes, filtertype = 'show_all', session = None):
    """
    For a given iterable of nodes, represented by xnames, query CAPMC for
    the power status of all nodes. Return a dictionary of nodes that have
    been bucketed by status.

    Args:
      nodes (list): Nodes to get status for
      filtertype (str): Type of filter to use when sorting

    Returns:
      node_status (dict): Keys are nodes; values are different power states or errors
      failed_nodes (set): A set of the nodes that had errors
      reasons_for_failure (dict): A dictionary containing the nodes (values)
                                  suffering from errors (keys)

    Raises:
      HTTPError
      JSONDecodeError -- error decoding the CAPMC response
    """
    endpoint = '%s/get_xname_status' % (ENDPOINT)
    status_bucket = defaultdict(set)
    session = session or requests_retry_session()
    body = {'filter': filtertype,
            'xnames': list(nodes)}

    response = session.post(endpoint, json = body)
    try:
        json_response = json.loads(response.text)
    except json.JSONDecodeError as jde:
        errmsg = "CAPMC returned a non-JSON response: %s %s" % (response.text, jde)
        LOGGER.error(errmsg)
        raise

    failed_nodes = set()
    reasons_for_failure = defaultdict(list)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        if response.status_code != 400:
            LOGGER.error("Failed interacting with Cray Advanced Platform Monitoring and Control "
                     "(CAPMC): %s", err)
            LOGGER.error(response.text)
            raise
        else:
            # Handle the 400 response code
            failed_nodes, reasons_for_failure = parse_response(json_response)

    for key in ('e', 'err_msg'):
        try:
            del json_response[key]
        except KeyError:
            pass

    # Reorder JSON response into a dictionary where the nodes are the keys.
    node_status = {}
    for power_state, nodes in json_response.items():
        for node in nodes:
            node_status[node] = power_state

    return node_status, failed_nodes, reasons_for_failure


def parse_response(response):
    """
    Takes a CAPMC power action JSON response and processes it for errors.
    This function is used in booting as well as shutdown, so it has been
    abstracted to one place in order to avoid duplication.

    This function has the side effect of categorizing and logging errors
    by error condition encountered.

    ----------------------------------------------------------------------------------------
    Here is an example of what a partially successful shutdown looks like, since it isn't captured
    in the documentation particularly well. This is from the CAPMC backend.
    {"e":-1,"err_msg":"Errors encountered with 1/1 Xnames issued On","xnames":[{"xname":"x3000c0s19b3n0","e":-1,"err_msg":"NodeBMC Communication Error"}]}

    Here is CAPMC's error response format to requests to the get_xname_status endpoint when
    the CAPMC front-end encounters an error.
    They are reproduced here because, otherwise, it is only available in a Jira.

    {"e": 400,
     "err_msg": "invalid/duplicate xnames: [x1000c0s0b0n0,x1000c0s0b0n1]"}

    e: 400
    errMsg: "no request"
    errMsg: some sort of decoding error
    *    Retry with valid payload

    e: 400
    errMsg: "invalid filter string: abcd"
    *    Retry with valid filter string

    e: 400
    errMsg: "unknown status source 'abcd'"
    *    Retry with valid source or restriction removed

    e: 400
    errMsg: "invalid/duplicate xnames: [x1000c0s0b0n0]"
    errMsg: "xnames not found: [x1000c8s8b8n0]"
    errMsg: "disabled or not found: [x1000c0s0b0n0]"
    errMsg: "xnames role blocked: [x1000c0s0b0n0]"
    errMsg: "xnames role blocked/not found: [x1000c0s0b0n0]"
    *    Retry with invalid and/or duplicate names removed

    e: 400
    errMsg: "No matching components found"
    *    Retry with valid xname list or different filter options

    e: 405
    errMsg: "(PATCH) Not Allowed"
    *    Retry with GET

    e: 500
    errMsg: "Error: " + request/unmarshal error string
    errMst: "Connection to the secure store isn't ready. Can not get redfish credentials."
    *    FATAL. CAPMC is unable to talk to a required service (HSM, VAULT)
    ----------------------------------------------------------------------------------------

    This function only returns failed nodes for the 400 errors that actually provide
    failed nodes. Others, do not provide a list of failed nodes, so those errors are
    merely logged but not otherwise handled.

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
    LOGGER.error("CAPMC responded with an error response code '%s': %s",
                 response['e'], response)
    if response['e'] == -1:
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
    elif response['e'] == 400:
        for err_str in CAPMC_HANDLED_ERROR_STRINGS:
            match = re.match(fr"{err_str}: +\[([\w,]+)\]", response['err_msg'])
            if match:
                current_failed_nodes = match.group(1).split(',')
                failed_nodes |= set(current_failed_nodes)
                reasons_for_failure[err_str] = current_failed_nodes

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


def node_type(nodes):
    """
    Given a list of <nodes>, determine if they're in nid or xname format.
    """
    return ('node', 'nids') if list(nodes)[0].startswith('nid') else ('xname', 'xnames')


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
