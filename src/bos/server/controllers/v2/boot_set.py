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

import logging
from bos.common.utils import exc_type_msg
from bos.operators.utils.boot_image_metadata import BootImageMetaData
from bos.operators.utils.boot_image_metadata.factory import BootImageMetaDataFactory
from bos.operators.utils.clients.s3 import S3Object
from bos.server.controllers.v2.options import get_v2_options_data
from bos.server.utils import canonize_xname, ParsingException

LOGGER = logging.getLogger('bos.server.controllers.v2.boot_set')

BOOT_SET_SUCCESS = 0
BOOT_SET_WARNING = 1
BOOT_SET_ERROR = 2

# Valid boot sets are required to have at least one of these fields
HARDWARE_SPECIFIER_FIELDS = ( "node_list", "node_roles_groups", "node_groups" )

DEFAULT_ARCH = "X86"

# Mapping from BOS boot set arch values to expected IMS image arch values
# Omits BOS Other value, since there is no corresponding IMS image arch value
EXPECTED_IMS_ARCH = {
    "ARM": "aarch64",
    "Unknown": "x86_64",
    "X86": "x86_64"
}


class BootSetValidationError(Exception):
    pass


class BootSetArchMismatch(BootSetValidationError):
    def __init__(self, bs_arch: str, expected_ims_arch: str, actual_ims_arch: str):
        super().__init__(self, f"Boot set arch '{bs_arch}' means IMS image arch should be "
                         f"'{expected_ims_arch}', but actual IMS image arch is {actual_ims_arch}")


class CannotValidateBootSetArch(BootSetValidationError):
    pass


def validate_boot_sets(session_template: dict,
                       operation: str,
                       template_name: str,
                       reject_nids: bool|None=None) -> tuple[str, int]:
    """
    Validates the boot sets listed in a session template.
    It ensures that there are boot sets.
    It checks that each boot set specifies nodes via at least one of the specifier fields.
    Ensures that the boot artifacts exist.

    Inputs:
      session_template (dict): Session template data
      operation (str): Requested operation
      template_name (str): The name of the session template; Note, during Session template
                                 creation, the name in the session template data does not have
                                 to match the name used to create the session template.
    Returns:
        Returns an error_code and a message
          error_code:
            0 -- Success
            1 -- Warning, not fatal
            2 -- Error, fatal


    """
    # Verify boot sets exist.
    if not session_template.get('boot_sets', None):
        msg = f"Session template '{template_name}' requires at least 1 boot set."
        return BOOT_SET_ERROR, msg

    if reject_nids is None:
        reject_nids = get_v2_options_data().get('reject_nids', False)

    warning_msgs = []
    for bs_name, bs in session_template['boot_sets'].items():
        try:
            warning_msgs.extend(validate_boot_set(template_name, bs_name, bs))
        except BootSetValidationError as err:
            msg = f"Session template: '{template_name}' boot set: '{bs_name}': {err}"
            LOGGER.error(msg)
            return BOOT_SET_ERROR, msg

    if warning_msgs:
        return BOOT_SET_WARNING, "; ".join(warning_msgs)

    return BOOT_SET_SUCCESS, "Valid"


def validate_boot_set(template_name: str, bs_name: str, bs: dict) -> list[str]:
    warning_msgs = []
    # Verify that the hardware is specified
    specified = [bs.get(field, None)
                 for field in HARDWARE_SPECIFIER_FIELDS]
    if not any(specified):
        raise BootSetValidationError(
            "No non-empty hardware specifier fields (%s)" % (', '.join(HARDWARE_SPECIFIER_FIELDS)))

    try:
        if any(node[:3] == "nid" for node in bs["node_list"]):
            msg = "Has NID in 'node_list'"
            if reject_nids:
                raise BootSetValidationError(msg)
            # Otherwise, log this as a warning -- even if reject_nids is not set,
            # BOS still doesn't support NIDs, so this is still undesirable
            msg = f"Session template: '{template_name}' boot set: '{bs_name}': {msg}"
            LOGGER.warning(msg)
            warning_msgs.append(msg)
    except KeyError:
        # If there is no node_list field, not a problem
        pass

    if operation in ['boot', 'reboot']:
        # Verify that the boot artifacts exist
        try:
            image_metadata = BootImageMetaDataFactory(bs)()
        except Exception as err:
            raise BootSetValidationError(
                "Can't locate boot artifacts. Error: " + exc_type_msg(err)) from err

        try:
            validate_boot_set_arch(bs, image_metadata)
        except CannotValidateBootSetArch as err:
            msg = f"Session template: '{template_name}' boot set: '{bs_name}'. Warning: {err}"
            LOGGER.warning(msg)
            warning_msgs.append(msg)
        except Exception as err:
            raise BootSetValidationError("Arch validation error: " + exc_type_msg(err)) from err

        # Check boot artifacts' S3 headers
        for boot_artifact in ["kernel"]:
            try:
                artifact = getattr(image_metadata.boot_artifacts, boot_artifact)
                path = artifact ['link']['path']
                etag = artifact['link']['etag']
                obj = S3Object(path, etag)
                _ = obj.object_header
            except Exception as err:
                raise BootSetValidationError(
                    f"Can't locate its {boot_artifact}. Error: " + exc_type_msg(err)) from err

        for boot_artifact in ["initrd", "boot_parameters"]:
            try:
                artifact = getattr(image_metadata.boot_artifacts, boot_artifact)
                if not artifact:
                    raise BootSetValidationError(f"Doesn't contain a {boot_artifact}.")
                path = artifact ['link']['path']
                etag = artifact['link']['etag']
                obj = S3Object(path, etag)
                _ = obj.object_header
            except Exception as err:
                msg = f"Session template: '{template_name}' boot set: '{bs_name}' " \
                      f"could not locate its {boot_artifact}. Warning: " + exc_type_msg(err)
                LOGGER.warning(msg)
                warning_msgs.append(msg)
    return warning_msgs


