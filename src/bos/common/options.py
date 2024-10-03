#
# MIT License
#
# (C) Copyright 2024 Hewlett Packard Enterprise Development LP
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
from abc import ABC, abstractmethod
from typing import Any


# This is the source of truth for default option values. All other BOS
# code should either import this dict directly, or (preferably) access
# its values indirectly using a DefaultOptions object
DEFAULTS = {
    'cleanup_completed_session_ttl': "7d",
    'clear_stage': False,
    'component_actual_state_ttl': "4h",
    'default_retry_policy': 3,
    'disable_components_on_completion': True,
    'discovery_frequency': 300,
    'logging_level': 'INFO',
    'max_boot_wait_time': 1200,
    'max_component_batch_size': 2800,
    'max_power_off_wait_time': 300,
    'max_power_on_wait_time': 120,
    'polling_frequency': 15,
    'reject_nids': False,
    'session_limit_required': False
}

class BaseOptions(ABC):
    """
    Abstract base class for getting BOS option values
    """

    @abstractmethod
    def get_option(self, key: str) -> Any:
        """
        Return the value for the specified option
        """

    # These properties call the method responsible for getting the option value.
    # All these do is convert the response to the appropriate type for the option,
    # and return it.

    @property
    def cleanup_completed_session_ttl(self) -> str:
        return str(self.get_option('cleanup_completed_session_ttl'))

    @property
    def clear_stage(self) -> bool:
        return bool(self.get_option('clear_stage'))

    @property
    def component_actual_state_ttl(self) -> str:
        return str(self.get_option('component_actual_state_ttl'))

    @property
    def default_retry_policy(self) -> int:
        return int(self.get_option('default_retry_policy'))

    @property
    def disable_components_on_completion(self) -> bool:
        return bool(self.get_option('disable_components_on_completion'))

    @property
    def discovery_frequency(self) -> int:
        return int(self.get_option('discovery_frequency'))

    @property
    def logging_level(self) -> str:
        return str(self.get_option('logging_level'))

    @property
    def max_boot_wait_time(self) -> int:
        return int(self.get_option('max_boot_wait_time'))

    @property
    def max_component_batch_size(self) -> int:
        return int(self.get_option('max_component_batch_size'))

    @property
    def max_power_off_wait_time(self) -> int:
        return int(self.get_option('max_power_off_wait_time'))

    @property
    def max_power_on_wait_time(self) -> int:
        return int(self.get_option('max_power_on_wait_time'))

    @property
    def polling_frequency(self) -> int:
        return int(self.get_option('polling_frequency'))

    @property
    def reject_nids(self) -> bool:
        return bool(self.get_option('reject_nids'))

    @property
    def session_limit_required(self) -> bool:
        return bool(self.get_option('session_limit_required'))


class DefaultOptions(BaseOptions):
    """
    Returns the default value for each option
    """
    def get_option(self, key: str) -> Any:
        if key in DEFAULTS:
            return DEFAULTS[key]
        raise KeyError(key)


class OptionsCache(DefaultOptions, ABC):
    """
    Handler for reading configuration options from the BOS API/DB

    This caches the options so that frequent use of these options do not all
    result in network/DB calls.
    """
    def __init__(self, update_on_create:bool=True):
        super().__init__()
        if update_on_create:
            self.update()
        else:
            self.options = {}

    def update(self) -> None:
        """Refreshes the cached options data"""
        self.options = self._get_options()

    @abstractmethod
    def _get_options(self) -> dict:
        """Retrieves the current options from the BOS api/DB"""

    def get_option(self, key: str) -> Any:
        if key in self.options:
            return self.options[key]
        try:
            return super().get_option(key)
        except KeyError as err:
            raise KeyError(f'Option {key} not found and no default exists') from err
