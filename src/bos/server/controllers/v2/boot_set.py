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
import logging
from bos.common.utils import exc_type_msg, requests_retry_session
from bos.operators.utils.boot_image_metadata import BootImageMetaData
from bos.operators.utils.boot_image_metadata.factory import BootImageMetaDataFactory
from bos.operators.utils.clients.ims import get_arch_from_image_data, get_image, \
                                            get_ims_id_from_s3_url, ImageNotFound
from bos.operators.utils.clients.s3 import S3Object, ArtifactNotFound
from bos.server.controllers.v2.options import OptionsData
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


class BootSetError(Exception):
    """
    Generic error class for fatal problems found during boot set validation
    """


class BootSetWarning(Exception):
    """
    Generic error class for non-fatal problems found during boot set validation
    """


class NonImsImage(BootSetWarning):
    """
    Raised to indicate the boot set boot image is not from IMS
    """


class BootSetArchMismatch(BootSetError):
    def __init__(self, bs_arch: str, expected_ims_arch: str, actual_ims_arch: str):
        super().__init__(f"Boot set arch '{bs_arch}' means IMS image arch should be "
                         f"'{expected_ims_arch}', but actual IMS image arch is '{actual_ims_arch}'")


class CannotValidateBootSetArch(BootSetWarning):
    def __init__(self, msg: str):
        super().__init__(f"Can't validate boot image arch: {msg}")


def validate_boot_sets(session_template: dict,
                       operation: str,
                       template_name: str,
                       options_data: OptionsData|None=None) -> tuple[str, int]:
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

    if options_data is None:
        options_data = OptionsData()

    warning_msgs = []
    for bs_name, bs in session_template['boot_sets'].items():
        bs_msg = partial(_bs_msg, template_name=template_name, bs_name=bs_name)
        try:
            bs_warning_msgs = _validate_boot_set(bs=bs, operation=operation,
                                                 options_data=options_data)
        except BootSetError as err:
            msg = bs_msg(str(err))
            LOGGER.error(msg)
            return BOOT_SET_ERROR, msg
        except Exception as err:
            LOGGER.error(
                bs_msg(f"Unexpected exception in _validate_boot_set: {exc_type_msg(err)}"))
            raise
        for msg in map(bs_msg, bs_warning_msgs):
            LOGGER.warning(msg)
            warning_msgs.append(msg)

    if warning_msgs:
        return BOOT_SET_WARNING, "; ".join(warning_msgs)

    return BOOT_SET_SUCCESS, "Valid"


def _bs_msg(msg: str, template_name: str, bs_name: str) -> str:
    """
    Shortcut for creating validation error/warning messages for a specific bootset
    """
    return f"Session template: '{template_name}' boot set: '{bs_name}': {msg}"


def _validate_boot_set(bs: dict, operation: str, options_data: OptionsData) -> list[str]:
    """
    Helper function for validate_boot_sets that performs validation on a single boot set.
    Raises BootSetError if fatal errors found.
    Returns a list of warning messages (if any)
    """
    warning_msgs = []

    # Verify that the hardware is specified
    specified = [bs.get(field, None)
                 for field in HARDWARE_SPECIFIER_FIELDS]
    if not any(specified):
        raise BootSetError(f"No non-empty hardware specifier field {HARDWARE_SPECIFIER_FIELDS}")
    try:
        if any(node[:3] == "nid" for node in bs["node_list"]):
            msg = "Has NID in 'node_list'"
            if options_data.reject_nids:
                raise BootSetError(msg)
            # Otherwise, log this as a warning -- even if reject_nids is not set,
            # BOS still doesn't support NIDs, so this is still undesirable
            warning_msgs.append(msg)
    except KeyError:
        # If there is no node_list field, not a problem
        pass

    if operation in ['boot', 'reboot']:
        # Verify that the boot artifacts exist
        try:
            image_metadata = BootImageMetaDataFactory(bs)()
        except Exception as err:
            raise BootSetError(f"Can't find boot artifacts. Error: {exc_type_msg(err)}") from err

        try:
            validate_ims_boot_image(bs, image_metadata, options_data)
        except BootSetWarning as err:
            warning_msgs.append(str(err))

        # Check boot artifacts' S3 headers
        for boot_artifact in ["kernel"]:
            try:
                artifact = getattr(image_metadata.boot_artifacts, boot_artifact)
                path = artifact ['link']['path']
                etag = artifact['link']['etag']
                obj = S3Object(path, etag)
                _ = obj.object_header
            except Exception as err:
                raise BootSetError(f"Can't find {boot_artifact} in "
                                   f"{image_metadata.manifest_s3_url.url}. "
                                   f"Error: {exc_type_msg(err)}") from err

        for boot_artifact in ["initrd", "boot_parameters"]:
            try:
                artifact = getattr(image_metadata.boot_artifacts, boot_artifact)
                if not artifact:
                    raise ArtifactNotFound()
                path = artifact ['link']['path']
                etag = artifact['link']['etag']
                obj = S3Object(path, etag)
                _ = obj.object_header
            except ArtifactNotFound as err:
                warning_msgs.append(
                    f"{image_metadata.manifest_s3_url.url} doesn't contain a {boot_artifact}")
            except Exception as err:
                warning_msgs.append(f"Can't find {boot_artifact} in "
                                    f"{image_metadata.manifest_s3_url.url}. "
                                    f"Warning: {exc_type_msg(err)}")

    return warning_msgs


