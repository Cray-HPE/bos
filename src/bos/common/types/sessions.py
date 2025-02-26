#
# MIT License
#
# (C) Copyright 2025 Hewlett Packard Enterprise Development LP
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
Type annotation definitions for BOS sessions
"""
import copy
from typing import Literal, Required, TypedDict

from .general import BosDataRecord

SessionStatusLabel = Literal['complete', 'pending', 'running']

class SessionStatus(TypedDict, total=False):
    """
    #/components/schemas/V2SessionStatus
    """
    end_time: str | None
    error: str | None
    start_time: str
    status: SessionStatusLabel

SessionOperation = Literal['boot', 'reboot', 'shutdown']

class Session(BosDataRecord, total=False):
    """
    #/components/schemas/V2Session
    """
    components: str
    include_disabled: bool
    limit: str
    name: Required[str]
    operation: Required[SessionOperation]
    stage: bool
    status: Required[SessionStatus]
    template_name: Required[str]
    tenant: str | None

def update_session_record(record: Session, new_record: Session) -> None:
    """
    Patch 'record' in-place with the data from 'new_record'.
    """
    # Make a copy, to avoid changing new_record in place
    new_record_copy = copy.deepcopy(new_record)

    # First, merge the status sub-dict
    if "status" in new_record_copy:
        if "status" in record:
            record["status"].update(new_record_copy["status"])
            new_record_copy["status"] = record["status"]
        else:
            record["status"] = new_record_copy["status"]

    # The remaining fields can be merged the old-fashioned way
    record.update(new_record_copy)
