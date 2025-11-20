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
"""
Definitions for redis_db_utils modules
"""

from enum import IntEnum
import logging
from typing import Final, TypeVar

from bos.common.types.components import BootArtifacts, ComponentRecord
from bos.common.types.options import OptionsDict
from bos.common.types.sessions import Session
from bos.common.types.session_extended_status import SessionExtendedStatus
from bos.common.types.templates import SessionTemplate

from .env_vars import get_pos_int_env_var_or_default

LOGGER = logging.getLogger(__name__)

class Databases(IntEnum):
    """
    Integer value is the database ID
    """
    OPTIONS = 0
    COMPONENTS = 1
    SESSION_TEMPLATES = 2
    SESSIONS = 3
    BSS_TOKENS_BOOT_ARTIFACTS = 4
    SESSION_STATUS = 5

DB_HOST = 'cray-bos-db'
DB_PORT = 6379

# The decoded data formats for the different BOS databases
BosDataRecord = TypeVar("BosDataRecord", BootArtifacts, ComponentRecord, OptionsDict,
                        Session, SessionExtendedStatus, SessionTemplate)

# In a watch/execute pipeline, a DB method will not start a new retry iteration if
# more than DB_BUSY_SECONDS have elapsed since the DB operation started.
DEFAULT_DB_BUSY_SECONDS: Final[int] = 60
DB_BUSY_SECONDS = get_pos_int_env_var_or_default("DB_BUSY_SECONDS",
                                                 DEFAULT_DB_BUSY_SECONDS)
LOGGER.debug("DB_BUSY_SECONDS = %d", DB_BUSY_SECONDS)

# For database methods that work on multiple database entries, DB_BATCH_SIZE
# is the maximum number of entries it will attempt to work on at once.
# The lower the number, the worse the DB performance will be, but the lower
# the risk of DB operations being retried because of conflicting DB changes by other clients.
# The higher the number, the better the DB performance will be, but the higher
# the risk of DB operations being retried because of conflicting DB changes by other clients.
# (which would result in a performance impact or even a timeout failure for the
# overall DB method).
DEFAULT_DB_BATCH_SIZE: Final[int] = 20
DB_BATCH_SIZE = get_pos_int_env_var_or_default("DB_BATCH_SIZE",
                                               DEFAULT_DB_BATCH_SIZE)
LOGGER.debug("DB_BATCH_SIZE = %d", DB_BATCH_SIZE)
