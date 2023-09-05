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
from abc import ABC, abstractmethod
from collections import defaultdict

from bos.operators.utils import requests_retry_session, PROTOCOL

SERVICE_NAME = 'cray-capmc'
CAPMC_VERSION = 'v1'
ENDPOINT = "%s://%s/capmc/%s" % (PROTOCOL, SERVICE_NAME, CAPMC_VERSION)

LOGGER = logging.getLogger('bos.operators.utils.clients.capmc')

# If a CAPMC response contains an error that is in of the these lists,
# then it will also contain a list of nodes that should be disabled.
# XNAME_COMMON_ERROR_STRINGS, XNAME_STATUS_ERROR_STRINGS, and
# XNAME_ON_OFF_ERROR_STRINGS
XNAME_COMMON_ERROR_STRINGS = ['invalid/duplicate xnames',
                              'disabled or not found',
                              'xnames role blocked',
                              'xnames role blocked/not found']


XNAME_STATUS_ERROR_STRINGS = ['xnames not found']
XNAME_STATUS_ERROR_STRINGS.extend(XNAME_COMMON_ERROR_STRINGS)

XNAME_ON_OFF_ERROR_STRINGS = ["invalid xnames",
                              "Invalid Component IDs",
                              "components disabled"]
XNAME_ON_OFF_ERROR_STRINGS.extend(XNAME_COMMON_ERROR_STRINGS)
class CapmcReturnedError(ABC):
    """
    A base function for parsing the errors returned by CAPMC.
    The nodes_in_error is a dictionary with nodes (keys) and errors (values).

    Must override:
    * calculate_nodes_in_error
    * process_error_string
    """
    def __init__(self, response):
        self.response = response
        self.error_code = 0
        self.error_message = ''
        self.nodes_in_error = {}
        if 'e' in response:
            self.error_code = response['e']
        if 'err_msg' in response:
            self.error_message = response['err_msg']
        self.calculate_nodes_in_error()

    @abstractmethod
    def calculate_nodes_in_error(self):
        pass

    @abstractmethod
    def process_error_string(self):
        """
        Process the received error string against the appropriate
        error string dictionary.

        This function should be overridden replacing XNAME_COMMON_ERROR_STRINGS
        with the appropriate error string dictionary for the type of call
        being issued to CAPMC.
        """
        self._process_error_string(XNAME_COMMON_ERROR_STRINGS)

    def _process_error_string(self, error_string_dict):
        """
        This function will populate the nodes_in_error attribute if there are
        any nodes found to be in error. Note, some errors cannot be associated
        with an individual node.
        Inputs:
        :param dict error_strings: A dictionary of error strings to compare against
        """
        for err_str in error_string_dict:
            match = re.match(fr"{err_str}: +\[([\w,]+)\]", self.error_message)
            if match:
                nodes_in_error = match.group(1).split(',')
                for node in nodes_in_error:
                    self.nodes_in_error[node] = CapmcNodeError(self.error_code, err_str)
                break


class CapmcXnameStatusReturnedError(CapmcReturnedError):
    """
    This class processes errors returned when calling xname_get_status.

    ----------------------------------------------------------------------------------------
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

    This class only populates nodes_in_error for the 400 errors that actually provide
    failed nodes. Other errors do not provide a list of failed nodes, so those errors are
    merely captured at the top level.
    """
    def calculate_nodes_in_error(self):
        if self.error_code == 400:
            self.process_error_string()

    def process_error_string(self):
        """
        Process the received error string against the XNAME_STATUS_ERROR_STRINGS
        dictionary.
        """
        self._process_error_string(XNAME_STATUS_ERROR_STRINGS)

