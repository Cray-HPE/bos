#
# MIT License
#
# (C) Copyright 2021-2024 Hewlett Packard Enterprise Development LP
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
import json
from requests.exceptions import HTTPError, ConnectionError
from urllib3.exceptions import MaxRetryError

from bos.common.utils import exc_type_msg, requests_retry_session
from bos.operators.utils.clients.bos.base import BASE_ENDPOINT

LOGGER = logging.getLogger('bos.operators.utils.clients.bos.options')
__name = __name__.lower().rsplit('.', maxsplit=1)[-1]
ENDPOINT = f"{BASE_ENDPOINT}/{__name}"


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
        LOGGER.debug("GET %s", ENDPOINT)
        try:
            response = session.get(ENDPOINT)
            response.raise_for_status()
            return json.loads(response.text)
        except (ConnectionError, MaxRetryError) as e:
            LOGGER.error("Unable to connect to BOS: %s", exc_type_msg(e))
        except HTTPError as e:
            LOGGER.error("Unexpected response from BOS: %s", exc_type_msg(e))
        except json.JSONDecodeError as e:
            LOGGER.error("Non-JSON response from BOS: %s", exc_type_msg(e))
        return {}

    def get_option(self, key, value_type, default):
        if key in self.options:
            return value_type(self.options[key])
        if default:
            return value_type(default)
        raise KeyError(f'Option {key} not found and no default exists')

    @property
    def logging_level(self):
        return self.get_option('logging_level', str, 'INFO')

    @property
    def polling_frequency(self):
        return self.get_option('polling_frequency', int, 15)

    @property
    def discovery_frequency(self):
        return self.get_option('discovery_frequency', int, 5*60)

    @property
    def max_boot_wait_time(self):
        return self.get_option('max_boot_wait_time', int, 1200)

    @property
    def max_power_on_wait_time(self):
        return self.get_option('max_power_on_wait_time', int, 120)

    @property
    def max_power_off_wait_time(self):
        return self.get_option('max_power_off_wait_time', int, 300)

    @property
    def disable_components_on_completion(self):
        return self.get_option('disable_components_on_completion', bool, True)

    @property
    def cleanup_completed_session_ttl(self):
        # Defaults to 7 days (168 hours).
        return self.get_option('cleanup_completed_session_ttl', str, '7d')

    @property
    def clear_stage(self):
        return self.get_option('clear_stage', bool, False)

    @property
    def component_actual_state_ttl(self):
        return self.get_option('component_actual_state_ttl', str, '4h')

    @property
    def default_retry_policy(self):
        return self.get_option('default_retry_policy', int, 3)

    @property
    def max_component_batch_size(self):
        return self.get_option('max_component_batch_size', int, 2800)

    @property
    def session_limit_required(self):
        return self.get_option('session_limit_required', bool, False)

options = Options()
