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

from typing import Required, TypedDict


class Members(TypedDict, total=False):
    """
    https://github.com/Cray-HPE/hms-smd/blob/master/api/swagger_v2.yaml
    '#/definitions/Members.1.0.0'
    """
    ids: list[str]


class Group(TypedDict, total=False):
    """
    https://github.com/Cray-HPE/hms-smd/blob/master/api/swagger_v2.yaml
    '#/definitions/Group.1.0.0:'
    """
    label: Required[str]
    description: str
    tags: list[str]
    exclusiveGroup: str
    members: Members


class Partition(TypedDict, total=False):
    """
    https://github.com/Cray-HPE/hms-smd/blob/master/api/swagger_v2.yaml
    '#/definitions/Partition.1.0.0:'
    """
    name: Required[str]
    description: str
    tags: list[str]
    members: Members


class StateComponentData(TypedDict, total=False):
    """
    https://github.com/Cray-HPE/hms-smd/blob/master/api/swagger_v2.yaml
    '#/definitions/Component.1.0.0_Component'
    """
    ID: str
    Type: str
    State: str
    Flag: str
    Enabled: bool
    SoftwareStatus: str
    Role: str
    SubRole: str
    NID: int
    Subtype: str
    NetType: str
    Arch: str
    Class: str
    ReservationDisabled: bool
    Locked: bool


class StateComponentsDataArray(TypedDict, total=False):
    """
    https://github.com/Cray-HPE/hms-smd/blob/master/api/swagger_v2.yaml
    '#/definitions/ComponentArray_ComponentArray'
    """
    Components: list[StateComponentData]


class ComponentStatus(TypedDict, total=False):
    """
    https://github.com/Cray-HPE/hms-smd/blob/master/api/swagger_v2.yaml
    '#/definitions/ComponentStatus.1.0.0'
    """
    ID: str
    Locked: bool
    Reserved: bool
    CreatedTime: str
    ExpirationTime: str
    ReservationDisabled: bool


class LocksComponentsDataArray(TypedDict, total=False):
    """
    https://github.com/Cray-HPE/hms-smd/blob/master/api/swagger_v2.yaml
    '#/definitions/AdminStatusCheck_Response.1.0.0'
    """
    Components: list[ComponentStatus]
    # The way that BOS queries for locks, this field should never actually be used, since it never
    # queries for specific xnames
    NotFound: list[str]
