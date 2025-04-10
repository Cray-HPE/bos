#
# MIT License
#
# (C) Copyright 2019, 2021-2022, 2024-2025 Hewlett Packard Enterprise Development LP
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
import threading
import time

from bos.common.options import DEFAULTS, OptionsCache
from bos.common.types.general import JsonDict
from bos.common.types.options import OptionsDict, is_option_name
from bos.common.utils import exc_type_msg, do_update_log_level
import bos.server.redis_db_utils as dbutils

LOGGER = logging.getLogger(__name__)

LogLevelUpdateLock = threading.Lock()

DB = dbutils.OptionsDBWrapper()

class OptionsData(OptionsCache):
    """
    Handler for reading configuration options from the BOS DB

    This caches the options so that frequent use of these options do not all
    result in DB calls.
    """

    _create_lock = threading.Lock()

    def __new__(cls):
        """This override makes the class a singleton"""
        if not hasattr(cls, 'instance'):
            # Make sure that no other thread has beaten us to the punch
            with cls._create_lock:
                if not hasattr(cls, 'instance'):
                    new_instance = super().__new__(cls)
                    new_instance.__init__(_initialize=True)
                    # Only assign to cls.instance after all work has been done, to ensure
                    # no other threads access it prematurely
                    cls.instance = new_instance
        return cls.instance

    def __init__(self, _initialize: bool=False):
        """
        We only want this singleton to be initialized once
        """
        if _initialize:
            super().__init__()

    def _get_options(self) -> OptionsDict:
        """Retrieves the current options from the BOS DB"""
        LOGGER.debug("Retrieving options data from BOS DB")
        try:
            return get_options()
        except Exception as err:
            LOGGER.error("Error retrieving BOS options: %s", exc_type_msg(err))
        # Continue using current option values
        return self.options


def _cleanup_old_options() -> None:
    """
    Cleanup old options
    """
    while True:
        try:
            data = DB.get_options()
            break
        except dbutils.NotFoundInDB:
            # No old options to clean up
            return
        except Exception as err:
            LOGGER.info('Database is not yet available (%s)',
                        exc_type_msg(err))
            time.sleep(1)
    if not data:
        # No old options to clean up
        return
    data = remove_invalid_keys(data)
    DB.put_options(data)


def _init() -> None:
    """
    Called by bos.server.__main__ on server startup
    """
    _cleanup_old_options()
    update_server_log_level()


def remove_invalid_keys(data: JsonDict) -> OptionsDict:
    """Removes keys that are not in the options spec"""
    return { key: value for key, value in data.items() if is_option_name(key) }


def get_options() -> OptionsDict:
    """
    Helper function for OptionsData class
    """
    data = get_v2_options_data()
    return remove_invalid_keys(data)


def get_v2_options_data() -> OptionsDict:
    """
    Load the options from the BOS database, and then fill in
    default values
    """
    try:
        option_data = DB.get_options()
    except dbutils.NotFoundInDB:
        option_data = None
    return _check_defaults(option_data)


def _check_defaults(data: OptionsDict | None) -> OptionsDict:
    """Adds defaults to the options data if they don't exist"""
    put = False
    if not data:
        data = {}
        put = True
    for key, default_value in DEFAULTS.items():
        if key not in data:
            data[key] = default_value
            put = True
    if put:
        DB.put_options(data)
    return data


def update_server_log_level() -> None:
    """
    Refresh BOS options and update the log level for this process, if needed
    """
    options_data.update()
    desired_level_str = options_data.logging_level.upper()
    desired_level_int = logging.getLevelName(desired_level_str)
    current_level_int = LOGGER.getEffectiveLevel()
    if current_level_int == desired_level_int:
        # No update needed
        return
    # Take a lock to prevent multiple threads from doing this
    with LogLevelUpdateLock:
        if current_level_int != desired_level_int:
            do_update_log_level(current_level_int, desired_level_int, desired_level_str)


# Other server code which needs to read BOS options should import and use this dict
options_data = OptionsData()
