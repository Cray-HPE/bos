#
# MIT License
#
# (C) Copyright 2021-2025 Hewlett Packard Enterprise Development LP
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
from typing import Literal, cast

from connexion.lifecycle import ConnexionResponse as CxResponse

from bos.common.tenant_utils import (get_tenant_from_header,
                                     reject_invalid_tenant)
from bos.common.types.templates import SessionTemplate, remove_empty_cfs_field
from bos.common.utils import exc_type_msg
from bos.server import redis_db_utils as dbutils
from bos.server.controllers.utils import _400_bad_request, _404_tenanted_resource_not_found
from bos.server.schema import validator
from bos.server.utils import get_request_json
from .boot_set import validate_boot_sets, validate_sanitize_boot_sets

LOGGER = logging.getLogger(__name__)
DB = dbutils.SessionTemplateDBWrapper()

EXAMPLE_BOOT_SET = {
    "type": "s3",
    "etag": "boot-image-s3-etag",
    "kernel_parameters": "your-kernel-parameters",
    "cfs": {
        "configuration": "bootset-specific-cfs-override"
    },
    "node_list": ["xname1", "xname2", "xname3"],
    "path": "s3://boot-images/boot-image-ims-id/manifest.json",
    "rootfs_provider": "cpss3",
    "rootfs_provider_passthrough":
    "dvs:api-gw-service-nmn.local:300:hsn0,nmn0:0"
}

EXAMPLE_SESSION_TEMPLATE = {
    "boot_sets": {
        "name_your_boot_set": EXAMPLE_BOOT_SET
    },
    "cfs": {
        "configuration": "default-sessiontemplate-cfs-config"
    },
    "enable_cfs": True,
    "name": "name-your-template"
}


@reject_invalid_tenant
@dbutils.redis_error_handler
def put_v2_sessiontemplate(
    session_template_id: str
) -> tuple[SessionTemplate, Literal[200]] | CxResponse:  # noqa: E501
    """PUT /v2/sessiontemplates

    Creates a new session template. # noqa: E501
    """
    LOGGER.debug("PUT /v2/sessiontemplates/%s invoked put_v2_sessiontemplate",
                 session_template_id)
    try:
        template_data = cast(SessionTemplate, get_request_json())
    except Exception as err:
        LOGGER.error("Error parsing PUT '%s' request data: %s",
                     session_template_id, exc_type_msg(err))
        return _400_bad_request(f"Error parsing the data provided: {err}")

    try:
        validate_sanitize_session_template(session_template_id, template_data)
    except Exception as err:
        LOGGER.error("Error creating session template '%s': %s",
                     session_template_id, exc_type_msg(err))
        LOGGER.debug("Full template: %s", template_data)
        return _400_bad_request(f"The session template could not be created: {err}")

    tenant = get_tenant_from_header() or None
    template_data['tenant'] = tenant
    DB.tenant_aware_put(session_template_id, tenant, template_data)
    return template_data, 200


@dbutils.redis_error_handler
def get_v2_sessiontemplates() -> tuple[list[SessionTemplate], Literal[200]]:  # noqa: E501
    """
    GET /v2/sessiontemplates

    List all sessiontemplates
    """
    LOGGER.debug("GET /v2/sessiontemplates invoked get_v2_sessiontemplates")
    tenant=get_tenant_from_header()
    if tenant:
        def _matches_filter(data: SessionTemplate) -> SessionTemplate | None:
            return data if tenant == data.get("tenant") else None
        response = DB.get_all_filtered(filter_func=_matches_filter)
    else:
        response = DB.get_all()
    LOGGER.debug("get_v2_sessiontemplates returning %d templates",
                 len(response))
    return response, 200


@dbutils.redis_error_handler
def get_v2_sessiontemplate(
    session_template_id: str
) -> tuple[SessionTemplate, Literal[200]] | CxResponse:
    """
    GET /v2/sessiontemplates

    Get the session template by session template ID
    """
    LOGGER.debug("GET /v2/sessiontemplates/%s invoked get_v2_sessiontemplate",
                 session_template_id)
    tenant = get_tenant_from_header()
    template = DB.tenant_aware_get(session_template_id, tenant)
    if template is None:
        if tenant:
            LOGGER.warning("Session template not found for tenant '%s': %s", tenant,
                           session_template_id)
        else:
            LOGGER.warning("Session template not found: %s", session_template_id)
        return _404_template_not_found(resource_id=session_template_id, tenant=tenant)
    return template, 200


