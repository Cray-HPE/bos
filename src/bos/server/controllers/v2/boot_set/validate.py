#
# MIT License
#
# (C) Copyright 2021-2022, 2024 Hewlett Packard Enterprise Development LP
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

from functools import partial
from typing import Optional

from bos.common.types import BootSet, SessionOperation, SessionTemplate
from bos.common.utils import exc_type_msg
from bos.server.controllers.v2.options import OptionsData

from .artifacts import validate_boot_artifacts
from .defs import HARDWARE_SPECIFIER_FIELDS, LOGGER, BootSetStatus
from .exceptions import BootSetError, BootSetWarning
from .ims import validate_ims_boot_image


def validate_boot_sets(session_template: SessionTemplate,
                       operation: SessionOperation,
                       template_name: str,
                       options_data: Optional[OptionsData]=None) -> tuple[BootSetStatus, str]:
    """
    Validates the boot sets listed in a session template.
    This is called when creating a session or when using the sessiontemplatesvalid endpoint

    It ensures that there are boot sets.
    It checks that each boot set specifies nodes via at least one of the specifier fields.
    Ensures that the boot artifacts exist.

    Inputs:
      session_template (dict): Session template data
      operation (str): Requested operation
      template_name (str): The name of the session template; Note, during Session template
                                 creation, the name in the session template data does not have
                                 to match the name used to create the session template.
      options_data (OptionsData): BOS options, or None (in which case they will be loaded from BOS)
    Returns:
        Returns an status code and a message
        See BootSetStatus definition for details on the status codes
    """
    # Verify boot sets exist.
    if not session_template.get('boot_sets', None):
        msg = f"Session template '{template_name}' requires at least 1 boot set."
        return BootSetStatus.ERROR, msg

    if options_data is None:
        options_data = OptionsData()

    warning_msgs = []
    for bs_name, bs in session_template['boot_sets'].items():
        bs_msg = partial(_bs_msg, template_name=template_name, bs_name=bs_name)
        try:
            bs_warning_msgs = validate_boot_set(bs=bs, operation=operation,
                                                 options_data=options_data)
        except BootSetError as err:
            msg = bs_msg(str(err))
            LOGGER.error(msg)
            return BootSetStatus.ERROR, msg
        except Exception as err:
            LOGGER.error(
                bs_msg(f"Unexpected exception in _validate_boot_set: {exc_type_msg(err)}"))
            raise
        for msg in map(bs_msg, bs_warning_msgs):
            LOGGER.warning(msg)
            warning_msgs.append(msg)

    if warning_msgs:
        return BootSetStatus.WARNING, "; ".join(warning_msgs)

    return BootSetStatus.SUCCESS, "Valid"


def _bs_msg(msg: str, template_name: str, bs_name: str) -> str:
    """
    Shortcut for creating validation error/warning messages for a specific bootset
    """
    return f"Session template: '{template_name}' boot set: '{bs_name}': {msg}"


def validate_boot_set(bs: BootSet, operation: SessionOperation,
                      options_data: OptionsData) -> list[str]:
    """
    Helper function for validate_boot_sets that performs validation on a single boot set.
    Raises BootSetError if fatal errors found.
    Returns a list of warning messages (if any)
    """
    warning_msgs = []

    verify_nonempty_hw_specifier_field(bs)

    try:
        check_node_list_for_nids(bs, options_data)
    except BootSetWarning as err:
        warning_msgs.append(str(err))

    if operation in ['boot', 'reboot']:
        try:
            validate_boot_artifacts(bs)
        except BootSetWarning as err:
            warning_msgs.append(str(err))

        try:
            validate_ims_boot_image(bs, options_data)
        except BootSetWarning as err:
            warning_msgs.append(str(err))

    return warning_msgs


def verify_nonempty_hw_specifier_field(bs: BootSet) -> None:
    """
    Raises an exception if there are no non-empty hardware specifier fields.
    """
    # Validate that the boot set has at least one of the HARDWARE_SPECIFIER_FIELDS
    if not any(field_name in bs for field_name in HARDWARE_SPECIFIER_FIELDS):
        raise BootSetError(f"No hardware specifier fields ({HARDWARE_SPECIFIER_FIELDS})")

    # Validate that at least one of the HARDWARE_SPECIFIER_FIELDS is non-empty
    if not any(field_name in bs and bs[field_name]
               for field_name in HARDWARE_SPECIFIER_FIELDS):
        raise BootSetError(f"No non-empty hardware specifier fields ({HARDWARE_SPECIFIER_FIELDS})")


def check_node_list_for_nids(bs: BootSet, options_data: OptionsData) -> None:
    """
    If the node list contains no NIDs, return.
    Otherwise, raise BootSetError or BootSetWarning, depending on the value of the
    reject_nids option
    """
    if "node_list" not in bs:
        return
    if any(node[:3] == "nid" for node in bs["node_list"]):
        msg = "Has NID in 'node_list'"
        raise BootSetError(msg) if options_data.reject_nids else BootSetWarning(msg)
