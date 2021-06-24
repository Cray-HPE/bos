# Copyright 2021 Hewlett Packard Enterprise Development LP
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
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# (MIT License)
import json
import logging
import os
from requests.exceptions import HTTPError, ConnectionError
from urllib3.exceptions import MaxRetryError

from bos.operators.utils import requests_retry_session, PROTOCOL

SERVICE_NAME = 'cray-smd'
BASE_ENDPOINT = "%s://%s/hsm/v2/" % (PROTOCOL, SERVICE_NAME)
ENDPOINT = os.path.join(BASE_ENDPOINT, 'State/Components/Query')

LOGGER = logging.getLogger('bos.operators.utils.clients.hsm')


def get_components(node_list, enabled=None):
    """Get information for all list components HSM"""
    session = requests_retry_session()
    try:
        payload = {'ComponentIDs': node_list}
        if enabled is not None:
            payload['enabled'] = [str(enabled)]
        response = session.post(ENDPOINT, json=payload)
        response.raise_for_status()
        components = json.loads(response.text)
    except (ConnectionError, MaxRetryError) as e:
        LOGGER.error("Unable to connect to HSM: {}".format(e))
        raise e
    except HTTPError as e:
        LOGGER.error("Unexpected response from HSM: {}".format(e))
        raise e
    except json.JSONDecodeError as e:
        LOGGER.error("Non-JSON response from HSM: {}".format(e))
        raise e
    return components
