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
Type annotation definitions for BOS session templates
"""
import copy
from typing import get_args, Literal, Required, TypedDict

class Link(TypedDict, total=False):
    """
    #/components/schemas/Link
    """
    href: str
    rel: str

class SessionTemplateCfsParameters(TypedDict, total=False):
    """
    #/components/schemas/V2CfsParameters
    """
    configuration: str

BootSetArch = Literal['X86', 'ARM', 'Other', 'Unknown']

BOOT_SET_DEFAULT_ARCH: BootSetArch = 'X86'

# Valid boot sets are required to have at least one of these fields
BootSetHardwareSpecifierFields = Literal['node_list', 'node_roles_groups', 'node_groups']

# This fancy footwork lets us construct a frozenset of the string values from the previous
# definition, allowing us to avoid duplicating it.
BOOT_SET_HARDWARE_SPECIFIER_FIELDS: frozenset[BootSetHardwareSpecifierFields] = \
    frozenset(get_args(BootSetHardwareSpecifierFields))

class BootSet(TypedDict, total=False):
    """
    #/components/schemas/V2BootSet
    """
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

def _update_boot_set(record: BootSet, new_record_copy: BootSet) -> None:
    """
    This helper function will be used when patching boot sets.
    It patches 'record' in-place with the data from 'new_record_copy'.
    This is only ever called by _update_boot_sets
    """
    if "cfs" in new_record_copy:
        new_data = new_record_copy.pop("cfs")
        if "cfs" in record:
            record["cfs"].update(new_data)
        else:
            record["cfs"] = new_data

    # The remaining fields can be merged the old-fashioned way
    record.update(new_record_copy)

class SessionTemplate(TypedDict, total=False):
    """
    #/components/schemas/V2SessionTemplate
    """
    boot_sets: Required[dict[str, BootSet]]
    cfs: SessionTemplateCfsParameters
    description: str
    enable_cfs: bool
    links: list[Link]
    name: str
    tenant: str | None

def _update_boot_sets(record: dict[str, BootSet], new_record_copy: dict[str, BootSet]) -> None:
    """
    This helper function will be used when patching the 'boot_sets' map of a session template.
    It patches 'record' in-place with the data from 'new_record_copy'.
    This is only ever called by update_template_record
    """
    for new_bs_name, new_bs_record in new_record_copy.items():
        if new_bs_name in record:
            _update_boot_set(record[new_bs_name], new_bs_record)
        else:
            record[new_bs_name] = new_bs_record

def update_template_record(record: SessionTemplate, new_record: SessionTemplate) -> None:
    """
    This is used to patch session template data.
    The session template 'record' is patched in-place with the data from 'new_record'.
    """
    # Make a copy, to avoid changing new_record in place
    new_record_copy = copy.deepcopy(new_record)

    if "cfs" in new_record_copy:
        new_cfs_data = new_record_copy.pop("cfs")
        if "cfs" in record:
            record["cfs"].update(new_cfs_data)
        else:
            record["cfs"] = new_cfs_data

    # Next, merge "boot_sets"
    if "boot_sets" in new_record_copy:
        new_bs_data = new_record_copy["boot_sets"]
        if "boot_sets" in record:
            _update_boot_sets(record["boot_sets"], new_bs_data)
            new_record_copy["boot_sets"] = record["boot_sets"]
        else:
            record["boot_sets"] = new_bs_data

    # The remaining fields can be merged the old-fashioned way
    record.update(new_record_copy)

def remove_empty_cfs_field(data: SessionTemplate | BootSet) -> None:
    """
    If the data contains a 'cfs' field that is set to a null value
    (either an empty dict, or a dict whose 'configuration' field maps to an empty string),
    then delete it in-place. Do this to reduce confusion, since the behavior is the same either
    way, but the absence of the 'cfs' field has a more obvious meaning.
    """
    if "cfs" not in data:
        return
    if data["cfs"] and data["cfs"].get("configuration"):
        return
    del data["cfs"]
