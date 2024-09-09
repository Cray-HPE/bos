#
# MIT License
#
# (C) Copyright 2023-2024 Hewlett Packard Enterprise Development LP
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

from bos.common.tenant_utils import get_tenant_aware_key
from bos.common.utils import exc_type_msg
from bos.server.schema import validator

from .defs import LOGGER, TEMP_DB, ValidationError


def check_session(key: str|bytes, data: dict) -> None:
    """
    Raises a ValidationError if the data contains fatal errors.
    """
    try:
        name = data["name"]
    except KeyError as exc:
        raise ValidationError("Missing required 'name' field") from exc
    try:
        validator.validate(name, "V2SessionName")
    except Exception as exc:
        LOGGER.error(exc_type_msg(exc))
        raise ValidationError("Name does not follow schema") from exc
    tenant = get_validate_tenant(data)
    check_keys(key, get_tenant_aware_key(name, tenant))


def check_component(key: str|bytes, data: dict) -> None:
    """
    Raises a ValidationError if the data contains fatal errors.
    """
    try:
        name = data["id"]
    except KeyError as exc:
        raise ValidationError("Missing required 'id' field") from exc
    try:
        validator.validate(name, "V2ComponentId")
    except Exception as exc:
        LOGGER.error(exc_type_msg(exc))
        raise ValidationError("id does not follow schema") from exc
    check_keys(key, name)


def get_validate_tenant(data: dict) -> str|None:
    """
    If no tenant field present, return None.
    If the tenant field value is valid, return it.
    Otherwise, raise ValidationError
    """
    tenant = data.get("tenant", None)
    if tenant is not None:
        try:
            validator.validate(tenant, "V2TenantName")
        except Exception as exc:
            LOGGER.error(exc_type_msg(exc))
            raise ValidationError("Tenant name does not follow schema") from exc
    return tenant


def get_validate_bootset_path(bsname: str, bsdata: dict) -> str:
    try:
        path = bsdata["path"]
    except KeyError as exc:
        raise ValidationError(f"Boot set '{bsname}' missing required 'path' field") from exc
    try:
        validator.validate(path, "BootManifestPath")
    except Exception as exc:
        LOGGER.error(exc_type_msg(exc))
        raise ValidationError(f"Boot set '{bsname}' has invalid 'path' field") from exc
    return path


def check_keys(actual: str|bytes, expected: str|bytes) -> str|None:
    """
    Converts both keys to strings.
    Raises ValidationError if the strings do not match
    """
    if isinstance(actual, bytes):
        actual = actual.decode()
    if isinstance(expected, bytes):
        expected = expected.decode()
    if actual != expected:
        raise ValidationError(f"Actual DB key ('{actual}') does not match expected key ('{expected}')")


def is_valid_available_template_name(name: str, tenant: str|None) -> bool:
    if get_tenant_aware_key(name, tenant) in TEMP_DB:
        return False
    try:
        validator.validate(name, "SessionTemplateName")
    except Exception:
        return False
    return True