def validate_ims_boot_image(bs: dict, image_metadata: BootImageMetaData,
                            options_data: OptionsData) -> None:
    """
    If the boot set architecture is not set to Other, check that the IMS image
    architecture matches the boot set architecture (treating a boot set architecture
    of Unknown as X86)

    Otherwise, at least validate whether the boot image is in IMS, if we expect it to be.
    """
    bs_arch = bs.get("arch", DEFAULT_ARCH)

    ims_id = get_ims_image_id(image_metadata)

    # If IMS being inaccessible is not a fatal error, then reduce the number
    # of retries we make, to prevent a lengthy delay
    num_retries = None if options_data.ims_errors_fatal else 4

    try:
        image_data = get_ims_image_data(ims_id, num_retries)
    except ImageNotFound as err:
        raise BootSetWarning(str(err)) from err
    except Exception as err:
        if options_data.ims_errors_fatal:
            raise err
        if bs_arch != 'Other':
            # This means that this error is preventing us from validating the
            # boot set architecture
            raise CannotValidateBootSetArch(str(err)) from err
        # We weren't going to be validating the architecture, since it is Other,
        # but we should still log this as a warning
        raise BootSetWarning(str(err)) from err

    if bs_arch == 'Other':
        raise CannotValidateBootSetArch("Boot set arch set to 'Other'")

    try:
        ims_image_arch = get_arch_from_image_data(image_data)
    except Exception as err:
        # This most likely indicates that the IMS image data we got wasn't even a dict
        if options_data.ims_errors_fatal:
            raise err
        raise BootSetWarning(str(err)) from err

    if EXPECTED_IMS_ARCH[bs_arch] != ims_image_arch:
        raise BootSetArchMismatch(bs_arch=bs_arch, expected_ims_arch=EXPECTED_IMS_ARCH[bs_arch],
                                  actual_ims_arch=ims_image_arch)


def validate_sanitize_boot_sets(template_data: dict, options_data: OptionsData|None=None) -> None:
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

    if options_data is None:
        options_data = OptionsData()

    # Finally, call validate_sanitize_boot_set on each boot set
    for bs_name, bs in boot_sets.items():
        validate_sanitize_boot_set(bs_name, bs, options_data=options_data)


def validate_sanitize_boot_set(bs_name: str, bs_data: dict, options_data: OptionsData) -> None:
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

    # Get the boot image metadata
    try:
        image_metadata = BootImageMetaDataFactory(bs_data)()
    except Exception as err:
        LOGGER.warning("Can't find boot artifacts: %s", exc_type_msg(err))
    else: # No exception was raised in try block
        # Validate the boot set IMS image
        try:
            validate_ims_boot_image(bs_data, image_metadata, options_data)
        except BootSetWarning as err:
            LOGGER.warning("Boot set '%s': %s", bs_name, err)
            LOGGER.warning('Boot set contents: %s', bs_data)
        except Exception as err:
            raise ParsingException(str(err)) from err

    # Validate that the boot set has at least one of the HARDWARE_SPECIFIER_FIELDS
    if not any(field_name in bs_data for field_name in HARDWARE_SPECIFIER_FIELDS):
        raise ParsingException(f"Boot set {bs_name} has none of the following "
                               f"fields: {HARDWARE_SPECIFIER_FIELDS}")

    # Validate that at least one of the HARDWARE_SPECIFIER_FIELDS is non-empty
    if not any(field_name in bs_data and bs_data[field_name]
               for field_name in HARDWARE_SPECIFIER_FIELDS):
        raise ParsingException(f"Boot set {bs_name} has no non-empty hardware-specifier fields: "
                               f"{HARDWARE_SPECIFIER_FIELDS}")

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
        if options_data.reject_nids and node[:3] == 'nid':
            raise ParsingException(f"reject_nids: Boot set {bs_name} 'node_list' contains a NID")

        # Canonize the xname and append it to the node list
        new_node_list.append(canonize_xname(node))

    # Update the node_list value in the boot set with the canonized version
    bs_data["node_list"] = new_node_list


def get_ims_image_id(image_metadata: BootImageMetaData) -> str:
    """
    If the image is an IMS image, return its ID.
    Raise NonImsImage otherwise,
    Note that this does not actually check IMS to see if the ID
    exists.
    """
    s3_url = image_metadata.manifest_s3_url
    ims_id = get_ims_id_from_s3_url(s3_url)
    if ims_id:
        return ims_id
    raise NonImsImage(f"Boot artifact S3 URL '{s3_url.url}' doesn't follow convention "
                      "for IMS images")


def get_ims_image_data(ims_id: str, num_retries: int|None=None) -> dict:
    """
    Query IMS to get the image data and return it,
    or raise an exception.
    """
    kwargs = { "image_id": ims_id }
    if num_retries is not None:
        # A pylint bug generates a false positive error for this call
        # https://github.com/pylint-dev/pylint/issues/2271
        kwargs['session'] = requests_retry_session(retries=4) # pylint: disable=redundant-keyword-arg
    return get_image(**kwargs)
