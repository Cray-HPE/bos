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
    Base class for an object that has properties for each BOS option
    """

    # These properties call the abstract properties responsible for
    # getting the option values. All these do is convert the response
    # to the appropriate type for the option, and return it.

    @property
    def cleanup_completed_session_ttl(self) -> str:
        return str(self._cleanup_completed_session_ttl)

    @property
    def clear_stage(self) -> bool:
        return bool(self._clear_stage)

    @property
    def component_actual_state_ttl(self) -> str:
        return str(self._component_actual_state_ttl)

    @property
    def default_retry_policy(self) -> int:
        return int(self._default_retry_policy)

    @property
    def disable_components_on_completion(self) -> bool:
        return bool(self._disable_components_on_completion)

    @property
    def discovery_frequency(self) -> int:
        return int(self._discovery_frequency)

    @property
    def logging_level(self) -> str:
        return str(self._logging_level)

    @property
    def max_boot_wait_time(self) -> int:
        return int(self._max_boot_wait_time)

    @property
    def max_component_batch_size(self) -> int:
        return int(self._max_component_batch_size)

    @property
    def max_power_off_wait_time(self) -> int:
        return int(self._max_power_off_wait_time)

    @property
    def max_power_on_wait_time(self) -> int:
        return int(self._max_power_on_wait_time)

    @property
    def polling_frequency(self) -> int:
        return int(self._polling_frequency)

    @property
    def reject_nids(self) -> bool:
        return bool(self._reject_nids)

    @property
    def session_limit_required(self) -> bool:
        return bool(self._session_limit_required)

    # The following abstract properties must be implemented by
    # the classes that inherit from this base class. They are
    # responsible for returning a value for the option. The return
    # type is specified as Any because we allow for the possibility
    # that they return an unexpected type (which is then converted
    # by the above properties). That said, ideally they should just
    # return the correct type for the option.

    @property
    @abstractmethod
    def _cleanup_completed_session_ttl(self) -> Any:
        pass

    @property
    @abstractmethod
    def _clear_stage(self) -> Any:
        pass

    @property
    @abstractmethod
    def _component_actual_state_ttl(self) -> Any:
        pass

    @property
    @abstractmethod
    def _default_retry_policy(self) -> Any:
        pass

    @property
    @abstractmethod
    def _disable_components_on_completion(self) -> Any:
        pass

    @property
    @abstractmethod
    def _discovery_frequency(self) -> Any:
        pass

    @property
    @abstractmethod
    def _logging_level(self) -> Any:
        pass

    @property
    @abstractmethod
    def _max_boot_wait_time(self) -> Any:
        pass

    @property
    @abstractmethod
    def _max_component_batch_size(self) -> Any:
        pass

    @property
    @abstractmethod
    def _max_power_off_wait_time(self) -> Any:
        pass

    @property
    @abstractmethod
    def _max_power_on_wait_time(self) -> Any:
        pass

    @property
    @abstractmethod
    def _polling_frequency(self) -> Any:
        pass

    @property
    @abstractmethod
    def _reject_nids(self) -> Any:
        pass

    @property
    @abstractmethod
    def _session_limit_required(self) -> Any:
        pass


class OptionsWithDefaults(BaseOptions):
    """
    Handler for reading configuration options from the BOS API/DB

    This caches the options so that frequent use of these options do not all
    result in network/DB calls.
    """
    def __init__(self):
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
        if key in DEFAULTS:
            return DEFAULTS[key]
        raise KeyError(f'Option {key} not found and no default exists')

    @property
    def _logging_level(self) -> Any:
        return self.get_option('logging_level')

    @property
    def _polling_frequency(self) -> Any:
        return self.get_option('polling_frequency')

    @property
    def _discovery_frequency(self) -> Any:
        return self.get_option('discovery_frequency')

    @property
    def _max_boot_wait_time(self) -> Any:
        return self.get_option('max_boot_wait_time')

    @property
    def _max_power_on_wait_time(self) -> Any:
        return self.get_option('max_power_on_wait_time')

    @property
    def _max_power_off_wait_time(self) -> Any:
        return self.get_option('max_power_off_wait_time')

    @property
    def _disable_components_on_completion(self) -> Any:
        return self.get_option('disable_components_on_completion')

    @property
    def _cleanup_completed_session_ttl(self) -> Any:
        return self.get_option('cleanup_completed_session_ttl')

    @property
    def _clear_stage(self) -> Any:
        return self.get_option('clear_stage')

    @property
    def _component_actual_state_ttl(self) -> Any:
        return self.get_option('component_actual_state_ttl')

    @property
    def _default_retry_policy(self) -> Any:
        return self.get_option('default_retry_policy')

    @property
    def _max_component_batch_size(self) -> Any:
        return self.get_option('max_component_batch_size')

    @property
    def _session_limit_required(self) -> Any:
        return self.get_option('session_limit_required')

    @property
    def _reject_nids(self) -> Any:
        return self.get_option('reject_nids')
