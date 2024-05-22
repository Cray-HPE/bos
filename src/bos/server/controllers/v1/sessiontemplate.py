#
# MIT License
#
# (C) Copyright 2019-2024 Hewlett Packard Enterprise Development LP
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
import os

from bos.common.tenant_utils import no_v1_multi_tenancy_support
from bos.server import redis_db_utils as dbutils
from bos.server.models.v1_session_template import V1SessionTemplate  # noqa: E501
from bos.server.models.v2_session_template import V2SessionTemplate  # noqa: E501
from bos.server.utils import _canonize_xname
from bos.common.tenant_utils import get_tenant_aware_key
from ..v2.sessiontemplates import get_v2_sessiontemplate, get_v2_sessiontemplates, delete_v2_sessiontemplate

LOGGER = logging.getLogger('bos.server.controllers.v1.sessiontemplate')
DB = dbutils.get_wrapper(db='session_templates')

EXAMPLE_BOOT_SET = {
    "type": "s3",
    "etag": "boot-image-s3-etag",
    "kernel_parameters": "your-kernel-parameters",
    "node_list": [
        "xname1", "xname2", "xname3"],
    "path": "s3://boot-images/boot-image-ims-id/manifest.json",
    "rootfs_provider": "cpss3",
    "rootfs_provider_passthrough": "dvs:api-gw-service-nmn.local:300:hsn0,nmn0:0"}

EXAMPLE_SESSION_TEMPLATE = {
    "boot_sets": {
        "name_your_boot_set": EXAMPLE_BOOT_SET},
    "cfs": {
        "configuration": "desired-cfs-config"},
    "enable_cfs": True}

V1_SPECIFIC_ST_FIELDS = [ "cfs_branch", "cfs_url", "partition" ]
V1_SPECIFIC_CFS_FIELDS = [ "branch", "clone_url", "commit", "playbook" ]
V1_SPECIFIC_BOOTSET_FIELDS = [ "boot_ordinal", "network", "shutdown_ordinal" ]

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

def strip_v1_only_fields(template_data):
    """
    Edits in-place the template data, removing any fields which are specific to BOS v1.
    Returns True if any changes were made.
    Returns False if nothing was removed.
    """
    changes_made=False

    # Strip out the v1-specific fields from the dictionary
    for v1_field_name in V1_SPECIFIC_ST_FIELDS:
        try:
            del template_data[v1_field_name]
            LOGGER.info("Stripped %s field from session template %s", v1_field_name,
                        template_data.get("name", ""))
            changes_made=True
        except KeyError:
            pass

    # Do the same for each boot set
    # Oddly, boot_sets is not a required field, so only do this if it is present
    if "boot_sets" in template_data:
        for bs in template_data["boot_sets"].values():
            for v1_bs_field_name in V1_SPECIFIC_BOOTSET_FIELDS:
                try:
                    del bs[v1_bs_field_name]
                    LOGGER.info("Stripped %s field from a boot set in session template %s",
                                v1_bs_field_name, template_data.get("name", ""))
                    changes_made=True
                except KeyError:
                    pass

    # Do the same for the cfs field, if present
    if "cfs" in template_data:
        cfs_data = template_data["cfs"]
        for v1_cfs_field_name in V1_SPECIFIC_CFS_FIELDS:
            try:
                del cfs_data[v1_cfs_field_name]
                LOGGER.info("Stripped cfs.%s field from session template %s", v1_cfs_field_name,
                            template_data.get("name", ""))
                changes_made=True
            except KeyError:
                pass

    return changes_made

@no_v1_multi_tenancy_support
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
        """Verify that we can convert the JSON request data into a
           V1SessionTemplate object.
           Any exceptions caught here would be generated from the model
           (i.e. bos.server.models.session_template). Examples are
           an exception for a session template missing the required name
           field, or an exception for a session template name that does not
           confirm to Kubernetes naming convention.
           In this case return 400 with a description of the specific error.
        """
        template_data = connexion.request.get_json()
        V1SessionTemplate.from_dict(template_data)
    except Exception as err:
        return connexion.problem(
            status=400, title="The session template could not be created.",
            detail=str(err))

    strip_v1_only_fields(template_data)

    # BOS v2 doesn't want the session template name inside the dictionary itself
    # name is a required v1 field, though, so we can safely pop it here
    session_template_id = template_data.pop("name")

    # Now basically follow the same process as when creating a V2 session template (except in the end,
    # if successful, we will return 201 status and the name of the template, to match the v1 API spec)
    try:
        """Verify that we can convert the JSON request data into a
           V2SessionTemplate object.
           Any exceptions caught here would be generated from the model
           (i.e. bos.server.models.session_template).
           An example is an exception for a session template name that
           does not conform to Kubernetes naming convention.
           In this case return 400 with a description of the specific error.
        """
        V2SessionTemplate.from_dict(template_data)
    except Exception as err:
        return connexion.problem(
            status=400, title="The session template could not be created as a v2 template.",
            detail=str(err))

    template_data = sanitize_xnames(template_data)
    template_data['name'] = session_template_id
    # Tenants are not used in v1, but v1 and v2 share template storage
    template_data['tenant'] = ""
    template_key = get_tenant_aware_key(session_template_id, "")
    DB.put(template_key, template_data)
    return session_template_id, 201


@no_v1_multi_tenancy_support
def get_v1_sessiontemplates():  # noqa: E501
    """
    GET /v1/sessiontemplates

    List all sessiontemplates
    """
    LOGGER.debug("get_v1_sessiontemplates: Fetching sessions.")
    return get_v2_sessiontemplates()


@no_v1_multi_tenancy_support
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
    return EXAMPLE_SESSION_TEMPLATE, 200


@no_v1_multi_tenancy_support
def delete_v1_sessiontemplate(session_template_id):
    """
    DELETE /v1/sessiontemplate

    Delete the session template by session template ID
    """
    LOGGER.debug("delete_v1_sessiontemplate by ID: %s", session_template_id)
    return delete_v2_sessiontemplate(session_template_id)
