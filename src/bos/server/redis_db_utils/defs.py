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
from typing import TypeVar

from bos.common.types.components import BootArtifacts, ComponentRecord
from bos.common.types.options import OptionsDict
from bos.common.types.sessions import Session
from bos.common.types.session_extended_status import SessionExtendedStatus
from bos.common.types.templates import SessionTemplate

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
