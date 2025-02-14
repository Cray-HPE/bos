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
Type annotation definitions for BOS components
"""

from typing import Required, TypedDict

# Mapping from string labels to sets of node names
type NodeSetMapping = dict[str, set[str]]

type BootArtifacts = dict[str, str]
type ComponentStatus = dict[str, str]

class ComponentLastAction(TypedDict, total=False):
    action: str
    failed: bool
    last_updated: str

type ComponentEventStats = dict[str, int]

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

class ComponentRecord(TypedDict, total=False):
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
