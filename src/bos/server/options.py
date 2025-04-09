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
from collections.abc import Callable
import functools
import logging
import threading
import time
from typing import NoReturn, ParamSpec, TypeVar

from bos.common.options import DEFAULTS, OptionsCache
from bos.common.types.general import JsonDict
from bos.common.types.options import OptionsDict, remove_invalid_keys
from bos.common.utils import exc_type_msg, hlog, update_log_level
import .redis_db_utils as dbutils

LOGGER = logging.getLogger(__name__)

LogLevelUpdateLock = threading.Lock()
LogLevelUpdateThread: None | threading.Thread = None

DB = dbutils.OptionsDBWrapper()

class OptionsData(OptionsCache):
    """
    Handler for reading configuration options from the BOS DB

    This caches the options so that frequent use of these options do not all
    result in DB calls.
    """

    def _get_options(self) -> OptionsDict:
        """Retrieves the current options from the BOS DB"""
        LOGGER.debug("Retrieving options data from BOS DB")
        try:
            return get_options()
        except Exception as err:
            LOGGER.error("Error retrieving BOS options: %s", exc_type_msg(err))
        return {}


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
    data = get_v2_options_data()
    logging_level = data.get('logging_level')
    if logging_level is not None:
        update_log_level(logging_level)


def get_options() -> OptionsDict:
    """
    Helper function for OptionsData class
    """
    data = get_v2_options_data()
    return remove_invalid_keys(data)


def get_v2_options_data() -> OptionsDict:
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


def _check_logging_level() -> NoReturn:
    hlog("Starting check_logging_level")
    while True:
        try:
            data = get_v2_options_data()
            new_log_level = data.get('logging_level')
            if new_log_level is not None:
                update_log_level(new_log_level)
        except Exception as err:
            msg = f"Error checking or updating log level: {exc_type_msg(err)}"
            hlog(msg)
            LOGGER.debug(msg)

        time.sleep(5)


P = ParamSpec('P')
R = TypeVar('R')

def handle_log_level(func: Callable[P, R]) -> Callable[P, R]:
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        global LogLevelUpdateThread
        if LogLevelUpdateThread is None:
            hlog("LogLevelUpdateThread is None")
            with LogLevelUpdateLock:
                if LogLevelUpdateThread is None:
                    hlog("LogLevelUpdateThread is still None -> starting updater thread")
                    log_level_updater = threading.Thread(target=_check_logging_level, args=())
                    log_level_updater.start()
                    LogLevelUpdateThread = log_level_updater
                else:
                    hlog("LogLevelUpdateThread is not None anymore")
        return func(*args, **kwargs)

    return wrapper
