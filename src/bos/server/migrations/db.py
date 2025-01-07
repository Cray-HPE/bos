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

import logging
import time

import bos.server.redis_db_utils as dbutils

LOGGER = logging.getLogger('bos.server.migration')

TEMP_DB=dbutils.get_wrapper(db='session_templates')
SESS_DB=dbutils.get_wrapper(db='sessions')
STAT_DB=dbutils.get_wrapper(db='session_status')
COMP_DB=dbutils.get_wrapper(db='components')

MAX_DB_WAIT_SECONDS=120.0

def all_db_ready() -> bool:
    """
    Wait for up to MAX_DB_WAIT_SECONDS for all databases to be ready
    """
    start_time = time.time()
    first = True
    while time.time() - start_time <= MAX_DB_WAIT_SECONDS:
        if first:
            first = False
        else:
            LOGGER.info("Sleeping for 7 seconds before retrying databases")
            time.sleep(7)
        if not TEMP_DB.ready:
            continue
        LOGGER.info("Template database is ready")
        if not SESS_DB.ready:
            continue
        LOGGER.info("Session database is ready")
        if not STAT_DB.ready:
            continue
        LOGGER.info("Session status database is ready")
        if not COMP_DB.ready:
            continue
        LOGGER.info("Component database is ready")
        return True
    return False


def delete_from_db(db: dbutils.DBWrapper, key: str, err_msg: str|None=None) -> None:
    if err_msg is None:
        LOGGER.warning("Deleting %s under DB key '%s'", db.db_string, key)
    else:
        LOGGER.error("%s; Deleting %s under DB key '%s'", err_msg, db.db_string, key)
    data = db.get_and_delete(key)
    if data:
        LOGGER.info("Deleted %s '%s': %s", db.db_string, key, data)
    else:
        LOGGER.warning("Could not delete %s '%s' -- does not exist", db.db_string, key)


def delete_component(key: str, err_msg: str|None=None) -> None:
    delete_from_db(COMP_DB, key, err_msg)


def delete_template(key: str, err_msg: str|None=None) -> None:
    delete_from_db(TEMP_DB, key, err_msg)


def delete_session(key: str, err_msg: str|None=None) -> None:
    delete_from_db(SESS_DB, key, err_msg)
    LOGGER.info("Deleting associated session status, if it exists")
    delete_from_db(STAT_DB, key, err_msg)
