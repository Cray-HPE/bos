#
# MIT License
#
# (C) Copyright 2021-2023 Hewlett Packard Enterprise Development LP
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

from bos.common.tenant_utils import get_tenant_from_header, get_tenant_aware_key, reject_invalid_tenant
from bos.server.models.v2_session_template import V2SessionTemplate as SessionTemplate  # noqa: E501
from bos.server import redis_db_utils as dbutils
from bos.server.utils import _canonize_xname
from .boot_set import validate_boot_sets

LOGGER = logging.getLogger('bos.server.controllers.v2.sessiontemplates')
DB = dbutils.get_wrapper(db='session_templates')
BASEKEY = "/sessionTemplates"

EXAMPLE_BOOT_SET = {
    "type": "your-boot-type",
    "etag": "your_boot_image_etag",
    "kernel_parameters": "your-kernel-parameters",
    "cfs": {"configuration": "bootset-specific-cfs-override"},
    "node_list": [
        "xname1", "xname2", "xname3"],
    "path": "your-boot-path",
    "rootfs_provider": "your-rootfs-provider",
    "rootfs_provider_passthrough": "your-rootfs-provider-passthrough"}

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
    """PUT /v2/sessiontemplate

    Creates a new session template. # noqa: E501
    """
    LOGGER.debug("PUT /v2/sessiontemplate invoked put_sessiontemplate")
    if connexion.request.is_json:
        LOGGER.debug("connexion.request.is_json")
        LOGGER.debug("type=%s", type(connexion.request.get_json()))
        LOGGER.debug("Received: %s", connexion.request.get_json())
    else:
        return "PUT must be in JSON format", 400

    try:
        data = connexion.request.get_json()
    except Exception as err:
        return connexion.problem(
            status=400, title="Error parsing the data provided.",
            detail=str(err))

    template_data = data

    try:
        """Convert the JSON request data into a SessionTemplate object.
           Any exceptions caught here would be generated from the model
           (i.e. bos.server.models.session_template).
           An example is an exception for a session template name that
           does not conform to Kubernetes naming convention.
           In this case return 400 with a description of the specific error.
        """
        SessionTemplate.from_dict(template_data)
    except Exception as err:
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
    LOGGER.debug("get_sessiontemplates: Fetching sessions.")
    response = _get_filtered_templates(tenant=get_tenant_from_header())
    return response, 200


@dbutils.redis_error_handler
def get_v2_sessiontemplate(session_template_id):
    """
    GET /v2/sessiontemplate

    Get the session template by session template ID
    """
    LOGGER.debug("get_sessiontemplate by ID: %s", session_template_id)  # noqa: E501
    template_key = get_tenant_aware_key(session_template_id, get_tenant_from_header())
    if template_key not in DB:
        return connexion.problem(
            status=404, title="Sessiontemplate could not found.",
            detail="Sessiontemplate {} could not be found".format(session_template_id))
    template = DB.get(template_key)
    return template, 200


@dbutils.redis_error_handler
def get_v2_sessiontemplatetemplate():
    """
    GET /v2/sessiontemplatetemplate

    Get the example session template
    """
    return EXAMPLE_SESSION_TEMPLATE, 200


@dbutils.redis_error_handler
def delete_v2_sessiontemplate(session_template_id):
    """
    DELETE /v2/sessiontemplate

    Delete the session template by session template ID
    """
    LOGGER.debug("delete_sessiontemplate by ID: %s", session_template_id)
    template_key = get_tenant_aware_key(session_template_id, get_tenant_from_header())
    if template_key not in DB:
        return connexion.problem(
            status=404, title="Sessiontemplate could not found.",
            detail="Sessiontemplate {} could not be found".format(session_template_id))
    return DB.delete(template_key), 204


@dbutils.redis_error_handler
def patch_v2_sessiontemplate(session_template_id):
    """
    PATCH /v2/sessiontemplate

    Patch the session template by session template ID
    """
    LOGGER.debug("PATCH /v2/sessiontemplate invoked patch_sessiontemplate with ID: %s", session_template_id)
    template_key = get_tenant_aware_key(session_template_id, get_tenant_from_header())
    if template_key not in DB:
        return connexion.problem(
            status=404, title="Sessiontemplate could not found.",
            detail="Sessiontemplate {} could not be found".format(session_template_id))

    if connexion.request.is_json:
        LOGGER.debug("connexion.request.is_json")
        LOGGER.debug("type=%s", type(connexion.request.get_json()))
        LOGGER.debug("Received: %s", connexion.request.get_json())
    else:
        return "Patch must be in JSON format", 400

    try:
        data = connexion.request.get_json()
    except Exception as err:
        return connexion.problem(
            status=400, title="Error parsing the data provided.",
            detail=str(err))

    template_data = data

    try:
        """Convert the JSON request data into a SessionTemplate object.
           Any exceptions caught here would be generated from the model
           (i.e. bos.server.models.session_template).
           An example is an exception for a session template name that
           does not confirm to Kubernetes naming convention.
           In this case return 400 with a description of the specific error.
        """
        SessionTemplate.from_dict(template_data)
    except Exception as err:
        return connexion.problem(
            status=400, title="The session template could not be created.",
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
