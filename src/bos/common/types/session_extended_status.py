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
Type annotation definitions for BOS extended session statuses
"""
from typing import TypedDict

from .general import BosDataRecord
from .sessions import SessionStatusLabel

class SessionExtendedStatusPhases(TypedDict, total=True):
    """
    #/components/schemas/V2SessionExtendedStatusPhases
    """
    percent_complete: float
    percent_powering_on: float
    percent_powering_off: float
    percent_configuring: float

class SessionExtendedStatusErrorComponents(TypedDict, total=True):
    """
    #/components/schemas/V2SessionExtendedStatusErrorComponents
    """
    count: int
    list: str

class SessionExtendedStatusTiming(TypedDict, total=True):
    """
    #/components/schemas/V2SessionExtendedStatusTiming
    """
    end_time: str | None
    start_time: str
    duration: str

class SessionExtendedStatus(BosDataRecord, total=False):
    """
    #/components/schemas/V2SessionExtendedStatus
    """
    status: SessionStatusLabel
    managed_components_count: int
    phases: SessionExtendedStatusPhases
    percent_successful: float
    percent_failed: float
    percent_staged: float
    error_summary: dict[str, SessionExtendedStatusErrorComponents]
    timing: SessionExtendedStatusTiming