def validate_boot_set_arch(bs: dict, image_metadata: BootImageMetaData|None=None):
    """
    If the boot set architecture is not set to Other, check that the IMS image
    architecture matches the boot set architecture (treating a boot set architecture
    of Unknown as X86)
    """
    arch = bs.get("arch", DEFAULT_ARCH)
    if arch == 'Other':
        LOGGER.debug("Boot set arch set to 'Other'. Skipping IMS image arch validation: %s", bs)
        return

    if image_metadata is None:
        try:
            image_metadata = BootImageMetaDataFactory(bs)()
        except Exception as err:
            raise CannotValidateBootSetArch(
                "Can't locate boot artifacts: " + exc_type_msg(err)) from err

    try:
        ims_image_arch = image_metadata.arch
    except Exception as err:
        raise CannotValidateBootSetArch(
            "Can't validate architecture of boot artifacts: " + exc_type_msg(err)) from err

    if ims_image_arch is None:
        raise CannotValidateBootSetArch("Couldn't determine architecture of boot artifacts")
    if EXPECTED_IMS_ARCH[arch] != ims_image_arch:
        raise BootSetArchMismatch(bs_arch=arch, expected_ims_arch=EXPECTED_IMS_ARCH[arch],
                                  actual_ims_arch=ims_image_arch)


def validate_sanitize_boot_sets(template_data: dict) -> None:
    """
    Calls validate_sanitize_boot_set on every boot set in the template.
    Raises an exception if there are problems.
    """
    # The boot_sets field is required.
    try:
        boot_sets = template_data["boot_sets"]
    except KeyError as exc:
        raise ParsingException("Missing required 'boot_sets' field") from exc

    # The boot_sets field must map to a dict
    if not isinstance(boot_sets, dict):
        raise ParsingException("'boot_sets' field has invalid type")

    # The boot_sets field must be non-empty
    if not boot_sets:
        raise ParsingException("Session templates must contain at least one boot set")

    reject_nids = get_v2_options_data().get('reject_nids', False)

    # Finally, call validate_sanitize_boot_set on each boot set
    for bs_name, bs in boot_sets.items():
        validate_sanitize_boot_set(bs_name, bs, reject_nids=reject_nids)


def validate_sanitize_boot_set(bs_name: str, bs_data: dict, reject_nids: bool=False) -> None:
    """
    Called when creating/updating a BOS session template.
    Validates the boot set, and sanitizes it (editing it in place).
    Raises ParsingException on error.
    """
    if "name" not in bs_data:
        # Set the field here -- this allows the name to be validated
        # per the schema later
        bs_data["name"] = bs_name
    elif bs_data["name"] != bs_name:
        # All keys in the boot_sets mapping must match the 'name' fields in the
        # boot sets to which they map (if they contain a 'name' field).
        raise ParsingException(f"boot_sets key ({bs_name}) does not match 'name' "
                               f"field of corresponding boot set ({bs_data['name']})")

    # Validate the boot set architecture
    try:
        validate_boot_set_arch(bs_data)
    except CannotValidateBootSetArch as err:
        LOGGER.warning('%s', bs_data)
        LOGGER.warning("Cannot validate boot set architecture for boot set '%s': %s", bs_name, err)
    except Exception as err:
        raise ParsingException(
            f"Error found validating arch of boot set '{bs_name}': {exc_type_msg(err)}") from err

    # Validate that the boot set has at least one of the HARDWARE_SPECIFIER_FIELDS
    if not any(field_name in bs_data for field_name in HARDWARE_SPECIFIER_FIELDS):
        raise ParsingException(f"Boot set {bs_name} has none of the following "
                               f"fields: {HARDWARE_SPECIFIER_FIELDS}")

    # Last thing to do is validate/sanitize the node_list field, if it is present
    try:
        node_list = bs_data["node_list"]
    except KeyError:
        return

    # Make sure it is a list
    if not isinstance(node_list, list):
        raise ParsingException(f"Boot set {bs_name} has 'node_list' of invalid type")

    new_node_list = []
    for node in node_list:
        # Make sure it is a list of strings
        if not isinstance(node, str):
            raise ParsingException(f"Boot set {bs_name} 'node_list' contains non-string element")

        # If reject_nids is set, raise an exception if any member of the node list
        # begins with 'nid'
        if reject_nids and node[:3] == 'nid':
            raise ParsingException(f"reject_nids: Boot set {bs_name} 'node_list' contains a NID")

        # Canonize the xname and append it to the node list
        new_node_list.append(canonize_xname(node))

    # Update the node_list value in the boot set with the canonized version
    bs_data["node_list"] = new_node_list
