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
from bos.server.models.v2_session_template import V2SessionTemplate as SessionTemplate # noqa: E501
from bos.server import redis_db_utils as dbutils
from bos.server.utils import _canonize_xname
from .boot_set import validate_boot_sets

LOGGER = logging.getLogger('bos.server.controllers.v2.sessiontemplates')
DB = dbutils.get_wrapper(db='session_templates')

EXAMPLE_BOOT_SET = {
    "type": "s3",
    "etag": "boot-image-s3-etag",
    "kernel_parameters": "your-kernel-parameters",
    "cfs": {"configuration": "bootset-specific-cfs-override"},
    "node_list": [
        "xname1", "xname2", "xname3"],
    "path": "s3://boot-images/boot-image-ims-id/manifest.json",
    "rootfs_provider": "cpss3",
    "rootfs_provider_passthrough": "dvs:api-gw-service-nmn.local:300:hsn0,nmn0:0"}

EXAMPLE_SESSION_TEMPLATE = {
    "boot_sets": {
        "name_your_boot_set": EXAMPLE_BOOT_SET},
    "cfs": {
        "configuration": "default-sessiontemplate-cfs-config"},
    "enable_cfs": True,
    "name": "name-your-template"}


def _sanitize_xnames(st_json):
    """
    Sanitize xnames - Canonize the xnames
    N.B. Because python passes object references by value you need to use
    the return value.  It will have no impact on the inputted object.
    Args:
      st_json (dict): The Session Template as a JSON object

    Returns:
      The Session Template with all of the xnames sanitized
    """
    if 'boot_sets' in st_json:
        for boot_set in st_json['boot_sets']:
            if 'node_list' in st_json['boot_sets'][boot_set]:
                clean_nl = [_canonize_xname(node) for node in
                            st_json['boot_sets'][boot_set]['node_list']]
                st_json['boot_sets'][boot_set]['node_list'] = clean_nl
    return st_json


@reject_invalid_tenant
@dbutils.redis_error_handler
def put_v2_sessiontemplate(session_template_id):  # noqa: E501
    """PUT /v2/sessiontemplates

    Creates a new session template. # noqa: E501
    """
    LOGGER.debug("PUT /v2/sessiontemplates/%s invoked put_v2_sessiontemplate", session_template_id)
    if connexion.request.is_json:
        LOGGER.debug("connexion.request.is_json")
        LOGGER.debug("type=%s", type(connexion.request.get_json()))
        LOGGER.debug("Received: %s", connexion.request.get_json())
    else:
        return "PUT must be in JSON format", 400

    try:
        data = connexion.request.get_json()
    except Exception as err:
        LOGGER.error("Error parsing request data: %s", exc_type_msg(err))
        return connexion.problem(
            status=400, title="Error parsing the data provided.",
            detail=str(err))

    template_data = data

    try:
        # Convert the JSON request data into a SessionTemplate object.
        # Any exceptions caught here would be generated from the model
        # (i.e. bos.server.models.session_template).
        # An example is an exception for a session template name that
        # does not conform to Kubernetes naming convention.
        # In this case return 400 with a description of the specific error.
        SessionTemplate.from_dict(template_data)
    except Exception as err:
        LOGGER.error("Error creating session template: %s", exc_type_msg(err))
        return connexion.problem(
            status=400, title="The session template could not be created.",
            detail=str(err))

    template_data = _sanitize_xnames(template_data)
    tenant = get_tenant_from_header()
    template_data['name'] = session_template_id
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
    LOGGER.debug("get_v2_sessiontemplates returning %d templates", len(response))
    return response, 200


@dbutils.redis_error_handler
def get_v2_sessiontemplate(session_template_id):
    """
    GET /v2/sessiontemplates

    Get the session template by session template ID
    """
    LOGGER.debug("GET /v2/sessiontemplates/%s invoked get_v2_sessiontemplate", session_template_id)
    template_key = get_tenant_aware_key(session_template_id, get_tenant_from_header())
    if template_key not in DB:
        LOGGER.warning("Session template not found: %s", session_template_id)
        return connexion.problem(
            status=404, title="Sessiontemplate could not found.",
            detail=f"Sessiontemplate {session_template_id} could not be found")
    template = DB.get(template_key)
    return template, 200


@dbutils.redis_error_handler
def get_v2_sessiontemplatetemplate():
    """
    GET /v2/sessiontemplatetemplate

    Get the example session template
    """
    LOGGER.debug("GET /v2/sessiontemplatetemplate invoked get_v2_sessiontemplatetemplate")
    return EXAMPLE_SESSION_TEMPLATE, 200


@dbutils.redis_error_handler
def delete_v2_sessiontemplate(session_template_id):
    """
    DELETE /v2/sessiontemplates

    Delete the session template by session template ID
    """
    LOGGER.debug("DELETE /v2/sessiontemplates/%s invoked delete_v2_sessiontemplate",
                 session_template_id)
    template_key = get_tenant_aware_key(session_template_id, get_tenant_from_header())
    if template_key not in DB:
        LOGGER.warning("Session template not found: %s", session_template_id)
        return connexion.problem(
            status=404, title="Sessiontemplate could not found.",
            detail=f"Sessiontemplate {session_template_id} could not be found")
    return DB.delete(template_key), 204


@dbutils.redis_error_handler
def patch_v2_sessiontemplate(session_template_id):
    """
    PATCH /v2/sessiontemplates

    Patch the session template by session template ID
    """
    LOGGER.debug("PATCH /v2/sessiontemplates/%s invoked patch_v2_sessiontemplate",
                 session_template_id)
    template_key = get_tenant_aware_key(session_template_id, get_tenant_from_header())
    if template_key not in DB:
        LOGGER.warning("Session template not found: %s", session_template_id)
        return connexion.problem(
            status=404, title="Sessiontemplate could not found.",
            detail=f"Sessiontemplate {session_template_id} could not be found")

    if connexion.request.is_json:
        LOGGER.debug("connexion.request.is_json")
        LOGGER.debug("type=%s", type(connexion.request.get_json()))
        LOGGER.debug("Received: %s", connexion.request.get_json())
    else:
        return "Patch must be in JSON format", 400

    try:
        data = connexion.request.get_json()
    except Exception as err:
        LOGGER.error("Error parsing request data: %s", exc_type_msg(err))
        return connexion.problem(
            status=400, title="Error parsing the data provided.",
            detail=str(err))

    template_data = data

    try:
        # Convert the JSON request data into a SessionTemplate object.
        # Any exceptions caught here would be generated from the model
        # (i.e. bos.server.models.session_template).
        # An example is an exception for a session template name that
        # does not confirm to Kubernetes naming convention.
        # In this case return 400 with a description of the specific error.
        SessionTemplate.from_dict(template_data)
    except Exception as err:
        LOGGER.error("Error patching session template: %s", exc_type_msg(err))
        return connexion.problem(
            status=400, title="The session template could not be patched.",
            detail=str(err))

    template_data = _sanitize_xnames(template_data)
    template_data['name'] = session_template_id

    return DB.patch(template_key, template_data), 200


@dbutils.redis_error_handler
def validate_v2_sessiontemplate(session_template_id: str):
    """
    Validate a V2 session template. Look for missing elements or errors that would prevent
    a session from being launched using this template.
    """
    LOGGER.debug("GET /v2/sessiontemplatesvalid/%s invoked validate_v2_sessiontemplate",
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
