#
# MIT License
#
# (C) Copyright 2021-2022, 2024 Hewlett Packard Enterprise Development LP
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
This is a client module to the BOS component state API. 

The primary use for this is to allow nodes to indicate the
state of their boot artifacts as indicate by the BOS Session ID.
"""
import logging
import json
from requests.exceptions import HTTPError, ConnectionError
from urllib3.exceptions import MaxRetryError

from bos.common.utils import exc_type_msg
from bos.reporter.components import BOSComponentException
from bos.reporter.components import ENDPOINT as COMPONENT_ENDPOINT
from bos.reporter.client import requests_retry_session

LOGGER = logging.getLogger(__name__)


class UnknownComponent(BOSComponentException):
    """
    When we attempt to patch information on a component that doesn't exist.
    """


class UnrecognizedResponse(BOSComponentException):
    """
    BOS responded in an inconsistent fashion.
    """


def patch_component(component, properties, session=None):
    """
    For a given <component>, patch the component's <properties> using
    the BOS API endpoint.
    """
    session = session or requests_retry_session()
    component_endpoint = '%s/%s' % (COMPONENT_ENDPOINT, component)
    try:
        response = session.patch(component_endpoint, json=properties)
    except (ConnectionError, MaxRetryError) as ce:
        LOGGER.warning("Could not connect to BOS API service: %s", exc_type_msg(ce))
        raise BOSComponentException(ce) from ce
    try:
        response.raise_for_status()
    except HTTPError as hpe:
        if response.status_code == 404:
            try:
                json_response = json.loads(response.text)
                raise UnknownComponent(json_response['detail'])
            except json.JSONDecodeError as jde:
                raise UnrecognizedResponse("BOS returned a non-json response: %s\n%s" % (response.text, jde)) from jde
        LOGGER.warning("Unexpected response from '%s':\n%s: %s", component_endpoint, response.status_code, response.text)
        raise BOSComponentException(hpe) from hpe


def report_state(component, state, session=None):
    """
    Report the <component>'s state.
    """
    data = {'id': component, 'actual_state': state}
    patch_component(component, data, session=session)
