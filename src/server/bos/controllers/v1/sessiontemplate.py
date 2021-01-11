# Cray-provided controllers for the Boot Orchestration Service
# Copyright 2019-2020 Cray Inc.

import logging
import connexion
import json
import wget
import os
from connexion.lifecycle import ConnexionResponse

from bos.models.session_template import SessionTemplate  # noqa: E501
from bos.dbclient import BosEtcdClient
from bos.utils import _canonize_xname

LOGGER = logging.getLogger('bos.controllers.sessiontemplate')
BASEKEY = "/sessionTemplate"


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
           (i.e. bos.models.session_template).
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
        with BosEtcdClient() as bec:
            key = "{}/{}".format(BASEKEY, st_json['name'])
            bec.put(key, value=json_st_str)
            return key, 201

    if sessiontemplate.name:
        """If a template name has been provided in the body, treat this as
           a complete JSON session template record and store it.
           For now overwrite any existing template by name w/o warning.
           Later this can be changed when we support patching operations.
           This could also be changed to result in an HTTP 409 Conflict. TBD.
        """
        LOGGER.debug("create_v1_sessiontemplate name: %s", sessiontemplate.name)
        st_json = connexion.request.get_json()
        json_st_str = json.dumps(sanitize_xnames(st_json))
        with BosEtcdClient() as bec:
            key = "/sessionTemplate/{}".format(sessiontemplate.name)
            bec.put(key, value=json_st_str)
        return key, 201


def get_v1_sessiontemplates():  # noqa: E501
    """
    GET /v1/sessiontemplates

    List all sessiontemplates
    """
    LOGGER.debug("get_v1_sessiontemplates: Fetching sessions.")
    with BosEtcdClient() as bec:
        results = []
        for st, _meta in bec.get_prefix('{}/'.format(BASEKEY)):
            json_st = json.loads(st.decode('utf-8'))
            results.append(json_st)
        return results, 200


def get_v1_sessiontemplate(session_template_id):
    """
    GET /v1/sessiontemplate

    Get the session template by session template ID
    """
    LOGGER.debug("get_v1_sessiontemplate by ID: %s", session_template_id)  # noqa: E501
    with BosEtcdClient() as bec:
        key = "{}/{}".format(BASEKEY, session_template_id)
        st, _meta = bec.get(key)
        if st:
            json_st = json.loads(st.decode('utf-8'))
            return json_st, 200
        else:
            return connexion.problem(status=404,
                                     title="The Session Template was not found",
                                     detail="The Session Template '{}' was not found.".format(session_template_id))  # noqa: E501


def delete_v1_sessiontemplate(session_template_id):
    """
    DELETE /v1/sessiontemplate

    Delete the session template by session template ID
    """
    LOGGER.debug("delete_v1_sessiontemplate by ID: %s", session_template_id)
    result = get_v1_sessiontemplate(session_template_id)
    if isinstance(result, ConnexionResponse):
        return result
    with BosEtcdClient() as bec:
        key = "/sessionTemplate/{}".format(session_template_id)
        bec.delete(key)
        return '', 204
