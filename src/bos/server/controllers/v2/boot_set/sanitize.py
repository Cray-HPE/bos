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

from typing import Optional

from bos.common.types import BootSet, SessionTemplate
from bos.common.types import BOOT_SET_DEFAULT_ARCH as DEFAULT_ARCH
from bos.common.utils import exc_type_msg
from bos.server.controllers.v2.options import OptionsData
from bos.server.utils import canonize_xname

from .artifacts import validate_boot_artifacts
from .defs import LOGGER
from .exceptions import BootSetError, BootSetWarning
from .ims import validate_ims_boot_image
from .validate import check_node_list_for_nids, verify_nonempty_hw_specifier_field


def validate_sanitize_boot_sets(template_data: SessionTemplate,
                                options_data: Optional[OptionsData]=None) -> None:
    """
    Calls validate_sanitize_boot_set on every boot set in the template.
    Raises an exception if there are problems.
    """
    # The boot_sets field is required.
    try:
        boot_sets = template_data["boot_sets"]
    except KeyError as exc:
        raise BootSetError("Missing required 'boot_sets' field") from exc

    # The boot_sets field must map to a dict
    if not isinstance(boot_sets, dict):
        raise BootSetError("'boot_sets' field has invalid type")

    # The boot_sets field must be non-empty
    if not boot_sets:
        raise BootSetError("Session templates must contain at least one boot set")

    if options_data is None:
        options_data = OptionsData()

    # Finally, call validate_sanitize_boot_set on each boot set
    for bs_name, bs in boot_sets.items():
        validate_sanitize_boot_set(bs_name, bs, options_data=options_data)


def validate_sanitize_boot_set(bs_name: str, bs_data: BootSet, options_data: OptionsData) -> None:
    """
    Called when creating/updating a BOS session template.
    Validates the boot set, and sanitizes it (editing it in place).
    Since this request has come in through the API, we assume that schema-level validation has
    already happened.
    Raises BootSetError on error.
    """
    if "name" not in bs_data:
        # Set the field here -- this allows the name to be validated
        # per the schema later
        bs_data["name"] = bs_name
    elif bs_data["name"] != bs_name:
        # All keys in the boot_sets mapping must match the 'name' fields in the
        # boot sets to which they map (if they contain a 'name' field).
        raise BootSetError(f"boot_sets key ({bs_name}) does not match 'name' "
                               f"field of corresponding boot set ({bs_data['name']})")

    # Set the 'arch' field to the default value, if it is not present
    if "arch" not in bs_data:
        bs_data["arch"] = DEFAULT_ARCH

    # Check the boot artifacts
    try:
        validate_boot_artifacts(bs_data)
    except (BootSetError, BootSetWarning) as err:
        LOGGER.warning(str(err))

    # Validate the boot set IMS image
    try:
        validate_ims_boot_image(bs_data, options_data)
    except BootSetWarning as err:
        LOGGER.warning("Boot set '%s': %s", bs_name, err)
        LOGGER.warning('Boot set contents: %s', bs_data)
    except Exception as err:
        raise BootSetError(exc_type_msg(err)) from err

    # Validate that the boot set has at least one non-empty HARDWARE_SPECIFIER_FIELDS
    try:
        verify_nonempty_hw_specifier_field(bs_data)
    except BootSetError as err:
        raise BootSetError(f"Boot set {bs_name}: {err}") from err

    # Last things to do are validate/sanitize the node_list field, if it is present
    if "node_list" not in bs_data:
        return

    try:
        check_node_list_for_nids(bs_data, options_data)
    except BootSetWarning as err:
        LOGGER.warning("Boot set %s: %s", bs_name, err)
    except BootSetError as err:
        raise BootSetError(f"Boot set {bs_name}: {err}") from err

    bs_data["node_list"] = [ canonize_xname(node) for node in bs_data["node_list"] ]
