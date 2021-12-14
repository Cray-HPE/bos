# Copyright 2021 Hewlett Packard Enterprise Development LP
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
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# (MIT License)

import logging
import connexion
import json
import wget
import os

from bos.models.v2_session_template import V2SessionTemplate as SessionTemplate  # noqa: E501
from bos import redis_db_utils as dbutils
from bos.utils import _canonize_xname

LOGGER = logging.getLogger('bos.controllers.v2.sessiontemplates')
DB = dbutils.get_wrapper(db='session_templates')
BASEKEY = "/sessionTemplates"

EXAMPLE_BOOT_SET = {
    "type": "your-boot-type",
    "boot_ordinal": 1,
    "etag": "your_boot_image_etag",
    "kernel_parameters": "your-kernel-parameters",
    "network": "nmn",
    "node_list": [
        "xname1", "xname2", "xname3"],
    "path": "your-boot-path",
    "rootfs_provider": "your-rootfs-provider",
    "rootfs_provider_passthrough": "your-rootfs-provider-passthrough"}

EXAMPLE_SESSION_TEMPLATE = {
    "boot_sets": {
        "name_your_boot_set": EXAMPLE_BOOT_SET},
    "cfs": {
        "configuration": "desired-cfs-config"},
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


@dbutils.redis_error_handler
def put_sessiontemplate(session_template_id):  # noqa: E501
    """POST /v2/sessiontemplate

    Creates a new session template. # noqa: E501
    """
    LOGGER.debug("PUT /v2/sessiontemplate invoked put_sessiontemplate")
    if connexion.request.is_json:
        LOGGER.debug("connexion.request.is_json")
        LOGGER.debug("type=%s", type(connexion.request.get_json()))
        LOGGER.debug("Received: %s", connexion.request.get_json())
    else:
        return "Post must be in JSON format", 400

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
           (i.e. bos.models.session_template).
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
    return DB.put(session_template_id, template_data), 200


@dbutils.redis_error_handler
def get_sessiontemplates():  # noqa: E501
    """
    GET /v2/sessiontemplates

    List all sessiontemplates
    """
    LOGGER.debug("get_sessiontemplates: Fetching sessions.")
    response = DB.get_all()
    return response, 200


@dbutils.redis_error_handler
def get_sessiontemplate(session_template_id):
    """
    GET /v2/sessiontemplate

    Get the session template by session template ID
    """
    LOGGER.debug("get_sessiontemplate by ID: %s", session_template_id)  # noqa: E501
    if session_template_id not in DB:
        return connexion.problem(
            status=404, title="Sessiontemplate could not found.",
            detail="Sessiontemplate {} could not be found".format(session_template_id))
    template = DB.get(session_template_id)
    return template, 200


@dbutils.redis_error_handler
def get_sessiontemplatetemplate():
    """
    GET /v2/sessiontemplatetemplate

    Get the example session template
    """
    return EXAMPLE_SESSION_TEMPLATE, 200


@dbutils.redis_error_handler
def delete_sessiontemplate(session_template_id):
    """
    DELETE /v2/sessiontemplate

    Delete the session template by session template ID
    """
    LOGGER.debug("delete_sessiontemplate by ID: %s", session_template_id)
    if session_template_id not in DB:
        return connexion.problem(
            status=404, title="Sessiontemplate could not found.",
            detail="Sessiontemplate {} could not be found".format(session_template_id))
    return DB.delete(session_template_id), 204


@dbutils.redis_error_handler
def patch_sessiontemplate(session_template_id):
    """
    PATCH /v2/sessiontemplate

    Patch the session template by session template ID
    """
    LOGGER.debug("PATCH /v2/sessiontemplate invoked patch_sessiontemplate with ID: %s", session_template_id)

    if session_template_id not in DB:
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
           (i.e. bos.models.session_template).
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

    return DB.patch(session_template_id, template_data), 200
