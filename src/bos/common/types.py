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

from typing import Literal, Optional, Required, TypedDict

# For type hints

JsonData = bool|dict|int|float|list|None|str
JsonDict = dict[str,JsonData]

# Mapping from string labels to sets of node names
NodeSetMapping = dict[str, set[str]]

BootArtifacts = dict[str, str]
ComponentStatus = dict[str, str]

class ComponentLastAction(TypedDict, total=False):
    action: str
    failed: bool
    last_updated: str

ComponentEventStats = dict[str, int]

class BaseComponentState(TypedDict, total=False):
    boot_artifacts: BootArtifacts
    last_updated: str

class ComponentActualState(BaseComponentState, total=False):
    bss_token: str

class ComponentDesiredState(BaseComponentState, total=False):
    bss_token: str
    configuration: str

class ComponentStagedState(BaseComponentState, total=False):
    configuration: str
    session: str

class Component(TypedDict, total=False):
    actual_state: ComponentActualState
    desired_state: ComponentDesiredState
    enabled: bool
    error: str
    event_stats: ComponentEventStats
    id: Required[str]
    last_action: ComponentLastAction
    retry_policy: int
    session: str
    staged_state: ComponentStagedState
    status: ComponentStatus

SessionStatusLabel = Literal['complete', 'pending', 'running']

class SessionStatus(TypedDict, total=False):
    # Optional means these can be a string or be None
    end_time: Optional[str]
    error: Optional[str]
    start_time: str
    status: SessionStatusLabel

SessionOperation = Literal['boot', 'reboot', 'shutdown']

class Session(TypedDict, total=False):
    components: str
    include_disabled: bool
    limit: str
    name: Required[str]
    operation: Required[SessionOperation]
    stage: bool
    status: SessionStatus
    template_name: Required[str]
    # Optional means this can be a string or be None
    tenant: Optional[str]

class Link(TypedDict, total=False):
    href: str
    rel: str

class SessionTemplateCfsParameters(TypedDict, total=False):
    configuration: str

BootSetArch = Literal['X86', 'ARM', 'Other', 'Unknown']

BOOT_SET_DEFAULT_ARCH: BootSetArch = 'X86'

# Valid boot sets are required to have at least one of these fields
BootSetHardwareSpecifierFields = Literal['node_list', 'node_roles_groups', 'node_groups']

# This fancy footwork lets us construct a tuple of the string values from the previous definition,
# allowing us to avoid duplicating it.
BOOT_SET_HARDWARE_SPECIFIER_FIELDS: tuple[BootSetHardwareSpecifierFields] = \
    typing.get_args(BootSetHardwareSpecifierFields)

class BootSet(TypedDict, total=False):
    arch: BootSetArch
    cfs: SessionTemplateCfsParameters
    etag: str
    kernel_parameters: str
    name: str
    node_list: list[str]
    node_groups: list[str]
    node_roles_groups: list[str]    
    path: Required[str]
    rootfs_provider: str
    rootfs_provider_passthrough: str
    type: Required[str]

class SessionTemplate(TypedDict, total=False):
    boot_sets: Required[dict[str, BootSet]]
    cfs: SessionTemplateCfsParameters
    description: str
    enable_cfs: bool
    links: list[Link]
    name: Required[str]
    # Optional means this can be a string or be None
    tenant: Optional[str]
