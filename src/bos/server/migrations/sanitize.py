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

import copy
import itertools
import logging
import string
from typing import cast

from bos.common.tenant_utils import get_tenant_aware_key
from bos.common.types.general import JsonDict
from bos.common.types.templates import BOOT_SET_DEFAULT_ARCH as DEFAULT_ARCH
from bos.common.types.templates import BOOT_SET_HARDWARE_SPECIFIER_FIELDS as HARDWARE_SPECIFIER_FIELDS
from bos.server.schema import validator

from .db import TEMP_DB, delete_component, delete_session, delete_template
from .validate import (ValidationError,
                       check_component,
                       check_session,
                       check_keys,
                       get_required_field,
                       get_validate_tenant,
                       is_valid_available_template_name,
                       validate_bootset_path,
                       validate_against_schema)

LOGGER = logging.getLogger(__name__)

ALPHANUMERIC = string.ascii_letters + string.digits
TEMPLATE_NAME_CHARACTERS = ALPHANUMERIC + '-._'


def sanitize_component(key: str, data: JsonDict) -> None:
    """
    If the id field is missing or invalid, delete the component
    """
    try:
        check_component(key, data)
    except ValidationError as exc:
        delete_component(key, str(exc))


def sanitize_session(key: str, data: JsonDict) -> None:
    """
    If the name field is missing, or if the name or tenant fields are invalid, delete the session.
    """
    try:
        check_session(key, data)
    except ValidationError as exc:
        delete_session(key, str(exc))


def sanitize_session_template(key: str, data: JsonDict) -> None:
    """
    Session templates are the things most likely to run afoul of the API spec.
    This attempts to automatically fix them if at all possible, only deleting them
    as a last resort.
    """
    try:
        _sanitize_session_template(key, data)
    except ValidationError as exc:
        delete_template(key, str(exc))


def _sanitize_session_template(key: str, data: JsonDict) -> None:
    """
    Validates and tries to sanitize the session template.
    If there are correctable errors, the function will update the database
    to fix them.
    If there are uncorrectable errors, the function deletes the template.
    """
    # Validate presence of required name and boot_sets fields
    name = get_required_field("name", data)
    boot_sets = get_required_field("boot_sets", data)

    # Validate that name field is a string
    if not isinstance(name, str):
        raise ValidationError("'name' field has non-string value")

    # Validate that if there is a non-None tenant field, it follows the schema
    tenant = get_validate_tenant(data)

    # Make sure that the boot_set field is not empty and correct type
    if not isinstance(boot_sets, dict):
        raise ValidationError("'boot_sets' field value has invalid type")
    if not boot_sets:
        raise ValidationError("'boot_sets' field value is empty")
    # And make sure that it maps from strings to dicts
    for bs_key, bs_data in boot_sets.items():
        if not isinstance(bs_key, str):
            raise ValidationError("'boot_sets' dict has at least one non-string key")
        if not isinstance(bs_data, dict):
            raise ValidationError("'boot_sets' dict has at least one non-dict value")

    # Make a copy of the session template. If we identify problems, we will see if we can correct
    # them in the copy. While copying, remove any fields that are no longer in the spec
    new_data = {
        k: copy.deepcopy(v)
        for k, v in data.items() if k in validator.session_template_fields
    }

    # Check and sanitize each boot set
    # Above, we validated that data["boot_sets"] was a dict, and new_data is just a copy of
    # data, with invalid fields removed. We know that boot_sets is a valid field, so we
    # know that new_data["boot_sets"] is a dict. We also know that data overall is a JsonDict,
    # which tells us that any dicts inside of it must also be JsonDicts.
    # We use a cast in the following line to convince mypy of this
    for bsname, bsdata in cast(JsonDict, new_data["boot_sets"]).items():
        # Earlier we validated that bsname must be a string, and bsdata must be a dict, so
        # again we use casts to convince mypy of this
        sanitize_bootset(cast(str, bsname), cast(JsonDict, bsdata))

    sanitize_description_field(new_data)
    sanitize_cfs_field(new_data)

    new_name = get_unused_legal_template_name(name, tenant)

    if new_name == name:
        # Name did not change
        check_keys(key, get_tenant_aware_key(name, tenant))

        validate_against_schema(new_data, "V2SessionTemplate")

        if data == new_data:
            # Data did not change, so nothing to do
            return

        # This means the data changed, so we need to update the entry under the existing key
        LOGGER.warning(
            "Updating session template to comply with the BOS API schema")
        LOGGER.warning("Old template data: %s", data)
        LOGGER.warning("New template data: %s", new_data)
        TEMP_DB.put(key, new_data)
        return

    # Name changed
    base_msg = f"Renaming session template '{name}' (tenant: {tenant}) to new name '{new_name}'"
    if data == new_data:
        LOGGER.warning(base_msg)
    else:
        LOGGER.warning("%s and updating it to comply with the BOS API schema",
                       base_msg)

    delete_template(key)

    new_key = get_tenant_aware_key(new_name, tenant)
    LOGGER.info("Old DB key = '%s', new DB key = '%s'", key, new_key)

    new_data["name"] = new_name
    log_rename_in_template_description(name, new_data)

    LOGGER.warning("Old template data: %s", data)
    LOGGER.warning("New template data: %s", new_data)
    try:
        validate_against_schema(new_data, "V2SessionTemplate")
    except ValidationError:
        LOGGER.error(
            "New session template does not follow schema -- it will not be saved"
        )
        return

    TEMP_DB.put(new_key, new_data)


