#
# MIT License
#
# (C) Copyright 2022, 2024-2025 Hewlett Packard Enterprise Development LP
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
BOS values used by both server and operators
"""

from bos.common.types.components import (BootArtifacts,
                                         ComponentActionStr,
                                         ComponentActualState,
                                         ComponentDesiredState,
                                         ComponentPhaseStr,
                                         ComponentStagedState,
                                         ComponentStatusStr)
from bos.common.types.templates import SupportedRootfsProvider

# Phases
class Phase:
    powering_on: ComponentPhaseStr = "powering_on"
    powering_off: ComponentPhaseStr = "powering_off"
    configuring: ComponentPhaseStr = "configuring"
    none: ComponentPhaseStr = ""


# Actions
class Action:
    actual_state_cleanup: ComponentActionStr = "actual_state_cleanup"
    apply_staged: ComponentActionStr = "apply_staged"
    newly_discovered: ComponentActionStr = "newly_discovered"
    power_off_forcefully: ComponentActionStr = "powering_off_forcefully"
    power_off_gracefully: ComponentActionStr = "powering_off_gracefully"
    power_on: ComponentActionStr = "powering_on"
    session_setup: ComponentActionStr = "session_setup"


# Status
class Status:
    power_on_pending: ComponentStatusStr = "power_on_pending"
    power_on_called: ComponentStatusStr = "power_on_called"
    power_off_pending: ComponentStatusStr = "power_off_pending"
    power_off_gracefully_called: ComponentStatusStr = "power_off_gracefully_called"
    power_off_forcefully_called: ComponentStatusStr = "power_off_forcefully_called"
    configuring: ComponentStatusStr = "configuring"
    stable: ComponentStatusStr = "stable"
    failed: ComponentStatusStr = "failed"
    on_hold: ComponentStatusStr = "on_hold"

# Rootfs providers
class RootfsProvider:
    sbps: SupportedRootfsProvider = "sbps"

EMPTY_BOOT_ARTIFACTS: BootArtifacts = {
    "kernel": "",
    "kernel_parameters": "",
    "initrd": ""
}

EMPTY_ACTUAL_STATE: ComponentActualState = {
    "boot_artifacts": EMPTY_BOOT_ARTIFACTS,
    "bss_token": ""
}

EMPTY_DESIRED_STATE: ComponentDesiredState = {
    "configuration": "",
    "boot_artifacts": EMPTY_BOOT_ARTIFACTS,
    "bss_token": ""
}

EMPTY_STAGED_STATE: ComponentStagedState = {
    "configuration": "",
    "boot_artifacts": EMPTY_BOOT_ARTIFACTS
}
