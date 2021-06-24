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

import logging
import json
from requests.exceptions import HTTPError, ConnectionError
from urllib3.exceptions import MaxRetryError

from bos.operators.utils import requests_retry_session
from bos.operators.utils.clients.bos import ENDPOINT as BASE_ENDPOINT

LOGGER = logging.getLogger('bos.operators.utils.clients.bos.options')
ENDPOINT = "%s/%s" % (BASE_ENDPOINT, __name__.lower().split('.')[-1])


class Options:
    """
    Handler for reading configuration options from the BOS API

    This caches the options so that frequent use of these options do not all
    result in network calls.
    """
    def __init__(self):
        self.options = {}

    def update(self):
        """Refreshes the cached options data"""
        self.options = self._get_options()

    def _get_options(self):
        """Retrieves the current options from the BOS api"""
        session = requests_retry_session()
        try:
            response = session.get(ENDPOINT)
            response.raise_for_status()
            return json.loads(response.text)
        except (ConnectionError, MaxRetryError) as e:
            LOGGER.error("Unable to connect to BOS: {}".format(e))
        except HTTPError as e:
            LOGGER.error("Unexpected response from BOS: {}".format(e))
        except json.JSONDecodeError as e:
            LOGGER.error("Non-JSON response from BOS: {}".format(e))
        return {}

    def get_option(self, key, value_type):
        return value_type(self.options[key])

    @property
    def logging_level(self):
        return self.get_option('loggingLevel', str)

    @property
    def polling_frequency(self):
        return self.get_option('pollingFrequency', int)

    @property
    def max_component_wait_time(self):
        return self.get_option('maxComponentWaitTime', int)


options = Options()
