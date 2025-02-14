#
# MIT License
#
# (C) Copyright 2023-2025 Hewlett Packard Enterprise Development LP
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

from bos.common.tenant_utils import get_tenant_aware_key
from bos.common.types.general import JsonData, JsonDict
from bos.common.utils import exc_type_msg
from bos.server.schema import validator

from .db import TEMP_DB

LOGGER = logging.getLogger(__name__)


class ValidationError(Exception):
    """
    Raised by validation functions when they find problems
    """


def check_session(key: str | bytes, data: JsonDict) -> None:
    """
    Raises a ValidationError if the data contains fatal errors.
    """
    name = get_required_field("name", data)
    validate_against_schema(name, "V2SessionName")
    tenant = get_validate_tenant(data)
    expected_db_key = get_tenant_aware_key(name, tenant)
    check_keys(key, expected_db_key)


def check_component(key: str | bytes, data: JsonDict) -> None:
    """
    Raises a ValidationError if the data contains fatal errors.
    """
    compid = get_required_field("id", data)
    validate_against_schema(compid, "V2ComponentId")
    check_keys(key, compid)


def get_validate_tenant(data: JsonDict) -> str | None:
    """
    If no tenant field present, return None.
    If the tenant field value is valid, return it.
    Otherwise, raise ValidationError
    """
    tenant = data.get("tenant", None)
    if tenant is not None:
        validate_against_schema(tenant, "V2TenantName")
    return tenant


def validate_bootset_path(bsname: str, bsdata: JsonDict) -> None:
    try:
        path = get_required_field("path", bsdata)
    except ValidationError as exc:
        raise ValidationError(f"Boot set '{bsname}': {exc}") from exc
    try:
        validate_against_schema(path, "BootManifestPath")
    except ValidationError as exc:
        raise ValidationError(
            f"Boot set '{bsname}' has invalid 'path' field: {exc}") from exc


def check_keys(actual: str | bytes, expected: str | bytes) -> str | None:
    """
    Converts both keys to strings.
    Raises ValidationError if the strings do not match
    """
    if isinstance(actual, bytes):
        actual = actual.decode()
    if isinstance(expected, bytes):
        expected = expected.decode()
    if actual != expected:
        raise ValidationError(
            f"Actual DB key ('{actual}') does not match expected key ('{expected}')"
        )


def is_valid_available_template_name(name: str, tenant: str | None) -> bool:
    if get_tenant_aware_key(name, tenant) in TEMP_DB:
        return False
    try:
        validate_against_schema(name, "SessionTemplateName")
    except ValidationError:
        return False
    return True


def validate_against_schema(obj: JsonData, schema_name: str) -> None:
    """
    Raises a ValidationError if it does not follow the schema
    """
    try:
        validator.validate(obj, schema_name)
    except Exception as exc:
        LOGGER.error(exc_type_msg(exc))
        raise ValidationError(
            f"Does not follow {schema_name} schema: {obj}") from exc


def get_required_field(field: str, data: JsonDict) -> JsonData:
    """
    Returns the value of the field in the dict
    Raises ValiationError otherwise
    """
    try:
        return data[field]
    except KeyError as exc:
        raise ValidationError(f"Missing required '{field}' field") from exc
