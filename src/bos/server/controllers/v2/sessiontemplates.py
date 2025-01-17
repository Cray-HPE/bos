#
# MIT License
#
# (C) Copyright 2021-2024 Hewlett Packard Enterprise Development LP
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
import connexion

from bos.common.tenant_utils import get_tenant_from_header, get_tenant_aware_key, \
                                    reject_invalid_tenant
from bos.common.utils import exc_type_msg
from bos.server import redis_db_utils as dbutils
from bos.server.schema import validator
from bos.server.utils import get_request_json
from .boot_set import validate_boot_sets, validate_sanitize_boot_sets

LOGGER = logging.getLogger(__name__)
DB = dbutils.get_wrapper(db='session_templates')

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
def put_v2_sessiontemplate(session_template_id):  # noqa: E501
    """PUT /v2/sessiontemplates

    Creates a new session template. # noqa: E501
    """
    LOGGER.debug("PUT /v2/sessiontemplates/%s invoked put_v2_sessiontemplate",
                 session_template_id)
    try:
        template_data = get_request_json()
    except Exception as err:
        LOGGER.error("Error parsing PUT '%s' request data: %s",
                     session_template_id, exc_type_msg(err))
        return connexion.problem(status=400,
                                 title="Error parsing the data provided.",
                                 detail=str(err))

    try:
        validate_sanitize_session_template(session_template_id, template_data)
    except Exception as err:
        LOGGER.error("Error creating session template '%s': %s",
                     session_template_id, exc_type_msg(err))
        LOGGER.debug("Full template: %s", template_data)
        return connexion.problem(
            status=400,
            title="The session template could not be created.",
            detail=str(err))

    tenant = get_tenant_from_header()
    template_data['tenant'] = tenant
    template_key = get_tenant_aware_key(session_template_id, tenant)
    return DB.put(template_key, template_data), 200


@dbutils.redis_error_handler
def get_v2_sessiontemplates():  # noqa: E501
    """
    GET /v2/sessiontemplates

    List all sessiontemplates
    """
    LOGGER.debug("GET /v2/sessiontemplates invoked get_v2_sessiontemplates")
    response = _get_filtered_templates(tenant=get_tenant_from_header())
    LOGGER.debug("get_v2_sessiontemplates returning %d templates",
                 len(response))
    return response, 200


@dbutils.redis_error_handler
def get_v2_sessiontemplate(session_template_id):
    """
    GET /v2/sessiontemplates

    Get the session template by session template ID
    """
    LOGGER.debug("GET /v2/sessiontemplates/%s invoked get_v2_sessiontemplate",
                 session_template_id)
    template_key = get_tenant_aware_key(session_template_id,
                                        get_tenant_from_header())
    if template_key not in DB:
        LOGGER.warning("Session template not found: %s", session_template_id)
        return connexion.problem(
            status=404,
            title="Sessiontemplate could not found.",
            detail=f"Sessiontemplate {session_template_id} could not be found")
    template = DB.get(template_key)
    return template, 200


@dbutils.redis_error_handler
def get_v2_sessiontemplatetemplate():
    """
    GET /v2/sessiontemplatetemplate

    Get the example session template
    """
    LOGGER.debug(
        "GET /v2/sessiontemplatetemplate invoked get_v2_sessiontemplatetemplate"
    )
    return EXAMPLE_SESSION_TEMPLATE, 200


@dbutils.redis_error_handler
def delete_v2_sessiontemplate(session_template_id):
    """
    DELETE /v2/sessiontemplates

    Delete the session template by session template ID
    """
    LOGGER.debug(
        "DELETE /v2/sessiontemplates/%s invoked delete_v2_sessiontemplate",
        session_template_id)
    template_key = get_tenant_aware_key(session_template_id,
                                        get_tenant_from_header())
    if template_key not in DB:
        LOGGER.warning("Session template not found: %s", session_template_id)
        return connexion.problem(
            status=404,
            title="Sessiontemplate could not found.",
            detail=f"Sessiontemplate {session_template_id} could not be found")
    return DB.delete(template_key), 204


@dbutils.redis_error_handler
def patch_v2_sessiontemplate(session_template_id):
    """
    PATCH /v2/sessiontemplates

    Patch the session template by session template ID
    """
    LOGGER.debug(
        "PATCH /v2/sessiontemplates/%s invoked patch_v2_sessiontemplate",
        session_template_id)
    template_key = get_tenant_aware_key(session_template_id,
                                        get_tenant_from_header())
    if template_key not in DB:
        LOGGER.warning("Session template not found: %s", session_template_id)
        return connexion.problem(
            status=404,
            title="Sessiontemplate could not found.",
            detail=f"Sessiontemplate {session_template_id} could not be found")

    try:
        template_data = get_request_json()
    except Exception as err:
        LOGGER.error("Error parsing PATCH '%s' request data: %s",
                     session_template_id, exc_type_msg(err))
        return connexion.problem(status=400,
                                 title="Error parsing the data provided.",
                                 detail=str(err))

    try:
        validate_sanitize_session_template(session_template_id, template_data)
    except Exception as err:
        LOGGER.error("Error patching session template '%s': %s",
                     session_template_id, exc_type_msg(err))
        return connexion.problem(
            status=400,
            title="The session template could not be patched.",
            detail=str(err))

    return DB.patch(template_key, template_data), 200


@dbutils.redis_error_handler
def validate_v2_sessiontemplate(session_template_id: str):
    """
    Validate a V2 session template. Look for missing elements or errors that would prevent
    a session from being launched using this template.
    """
    LOGGER.debug(
        "GET /v2/sessiontemplatesvalid/%s invoked validate_v2_sessiontemplate",
        session_template_id)
    data, status_code = get_v2_sessiontemplate(session_template_id)

    if status_code != 200:
        return data, status_code

    # We assume boot because it and reboot are the most demanding from a validation
    # standpoint.
    operation = "boot"

    _error_code, msg = validate_boot_sets(data, operation, session_template_id)
    # We return 200 because the request itself was successful even if the session template
    # is invalid.
    return msg, 200


def _get_filtered_templates(tenant):
    response = DB.get_all()
    if any([tenant]):
        response = [r for r in response if _matches_filter(r, tenant)]
    return response


def _matches_filter(data, tenant):
    if tenant and tenant != data.get("tenant"):
        return False
    return True


def validate_sanitize_session_template(session_template_id, template_data):
    """
    Used when creating or patching session templates
    """
    validate_sanitize_boot_sets(template_data)
    template_data['name'] = session_template_id

    # Validate this against the API schema
    # An exception will be raised if it does not follow it
    validator.validate_session_template(template_data)

    # We do not bother storing the boot set names inside the boot sets, so delete them.
    # We know every boot set has a name field because we verified that earlier in
    # validate_sanitize_boot_sets()
    for bs in template_data["boot_sets"].values():
        del bs["name"]