class CapmcXnameOnOffReturnedError(CapmcReturnedError):
    """
    This class processes errors returned when calling xname_on and xname_off.

    This function is used in booting as well as shutdown, so it has been
    abstracted to one place in order to avoid duplication.

    ----------------------------------------------------------------------------------------
    Here is an example of what a partially successful shutdown looks like, since it isn't captured
    in the documentation particularly well. This is from the CAPMC backend.
    {"e":-1,"err_msg":"Errors encountered with 1/1 Xnames issued On","xnames":[{"xname":"x3000c0s19b3n0","e":-1,"err_msg":"NodeBMC Communication Error"}]}

    e: -1
    errMsg: "Errors encountered with %d components for %s"
    FATAL. Could not find supported power operations

    e: -1
    errMsg: "Errors encountered with %d/%d Xnames issued %s"\
    Partial success. Most likely FATAL for failed components

    e: -1
    errMsg: "no power controls for %s operation"
    FATAL. Can't determine power operation

    e: -1
    errMsg: "Skipping %s: Type, '%s', not defined in power sequence for '%s'"
    errMsg: "no supported ResetType for %s operation"
    FATAL. Power operation not supported.

    e: 37
    errMsg: "Error: Failed to reserve components while performing a %s."
    Retry. The condition may resolve itself

    e: 400
    errMsg: "Bad Request: " + decode error
    errMsg: "Bad Request: Missing required xnames parameter"
    errMsg: "Bad Request: Required xnames list is empty"
    Retry with valid request

    e: 400
    errMsg: "Cannot force the On operation"
    Retry without 'force=true' in payload

    e: 400
    errMsg: "Bad Request: recursive and prereq options are mutually exclusive"
    Retry with only one of the options

    e: 400
    errMsg: "invalid xnames: [x1001c0s0b0n0]"
    errMsg: "invalid/duplicate xnames: [x1001c0s0b0n0]"
    errMsg: "Invalid Component IDs: [x1001c0s0b0n0]"
    errMsg: "disabled or not found: [x1001c0s0b0n0]"
    errMsg: "xnames role blocked: [x1001c0s0b0n0]"
    errMsg: "xnames role blocked/not found: [x1001c0s0b0n0]"
    errMsg: "nodes disabled: [1001]"
    errMsg: "components disabled: [x1001c0s0b0n0]"
    Retry with invalid and/or duplicate names/IDs removed

    e: 400
    errMsg: "No nodes found to operate on"
    Retry with valid xname list or different filter options

    e: 405
    errMsg: "(PATCH) Not Allowed"
    Retry with POST

    e: 500
    errMsg: "Error: " + request/unmarshal error string
    errMst: "Connection to the secure store isn't ready. Can not get redfish credentials."
    FATAL. CAPMC is unable to talk to a required service (HSM, VAULT)
    ----------------------------------------------------------------------------------------

    This class only populates nodes_in_error for errors that actually provide
    failed nodes. Other errors do not provide a list of failed nodes, so those errors are
    merely captured at the top level.
    """
    def calculate_nodes_in_error(self):
        if self.error_code == -1:
            if 'undefined' in self.response:
                for node in self.response['undefined']:
                    self.nodes_in_error[node] = CapmcNodeError(self.error_code,'undefined')
            if 'xnames' in self.response:
                for xname_dict in self.response['xnames']:
                    xname = xname_dict['xname']
                    err_msg = xname_dict['err_msg']
                    self.nodes_in_error[xname] = CapmcNodeError(self.error_code, err_msg)
        elif self.error_code == 400:
            self.process_error_string()

    def process_error_string(self):
        """
        Process the received error string against the XNAME_ON_OFF_ERROR_STRINGS
        dictionary.
        """
        self._process_error_string(XNAME_ON_OFF_ERROR_STRINGS)


class CapmcNodeError(object):
    def __init__(self, error_code, error_message):
        self.error_code = error_code
        self.error_message = error_message

    def __repr__(self) -> str:
        """
        Print how this class was initialized for debugging purposes.
        """
        print(f"CapmcNodeError(self.error_code, self.error_message)")

    def __str__(self) -> str:
        """
        Print a human-readable version of this class.
        """
        print(f"Error code: {self.error_code}\tError Message: {self.error_message}")


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
      :rtype: dict
      xname_status_failures: A CapmcXnameStatusReturnedError class containing the error code,
       error string, and a dictionary containing nodes (keys) suffering from errors (valuse)
      :rtype: CapmcXnameStatusReturnedError

    Raises:
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

    xname_status_failures = CapmcXnameStatusReturnedError(json_response)
    LOGGER.debug("XNAME_STATUS_FAILURES: nodes_in_error: "
                 f"{xname_status_failures.nodes_in_error}")
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        LOGGER.error("Failed interacting with Cray Advanced Platform "
                     "Monitoring and Control (CAPMC). "
                     f"Error code: {xname_status_failures.error_code} "
                     f"Error message: {xname_status_failures.error_message} "
                     f"Entire response: {xname_status_failures.response}")

    # Remove the error elements leaving only the node's power status.
    for key in ('e', 'err_msg'):
        try:
            del json_response[key]
        except KeyError:
            pass

    # Reorder JSON response into a dictionary where the nodes are the keys.
    node_power_status = {}
    for power_state, nodes in json_response.items():
        for node in nodes:
            node_power_status[node] = power_state

    return node_power_status, xname_status_failures


def power(nodes, state, force = True, session = None, cont = True, reason = "BOS: Powering nodes") -> CapmcXnameOnOffReturnedError:
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
      errors (dict): A class container on error code, error message, and
      a dictionary containing the nodes (keys) suffering from errors (values)
      :rtype: CapmcXnameOnOffReturnedError

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

    errors = CapmcXnameOnOffReturnedError(json_response)
    if errors.error_code != 0:
        LOGGER.error("Failed interacting with Cray Advanced Platform "
                     "Monitoring and Control (CAPMC). "
                     f"Error code: {errors.error_code}"
                     f"Error message: {errors.error_message}")
    return errors


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

def disable_based_on_error_xname_on_off(error):
    """
    CAPMC returns errors to requests to xname_on and xname_off.
    Some errors are transient, some not.
    Some non-transient errors have nodes associated with them. Others do not
    have nodes associated with them.
    Non-transient errors with associated nodes should cause those node
    to be disabled.
    Inputs:
        :param str error: The error string returned by CAPMC.

    Returns:
        True: When the error is non-transient.
        False: When the error is transient.
        :rtype: boolean
    """
    if error in XNAME_ON_OFF_ERROR_STRINGS:
        return True
    return False

def disable_based_on_error_xname_status(error):
    """
    CAPMC returns errors to requests to get_xname_status.
    Some errors are transient, some not.
    Some non-transient errors have nodes associated with them. Others do not
    have nodes associated with them.
    Non-transient errors with associated nodes should cause those node
    to be disabled.
    Inputs:
        :param str error: The error string returned by CAPMC.

    Returns:
        True: When the error is non-transient.
        False: When the error is transient.
        :rtype: boolean
    """
    if error in XNAME_STATUS_ERROR_STRINGS:
        return True
    return False