def sanitize_description_field(data: JsonDict) -> None:
    """
    Ensure that the description field (if present) is a string that is <= 1023 characters long.
    Delete or truncate it as needed.
    """
    try:
        description = data["description"]
    except KeyError:
        # If there is no description field, nothing for us to do
        return

    # Delete it if it is empty
    if not description:
        del data["description"]
        return

    # Log a warning and delete it if it is not a string
    if not isinstance(description, str):
        LOGGER.warning(
            "Removing non-string 'description' field from session template")
        del data["description"]
        return

    # Truncate it if it is too long
    if len(description) > 1023:
        data["description"] = description[:1023]


def sanitize_bootset(bsname: str, bsdata: JsonDict) -> None:
    """
    Corrects in-place bsdata.
    Raises a ValidationError if this proves impossible.
    """
    # Every boot_set must have a valid path set
    validate_bootset_path(bsname, bsdata)

    # The type field is required and 's3' is its only legal value
    # So rather than even checking it, just set it to 's3'
    bsdata["type"] = "s3"

    # Delete the name field, if it is present -- it is redundant and should not
    # be stored inside the boot set under the current API spec
    bsdata.pop("name", None)

    # If the arch field is not present, set it to its default value
    if "arch" not in bsdata:
        bsdata["arch"] = DEFAULT_ARCH

    # Remove any fields that are no longer in the spec
    bad_fields = [
        field for field in bsdata if field not in validator.boot_set_fields
    ]
    for field in bad_fields:
        del bsdata[field]

    # Sanitize the cfs field, if any
    try:
        sanitize_cfs_field(bsdata)
    except ValidationError as exc:
        raise ValidationError(f"Boot set '{bsname}' {exc}") from exc

    nonempty_node_field_found = False

    # Use list() since we will be modifying the dict while iterating over its contents
    for field, value in list(bsdata.items()):
        # We have already dealt with 'cfs', 'path', and 'type', so we can skip those
        if field in {'cfs', 'path', 'type'}:
            continue

        # Delete None-valued fields that are not nullable (No boot set fields are nullable)
        if value is None:
            del bsdata[field]
            continue

        if field != 'rootfs_provider' and field not in HARDWARE_SPECIFIER_FIELDS:
            continue

        # rootfs_provider and the node-specifier fields are optional* but if present,
        # are not allowed to have an empty value.
        # So if we find any set to an empty values, delete it.
        #
        # * The node-specifier fields are each individually optional, but one of them must
        #   be set
        if not value:
            del bsdata[field]
        elif field in HARDWARE_SPECIFIER_FIELDS:
            nonempty_node_field_found = True

    # Validate that at least one of the required node-specified fields is present
    if nonempty_node_field_found:
        return

    raise ValidationError(
        f"Boot set '{bsname}' has no non-empty node fields ({HARDWARE_SPECIFIER_FIELDS})"
    )


