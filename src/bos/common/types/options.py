#
# MIT License
#
# (C) Copyright 2024-2025 Hewlett Packard Enterprise Development LP
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
Type annotation definitions for BOS options
"""

from typing import Literal, TypedDict

from .general import BosDataRecord

# To help with type hints
type OptionValue = int | bool | str

# This should match all of the data structures defined in bos.common.options
type OptionName = Literal[
    'bss_read_timeout',
    'cfs_read_timeout',
    'cleanup_completed_session_ttl',
    'clear_stage',
    'component_actual_state_ttl',
    'default_retry_policy',
    'disable_components_on_completion',
    'discovery_frequency',
    'hsm_read_timeout',
    'ims_errors_fatal',
    'ims_images_must_exist',
    'ims_read_timeout',
    'logging_level',
    'max_boot_wait_time',
    'max_component_batch_size',
    'max_power_off_wait_time',
    'max_power_on_wait_time',
    'pcs_read_timeout',
    'polling_frequency',
    'reject_nids',
    'session_limit_required'
]

class OptionsDict(BosDataRecord, total=False):
    """
    This should match all of the data structures defined in bos.common.options

    #/components/schemas/V2Options
    """
    bss_read_timeout: int
    cfs_read_timeout: int
    cleanup_completed_session_ttl: str
    clear_stage: bool
    component_actual_state_ttl: str
    default_retry_policy: int
    disable_components_on_completion: bool
    discovery_frequency: int
    hsm_read_timeout: int
    ims_errors_fatal: bool
    ims_images_must_exist: bool
    ims_read_timeout: int
    logging_level: str
    max_boot_wait_time: int
    max_component_batch_size: int
    max_power_off_wait_time: int
    max_power_on_wait_time: int
    pcs_read_timeout: int
    polling_frequency: int
    reject_nids: bool
    session_limit_required: bool
