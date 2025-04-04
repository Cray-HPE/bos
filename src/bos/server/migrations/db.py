#
# MIT License
#
# (C) Copyright 2024-2025 Hewlett Packard Enterprise Development LP
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

LOGGER = logging.getLogger(__name__)

TEMP_DB = dbutils.SessionTemplateDBWrapper()
SESS_DB = dbutils.SessionDBWrapper()
STAT_DB = dbutils.SessionStatusDBWrapper()
COMP_DB = dbutils.ComponentDBWrapper()

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


def delete_from_db(db: dbutils.DBWrapper,
                   key: str,
                   err_msg: str | None = None) -> None:
    if err_msg is None:
        LOGGER.warning("Deleting %s under DB key '%s'", db.db.name, key)
    else:
        LOGGER.error("%s; Deleting %s under DB key '%s'", err_msg,
                     db.db.name, key)
    try:
        data = db.get_and_delete_raw(key)
    except dbutils.NotFoundInDB:
        LOGGER.warning("Could not delete %s '%s' -- does not exist",
                       db.db.name, key)
    else: # No exception raised by DB call
        LOGGER.info("Deleted %s '%s': %s", db.db.name, key, data)


def delete_component(key: str, err_msg: str | None = None) -> None:
    delete_from_db(COMP_DB, key, err_msg)


def delete_template(key: str, err_msg: str | None = None) -> None:
    delete_from_db(TEMP_DB, key, err_msg)


def delete_session(key: str, err_msg: str | None = None) -> None:
    delete_from_db(SESS_DB, key, err_msg)
    LOGGER.info("Deleting associated session status, if it exists")
    delete_from_db(STAT_DB, key, err_msg)
