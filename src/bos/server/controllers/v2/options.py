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
import logging
import threading
import time

import connexion

from bos.common.options import DEFAULTS, OptionsCache
from bos.common.utils import exc_type_msg
from bos.server import redis_db_utils as dbutils
from bos.server.models.v2_options import V2Options as Options
from bos.server.utils import get_request_json

LOGGER = logging.getLogger('bos.server.controllers.v2.options')
DB = dbutils.get_wrapper(db='options')
# We store all options as json under this key so that the data format is
# similar to other data stored in the database, and to make retrieval of all
# options simpler
OPTIONS_KEY = 'options'


class OptionsData(OptionsCache):
    """
    Handler for reading configuration options from the BOS DB

    This caches the options so that frequent use of these options do not all
    result in DB calls.
    """
    def _get_options(self) -> dict:
        """Retrieves the current options from the BOS DB"""
        LOGGER.debug("Retrieving options data from BOS DB")
        try:
            return _get_v2_options()
        except Exception as err:
            LOGGER.error("Error retrieving BOS options: %s", exc_type_msg(err))
        return {}


def _init():
    # Start log level updater
    log_level_updater = threading.Thread(target=check_v2_logging_level, args=())
    log_level_updater.start()

    # Cleanup old options
    while True:
        try:
            data = DB.get(OPTIONS_KEY)
            break
        except Exception as err:
            LOGGER.info('Database is not yet available (%s)', exc_type_msg(err))
            time.sleep(1)
    if not data:
        return
    data = _clean_options_data(data)
    DB.put(OPTIONS_KEY, data)


@dbutils.redis_error_handler
def get_v2_options():
    """Used by the GET /options API operation"""
    LOGGER.debug("GET /v2/options invoked get_v2_options")
    return _get_v2_options(), 200


def _get_v2_options() -> dict:
    """
    Helper function for get_v2_options function and OptionsData class
    """
    data = get_v2_options_data()
    return _clean_options_data(data)


def _clean_options_data(data):
    """Removes keys that are not in the options spec"""
    to_delete = []
    all_options = set(Options().attribute_map.values())
    for key in data:
        if key not in all_options:
            to_delete.append(key)
    for key in to_delete:
        del data[key]
    return data


def get_v2_options_data():
    return _check_defaults(DB.get(OPTIONS_KEY))


def _check_defaults(data):
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
        return DB.put(OPTIONS_KEY, data)
    return data


@dbutils.redis_error_handler
def patch_v2_options():
    """Used by the PATCH /options API operation"""
    LOGGER.debug("PATCH /v2/options invoked patch_v2_options")
    try:
        data = get_request_json()
    except Exception as err:
        LOGGER.error("Error parsing PATCH request data: %s", exc_type_msg(err))
        return connexion.problem(
            status=400, title="Error parsing the data provided.",
            detail=str(err))

    if OPTIONS_KEY not in DB:
        DB.put(OPTIONS_KEY, {})
    return DB.patch(OPTIONS_KEY, data), 200


def update_log_level(new_level_str):
    new_level = logging.getLevelName(new_level_str.upper())
    current_level = LOGGER.getEffectiveLevel()
    if current_level != new_level:
        LOGGER.log(current_level, 'Changing logging level from %s to %s',
                   logging.getLevelName(current_level), logging.getLevelName(new_level))
        logger = logging.getLogger()
        logger.setLevel(new_level)
        LOGGER.log(new_level, 'Logging level changed from %s to %s',
                   logging.getLevelName(current_level), logging.getLevelName(new_level))


def check_v2_logging_level():
    while True:
        try:
            data = get_v2_options_data()
            if 'logging_level' in data:
                update_log_level(data['logging_level'])
        except Exception as err:
            LOGGER.debug("Error checking or updating log level: %s", exc_type_msg(err))
        time.sleep(5)
