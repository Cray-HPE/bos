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

from typing import Literal, Required, TypedDict

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

class Session(TypedDict, total=False):
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

class SessionCreate(TypedDict, total=False):
    """
    #/components/schemas/V2SessionCreate
    """
    include_disabled: bool
    limit: str
    name: str
    operation: Required[SessionOperation]
    stage: bool
    template_name: Required[str]

class SessionUpdate(TypedDict, total=False):
    """
    #/components/schemas/V2SessionUpdate
    """
    components: str
    status: SessionStatus

def update_session_record(record: Session, patch_data: SessionUpdate) -> None:
    """
    Patch 'record' in-place with the data from 'patch_data'.
    """
    if "status" in patch_data:
        record["status"].update(patch_data["status"])

    if "components" in patch_data:
        record["components"] = patch_data["components"]

class SessionFilter(TypedDict, total=False):
    """
    The parameters that can be passed into BOS session endpoints that allow filtering
    V2SessionsMaxAgeQueryParam:
    V2SessionsMinAgeQueryParam:
    V2SessionsStatusQueryParam:
    """
    min_age: str
    max_age: str
    status: SessionStatusLabel