def sanitize_cfs_field(data: JsonDict) -> None:
    """
    If the 'cfs' field is present:
    * If it's mapped to None, remove it
    * If it isn't a dict, raise a ValidationError
    * Remove any invalid fields from it
    * Delete the configuration field if it is empty or null
    * If (after the above) the cfs dict is empty, remove it.
    """
    try:
        cfs = data["cfs"]
    except KeyError:
        # If no CFS field, nothing to sanitize
        return

    # The CFS field is not nullable, so if it is mapped to None, delete it
    # Also delete it if it is empty, since that is the same effect as it not being present
    if not cfs:
        del data["cfs"]
        return

    # If it does not map to a dictionary, raise an exception
    if not isinstance(cfs, dict):
        raise ValidationError("'cfs' field value has invalid type")

    # Remove any fields that are no longer in the spec
    bad_fields = [field for field in cfs if field not in validator.cfs_fields]
    for field in bad_fields:
        del cfs[field]

    if "configuration" in cfs:
        # The configuration field is not nullable, so if it maps to None, delete it
        # Also delete it if it is empty, since that is the same effect as it not being present
        if not cfs["configuration"]:
            del cfs["configuration"]

    # If this results in the cfs field being empty now, delete it
    if not cfs:
        del data["cfs"]


def get_unused_legal_template_name(name: str, tenant: str | None) -> str:
    """
    If the current name is legal, return it unchanged.
    Otherwise, try to find a name which is not in use and which is legal per the spec.
    Returns the new name if successful, otherwise raises ValidationError
    """
    try:
        validate_against_schema(name, "SessionTemplateName")
        return name
    except ValidationError:
        # If the name has no legal characters at all, or in the (hopefully unlikely) case that it
        # is 0 length, make no attempt to salvage it. Otherwise, we will try to find a good name
        if not name or not any(c in TEMPLATE_NAME_CHARACTERS for c in name):
            raise

    if tenant:
        LOGGER.warning(
            "Session template name '%s' (tenant: %s) does not follow schema. "
            "Will attempt to rename to a legal name", name, tenant)
    else:
        LOGGER.warning(
            "Session template name '%s' does not follow schema. "
            "Will attempt to rename to a legal name", name)

    # Strip out illegal characters, but replace spaces with underscores and prepend 'auto_renamed_'
    new_name_base = 'auto_renamed_' + ''.join(
        [c for c in name.replace(' ', '_') if c in TEMPLATE_NAME_CHARACTERS])

    # Trim to 127 characters, if it exceeds that
    new_name = new_name_base[:127]

    # At this point the only thing preventing this from being a legal name would be if the final
    # character is not alphanumeric
    if new_name[-1] in ALPHANUMERIC:
        if is_valid_available_template_name(new_name, tenant):
            return new_name

    # Trying all 2 character alphanumeric suffixes gives 1953 options, which is enough of an effort
    # for us to make here.
    for suffix_length in range(1, 3):
        for suffix in itertools.combinations_with_replacement(
                ALPHANUMERIC, suffix_length):
            new_name = f'{new_name_base[:126-suffix_length]}_{suffix}'
            if is_valid_available_template_name(new_name, tenant):
                return new_name

    if tenant:
        LOGGER.error(
            "Unable to find unused valid new name for session template '%s' (tenant: %s)",
            name, tenant)
    else:
        LOGGER.error("Unable to find unused valid new name for session template '%s'", name)
    raise ValidationError("Name does not follow schema")


def log_rename_in_template_description(old_name: str, data: JsonDict) -> None:
    """
    If possible, update the session template description field to record the previous name of this
    template. Failing that, if possible, at least record that it was renamed.
    """
    rename_messages = [
        f"Former name: {old_name}", "Renamed during BOS upgrade",
        "Auto-renamed", "Renamed"
    ]

    current_description = data.get("description", "")
    for msg in rename_messages:
        new_description = f"{current_description}; {msg}" if current_description else msg
        if len(new_description) <= 1023:
            data["description"] = new_description
            return
