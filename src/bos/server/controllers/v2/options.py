#
# MIT License
#
# (C) Copyright 2021-2025 Hewlett Packard Enterprise Development LP
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
import connexion
import threading
import time

from bos.common.utils import exc_type_msg
from bos.server import redis_db_utils as dbutils
from bos.server.models.v2_options import V2Options as Options

LOGGER = logging.getLogger('bos.server.controllers.v2.options')
DB = dbutils.get_wrapper(db='options')
# We store all options as json under this key so that the data format is
# similar to other data stored in the database, and to make retrieval of all
# options simpler
OPTIONS_KEY = 'options'
DEFAULTS = {
    'bss_read_timeout': 10,
    'cfs_read_timeout': 10,
    'cleanup_completed_session_ttl': "7d",
    'clear_stage': False,
    'component_actual_state_ttl': "4h",
    'disable_components_on_completion': True,
    'discovery_frequency': 5*60,
    'hsm_read_timeout': 10,
    'logging_level': 'INFO',
    'max_boot_wait_time': 1200,
    'max_power_on_wait_time': 120,
    'max_power_off_wait_time': 300,
    'pcs_read_timeout': 10,
    'polling_frequency': 15,
    'default_retry_policy': 3,
    'max_component_batch_size': 2800,
    "session_limit_required": False
}


def _init():
    # Start log level updater
    log_level_updater = threading.Thread(target=check_v2_logging_level, args=())
    log_level_updater.start()

    """ Cleanup old options """
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
    data = get_v2_options_data()
    data = _clean_options_data(data)
    return data, 200


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
    for key in DEFAULTS:
        if key not in data:
            data[key] = DEFAULTS[key]
            put = True
    if put:
        return DB.put(OPTIONS_KEY, data)
    return data


@dbutils.redis_error_handler
def patch_v2_options():
    """Used by the PATCH /options API operation"""
    LOGGER.debug("PATCH /v2/options invoked patch_v2_options")
    try:
        data = connexion.request.get_json()
    except Exception as err:
        LOGGER.error("Error parsing request data: %s", exc_type_msg(err))
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
        LOGGER.log(current_level, 'Changing logging level from {} to {}'.format(
            logging.getLevelName(current_level), logging.getLevelName(new_level)))
        logger = logging.getLogger()
        logger.setLevel(new_level)
        LOGGER.log(new_level, 'Logging level changed from {} to {}'.format(
            logging.getLevelName(current_level), logging.getLevelName(new_level)))


def check_v2_logging_level():
    while True:
        try:
            data = get_v2_options_data()
            if 'logging_level' in data:
                update_log_level(data['logging_level'])
        except Exception as err:
            LOGGER.debug("Error checking or updating log level: %s", exc_type_msg(err))
        time.sleep(5)
