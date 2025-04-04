#
# MIT License
#
# (C) Copyright 2021-2022, 2024-2025 Hewlett Packard Enterprise Development LP
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
from typing import Literal, NoReturn, cast

from connexion.lifecycle import ConnexionResponse

from bos.common.options import DEFAULTS, OptionsCache
from bos.common.types.general import JsonDict
from bos.common.types.options import is_option_name, OptionsDict
from bos.common.utils import exc_type_msg
from bos.server import redis_db_utils as dbutils
from bos.server.controllers.utils import _400_bad_request
from bos.server.utils import get_request_json

LOGGER = logging.getLogger(__name__)
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
            return _get_v2_options()
        except Exception as err:
            LOGGER.error("Error retrieving BOS options: %s", exc_type_msg(err))
        return {}


def _init() -> None:
    # Start log level updater
    log_level_updater = threading.Thread(target=check_v2_logging_level,
                                         args=())
    log_level_updater.start()

    # Cleanup old options
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
    data = _clean_options_data(data)
    DB.put_options(data)


@dbutils.redis_error_handler
def get_v2_options() -> tuple[OptionsDict, Literal[200]]:
    """Used by the GET /options API operation"""
    LOGGER.debug("GET /v2/options invoked get_v2_options")
    return _get_v2_options(), 200


def _get_v2_options() -> OptionsDict:
    """
    Helper function for get_v2_options function and OptionsData class
    """
    data = get_v2_options_data()
    return _clean_options_data(data)


def _clean_options_data(data: JsonDict) -> OptionsDict:
    """Removes keys that are not in the options spec"""
    return { key: value for key, value in data.items() if is_option_name(key) }


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


@dbutils.redis_error_handler
def patch_v2_options() -> tuple[OptionsDict, Literal[200]] | ConnexionResponse:
    """Used by the PATCH /options API operation"""
    LOGGER.debug("PATCH /v2/options invoked patch_v2_options")
    try:
        data = cast(OptionsDict, get_request_json())
    except Exception as err:
        LOGGER.error("Error parsing PATCH request data: %s", exc_type_msg(err))
        return _400_bad_request(f"Error parsing the data provided: {err}")

    options = get_v2_options_data()
    options.update(data)
    DB.put_options(data)
    return data, 200


def update_log_level(new_level_str: str) -> None:
    new_level = logging.getLevelName(new_level_str.upper())
    current_level = LOGGER.getEffectiveLevel()
    if current_level != new_level:
        LOGGER.log(current_level, 'Changing logging level from %s to %s',
                   logging.getLevelName(current_level), logging.getLevelName(new_level))
        logger = logging.getLogger()
        logger.setLevel(new_level)
        LOGGER.log(new_level, 'Logging level changed from %s to %s',
                   logging.getLevelName(current_level), logging.getLevelName(new_level))


def check_v2_logging_level() -> NoReturn:
    while True:
        try:
            data = get_v2_options_data()
            if 'logging_level' in data:
                update_log_level(data['logging_level'])
        except Exception as err:
            LOGGER.debug("Error checking or updating log level: %s",
                         exc_type_msg(err))
        time.sleep(5)
