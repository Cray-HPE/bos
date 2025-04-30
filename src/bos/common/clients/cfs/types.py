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

from typing import Literal, TypedDict

from bos.common.types.general import JsonDict

CfsComponentConfigurationStatus = Literal["unconfigured", "pending", "failed", "configured"]

class CfsComponentData(TypedDict, total=False):
    """
    https://github.com/Cray-HPE/config-framework-service/blob/develop/api/openapi.yaml
    '#/components/schemas/V3ComponentData'
    """
    id: str
    desired_config: str
    error_count: int
    retry_policy: int
    enabled: bool
    configuration_status: CfsComponentConfigurationStatus
    logs: str
    tags: dict[str, str]
    # We do not care about the following fields, so we do not fully type annotate them
    state: list[JsonDict]
    state_append: JsonDict
    desired_state: list[JsonDict]

class CfsComponentsFilter(TypedDict, total=False):
    """
    https://github.com/Cray-HPE/config-framework-service/blob/develop/api/openapi.yaml
    '#/components/schemas/V3ComponentsFilter'
    """
    ids: str
    status: CfsComponentConfigurationStatus
    enabled: bool
    config_name: str
    tags: str

class CfsComponentsUpdate(TypedDict, total=True):
    """
    https://github.com/Cray-HPE/config-framework-service/blob/develop/api/openapi.yaml
    '#/components/schemas/V3ComponentsUpdate'
    """
    patch: CfsComponentData
    filters: CfsComponentsFilter

class CfsGetComponentsPagedResponse(TypedDict, total=False):
    """
    https://github.com/Cray-HPE/config-framework-service/blob/develop/api/openapi.yaml
    '#/components/schemas/V3ComponentDataCollection'
    """
    components: list[CfsComponentData]
    next: JsonDict | None
