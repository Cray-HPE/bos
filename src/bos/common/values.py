#
# MIT License
#
# (C) Copyright 2022, 2024 Hewlett Packard Enterprise Development LP
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

from bos.common.types import BootArtifacts, ComponentActualState, ComponentDesiredState, \
                             ComponentStagedState

# Phases
class Phase:
    powering_on = "powering_on"
    powering_off = "powering_off"
    configuring = "configuring"
    none = ""

# Actions
class Action:
    power_on = "powering_on"
    power_off_gracefully = "powering_off_gracefully"
    power_off_forcefully = "powering_off_forcefully"
    apply_staged = "apply_staged"
    session_setup = "session_setup"
    newly_discovered = "newly_discovered"

# Status
class Status:
    power_on_pending = "power_on_pending"
    power_on_called = "power_on_called"
    power_off_pending = "power_off_pending"
    power_off_gracefully_called = "power_off_gracefully_called"
    power_off_forcefully_called = "power_off_forcefully_called"
    configuring = "configuring"
    stable = "stable"
    failed = "failed"
    on_hold = "on_hold"


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
