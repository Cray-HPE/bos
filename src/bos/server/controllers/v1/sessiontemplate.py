#
# MIT License
#
# (C) Copyright 2019-2023 Hewlett Packard Enterprise Development LP
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
# Cray-provided controllers for the Boot Orchestration Service

import logging
import connexion
import json
import wget
import os

from bos.server import redis_db_utils as dbutils
from bos.server.models.v1_session_template import V1SessionTemplate as SessionTemplate  # noqa: E501
from bos.server.models.v1_session_template_example_properties import V1SessionTemplateExampleProperties \
                                                              as SessionTemplateExampleProperties  # noqa: E501
from bos.server.utils import _canonize_xname
from ..v2.sessiontemplates import get_v2_sessiontemplate, get_v2_sessiontemplates, delete_v2_sessiontemplate

LOGGER = logging.getLogger('bos.server.controllers.v1.sessiontemplate')
DB = dbutils.get_wrapper(db='session_templates')

# These are examples returned by the /v1/sessiontemplatetemplate endpoint.
# The intention is that a CLI user will save them to a file, edit them, and then
# create a template via the CLI using the --file argument. When using the CLI,
# the template name is not read in from that file -- it is provided using its own
# argument. Because of this, this example template deliberately omits the "name" field.

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
    "description": "Describe your template",
    "enable_cfs": True}

SESSION_TEMPLATE_TEMPLATE = SessionTemplateExampleProperties.from_dict(EXAMPLE_SESSION_TEMPLATE)

def sanitize_xnames(st_json):
    """
    Sanitize xnames - Canonize the xnames
    N.B. Because python passes object references by value you need to use
    the return value.  It will have no impact on the inputted object.
    Args:
      st_json (string): The Session Template as a JSON object

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
def create_v1_sessiontemplate():  # noqa: E501
    """POST /v1/sessiontemplate

    Creates a new session template. # noqa: E501
    """
    LOGGER.debug("POST /v1/sessiontemplate invoked create_v1_sessiontemplate")
    if connexion.request.is_json:
        LOGGER.debug("connexion.request.is_json")
        LOGGER.debug("type=%s", type(connexion.request.get_json()))
        LOGGER.debug("Received: %s", connexion.request.get_json())
    else:
        return "Post must be in JSON format", 400

    sessiontemplate = None

    try:
        """Convert the JSON request data into a SessionTemplate object.
           Any exceptions caught here would be generated from the model
           (i.e. bos.server.models.session_template).
           An example is an exception for a session template name that
           does not confirm to Kubernetes naming convention.
           In this case return 400 with a description of the specific error.
        """
        sessiontemplate = SessionTemplate.from_dict(connexion.request.get_json())
    except Exception as err:
        return connexion.problem(
            status=400, title="The session template could not be created.",
            detail=str(err))

    if sessiontemplate.template_url:
        """If a template URL was provided in the body treat this as a reference
           to a JSON session template structure which needs to be read and
           stored.
        """
        LOGGER.debug("create_v1_sessiontemplate template_url: %s", sessiontemplate.template_url)

        """Downloads the content locally into a file named after the uri.
           An optional 'out' parameter can be specified as the base dir
           for the file
        """
        sessionTemplateFile = ""
        try:
            sessionTemplateFile = wget.download(sessiontemplate.template_url)
            LOGGER.debug("Downloaded: %s", sessionTemplateFile)
        except Exception as err:
            return connexion.problem(
                status=400,
                title="Error while getting content from '{}'".format(
                    sessiontemplate.template_url),
                detail=str(err))

        # Read in the session template file
        with open(sessionTemplateFile, 'r') as f:
            st_json = json.load(f)
            if 'name' not in st_json.keys() or st_json['name'] == "":
                return connexion.problem(
                    status=400, title="Bad request",
                    detail="The Session Template '{}' "
                           "is missing the required \'name\' attribute."
                    .format(sessiontemplate.template_url))
            json_st_str = json.dumps(sanitize_xnames(st_json))
        LOGGER.debug("Removing temporary local file: '%s'", sessionTemplateFile)
        os.remove(sessionTemplateFile)

        # Create a Session Template from the content.
        """Store the Session Template content.
           For now overwrite any existing template by name w/o warning.
           Later this can be changed (detected and blocked) when we
           support patching operations. This could also be changed to
           result in an HTTP 409 Conflict. TBD.
        """
        sessiontemplate_name = st_json['name']
        DB.put(sessiontemplate_name, st_json)
        return sessiontemplate_name, 201

    if sessiontemplate.name:
        """If a template name has been provided in the body, treat this as
           a complete JSON session template record and store it.
           For now overwrite any existing template by name w/o warning.
           Later this can be changed when we support patching operations.
           This could also be changed to result in an HTTP 409 Conflict. TBD.
        """
        LOGGER.debug("create_v1_sessiontemplate name: %s", sessiontemplate.name)
        st_json = connexion.request.get_json()
        DB.put(sessiontemplate.name, st_json)
        return sessiontemplate.name, 201


def get_v1_sessiontemplates():  # noqa: E501
    """
    GET /v1/sessiontemplates

    List all sessiontemplates
    """
    LOGGER.debug("get_v1_sessiontemplates: Fetching sessions.")
    return get_v2_sessiontemplates()


def get_v1_sessiontemplate(session_template_id):
    """
    GET /v1/sessiontemplate

    Get the session template by session template ID
    """
    LOGGER.debug("get_v1_sessiontemplate by ID: %s", session_template_id)  # noqa: E501
    return get_v2_sessiontemplate(session_template_id)


def get_v1_sessiontemplatetemplate():
    """
    GET /v1/sessiontemplatetemplate

    Get the example session template
    """
    return SESSION_TEMPLATE_TEMPLATE, 200


def delete_v1_sessiontemplate(session_template_id):
    """
    DELETE /v1/sessiontemplate

    Delete the session template by session template ID
    """
    LOGGER.debug("delete_v1_sessiontemplate by ID: %s", session_template_id)
    return delete_v2_sessiontemplate(session_template_id)