@dbutils.redis_error_handler
def get_v2_sessiontemplatetemplate() -> tuple[SessionTemplate, Literal[200]]:
    """
    GET /v2/sessiontemplatetemplate

    Get the example session template
    """
    LOGGER.debug(
        "GET /v2/sessiontemplatetemplate invoked get_v2_sessiontemplatetemplate"
    )
    return EXAMPLE_SESSION_TEMPLATE, 200


@dbutils.redis_error_handler
def delete_v2_sessiontemplate(session_template_id: str) -> tuple[None, Literal[204]] | CxResponse:
    """
    DELETE /v2/sessiontemplates

    Delete the session template by session template ID
    """
    LOGGER.debug(
        "DELETE /v2/sessiontemplates/%s invoked delete_v2_sessiontemplate",
        session_template_id)
    tenant = get_tenant_from_header()
    template = DB.tenant_aware_get_and_delete(session_template_id, tenant)
    if template is None:
        if tenant:
            LOGGER.warning("Session template not found for tenant '%s': %s", tenant,
                           session_template_id)
        else:
            LOGGER.warning("Session template not found: %s", session_template_id)
        return _404_template_not_found(resource_id=session_template_id, tenant=tenant)
    return None, 204


@dbutils.redis_error_handler
def patch_v2_sessiontemplate(
    session_template_id: str
) -> tuple[SessionTemplate, Literal[200]] | CxResponse:
    """
    PATCH /v2/sessiontemplates

    Patch the session template by session template ID
    """
    LOGGER.debug(
        "PATCH /v2/sessiontemplates/%s invoked patch_v2_sessiontemplate",
        session_template_id)
    tenant = get_tenant_from_header()
    if not DB.has_tenanted_entry(session_template_id, tenant):
        if tenant:
            LOGGER.warning("Session template not found for tenant '%s': %s", tenant,
                           session_template_id)
        else:
            LOGGER.warning("Session template not found: %s", session_template_id)
        return _404_template_not_found(resource_id=session_template_id, tenant=tenant)

    try:
        template_data = cast(SessionTemplate, get_request_json())
    except Exception as err:
        LOGGER.error("Error parsing PATCH '%s' request data: %s",
                     session_template_id, exc_type_msg(err))
        return _400_bad_request(f"Error parsing the data provided: {err}")

    try:
        validate_sanitize_session_template(session_template_id, template_data)
    except Exception as err:
        LOGGER.error("Error patching session template '%s': %s",
                     session_template_id, exc_type_msg(err))
        return _400_bad_request(f"The session template could not be patched: {err}")

    return DB.tenant_aware_patch(session_template_id, tenant, template_data), 200


@dbutils.redis_error_handler
def validate_v2_sessiontemplate(
    session_template_id: str
) -> tuple[str, Literal[200]] | CxResponse:
    """
    Validate a V2 session template. Look for missing elements or errors that would prevent
    a session from being launched using this template.
    """
    LOGGER.debug(
        "GET /v2/sessiontemplatesvalid/%s invoked validate_v2_sessiontemplate",
        session_template_id)
    response = get_v2_sessiontemplate(session_template_id)
    if isinstance(response, CxResponse):
        # This means it was an error, so we just pass it up
        return response

    # Otherwise it should be a tuple of data and 200 status code
    data, _ = response

    # We assume boot because it and reboot are the most demanding from a validation
    # standpoint.
    operation = "boot"

    _error_code, msg = validate_boot_sets(data, operation, session_template_id)
    # We return 200 because the request itself was successful even if the session template
    # is invalid.
    return msg, 200


def validate_sanitize_session_template(session_template_id: str, template_data: SessionTemplate) -> None:
    """
    Used when creating or patching session templates
    """
    validate_sanitize_boot_sets(template_data)
    template_data['name'] = session_template_id

    remove_empty_cfs_field(template_data)

    # Validate this against the API schema
    # An exception will be raised if it does not follow it
    validator.validate_session_template(template_data)

    # We do not bother storing the boot set names inside the boot sets, so delete them.
    # We know every boot set has a name field because we verified that earlier in
    # validate_sanitize_boot_sets()
    for bs in template_data["boot_sets"].values():
        del bs["name"]

_404_template_not_found = partial(_404_tenanted_resource_not_found, resource_type="Session template")
