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

import connexion
import logging

from bos.common.utils import get_current_timestamp
from bos.server import redis_db_utils as dbutils
from bos.server.dbs.boot_artifacts import get_boot_artifacts, BssTokenUnknown

LOGGER = logging.getLogger('bos.server.controllers.v2.components')
DB = dbutils.get_wrapper(db='components')
SESSIONS_DB = dbutils.get_wrapper(db='sessions')
EMPTY_BOOT_ARTIFACTS = {
    "kernel": "",
    "kernel_parameters": "",
    "initrd": ""
}


@dbutils.redis_error_handler
def get_v2_components(ids="", enabled=None, session=None, staged_session=None):
    """Used by the GET /components API operation

    Allows filtering using a comma separated list of ids.
    """
    LOGGER.debug("GET /components invoked get_components")
    id_list = []
    if ids:
        try:
            id_list = ids.split(',')
        except Exception as err:
            return connexion.problem(
                status=400, title="Error parsing the ids provided.",
                detail=str(err))
    response = get_v2_components_data(id_list=id_list, enabled=enabled, session=session, staged_session=staged_session)
    return response, 200


def get_v2_components_data(id_list=None, enabled=None, session=None, staged_session=None):
    """Used by the GET /components API operation

    Allows filtering using a comma separated list of ids.
    """
    response = []
    if id_list:
        for component_id in id_list:
            data = DB.get(component_id)
            if data:
                response.append(data)
    else:
        # TODO: On large scale systems, this response may be too large
        # and require paging to be implemented
        response = DB.get_all()
    if enabled is not None or session is not None or staged_session is not None:
        response = [r for r in response if _matches_filter(r, enabled, session, staged_session)]
    return response


def _matches_filter(data, enabled, session, staged_session):
    if enabled is not None and data.get('enabled', None) != enabled:
        return False
    if session is not None and data.get('session', None) != session:
        return False
    if staged_session is not None and data.get('stagedState', {}).get('session', None) != staged_session:
        return False
    return True


@dbutils.redis_error_handler
def put_v2_components():
    """Used by the PUT /components API operation"""
    LOGGER.debug("PUT /components invoked put_components")
    try:
        data = connexion.request.get_json()
        components = []
        for component_data in data:
            component_id = component_data['id']
            components.append((component_id, component_data))
    except Exception as err:
        return connexion.problem(
            status=400, title="Error parsing the data provided.",
            detail=str(err))
    response = []
    for component_id, component_data in components:
        component_data = _set_auto_fields(component_data)
        response.append(DB.put(component_id, component_data))
    return response, 200


@dbutils.redis_error_handler
def patch_v2_components():
    """Used by the PATCH /components API operation"""
    LOGGER.debug("PATCH /components invoked patch_components")
    try:
        data = connexion.request.get_json()
        components = []
        for component_data in data:
            component_id = component_data['id']
            if component_id not in DB:
                return connexion.problem(
                    status=404, title="Component could not found.",
                    detail="Component {} could not be found".format(component_id))
            components.append((component_id, component_data))
    except Exception as err:
        return connexion.problem(
            status=400, title="Error parsing the data provided.",
            detail=str(err))
    response = []
    for component_id, component_data in components:
        component_data = _set_auto_fields(component_data)
        response.append(DB.patch(component_id, component_data, _update_handler))
    return response, 200


@dbutils.redis_error_handler
def get_v2_component(component_id):
    """Used by the GET /components/{component_id} API operation"""
    LOGGER.debug("GET /components/id invoked get_component")
    if component_id not in DB:
        return connexion.problem(
            status=404, title="Component could not found.",
            detail="Component {} could not be found".format(component_id))
    component = DB.get(component_id)
    return component, 200


@dbutils.redis_error_handler
def put_v2_component(component_id):
    """Used by the PUT /components/{component_id} API operation"""
    LOGGER.debug("PUT /components/id invoked put_component")
    try:
        data = connexion.request.get_json()
    except Exception as err:
        return connexion.problem(
            status=400, title="Error parsing the data provided.",
            detail=str(err))
    data['id'] = component_id
    data = _set_auto_fields(data)
    return DB.put(component_id, data), 200


@dbutils.redis_error_handler
def patch_v2_component(component_id):
    """Used by the PATCH /components/{component_id} API operation"""
    LOGGER.debug("PATCH /components/id invoked patch_component")
    if component_id not in DB:
        return connexion.problem(
            status=404, title="Component could not found.",
            detail="Component {} could not be found".format(component_id))
    try:
        data = connexion.request.get_json()
    except Exception as err:
        return connexion.problem(
            status=400, title="Error parsing the data provided.",
            detail=str(err))
    data = _set_auto_fields(data)
    return DB.patch(component_id, data, _update_handler), 200


@dbutils.redis_error_handler
def delete_v2_component(component_id):
    """Used by the DELETE /components/{component_id} API operation"""
    LOGGER.debug("DELETE /components/id invoked delete_component")
    if component_id not in DB:
        return connexion.problem(
            status=404, title="Component could not found.",
            detail="Component {} could not be found".format(component_id))
    return DB.delete(component_id), 204


@dbutils.redis_error_handler
def post_v2_apply_staged():
    """Used by the POST /applystaged API operation"""
    LOGGER.debug("POST /applystaged invoked post_v2_apply_staged")
    response = {"succeeded": [], "failed": [], "ignored": []}
    try:
        data = connexion.request.get_json()
        xnames = data.get("xnames", [])
        for xname in xnames:
            try:
                if _apply_staged(xname):
                    response["succeeded"].append(xname)
                else:
                    response["ignored"].append(xname)
            except Exception:
                response["failed"].append(xname)
    except Exception as err:
        return connexion.problem(
            status=400, title="Error parsing the data provided.",
            detail=str(err))
    return response, 200


def _apply_staged(component_id):
    if component_id not in DB:
        return False
    data = DB.get(component_id)
    staged_state = data.get("stagedState", {})
    staged_session_id = staged_state.get("session", "")
    if not staged_session_id:
        return False
    try:
        response = _set_state_from_staged(data)
    except Exception as e:
        data["error"] = str(e)
        data["enabled"] = False
        raise e
    finally:
        # For both the successful and failed cases, we want the new session to own the node
        data["session"] = staged_session_id
        data["lastAction"]["action"] = "Apply-Staged"
        data["lastAction"]["numAttempts"] = 1
        data["stagedState"] = {
            "bootArtifacts": EMPTY_BOOT_ARTIFACTS,
            "configuration": ""
        }
        _set_auto_fields(data)
        DB.put(component_id, data)
    return response


def _set_state_from_staged(data):
    staged_state = data.get("stagedState", {})
    staged_session_id = staged_state.get("session", "")
    if staged_session_id not in SESSIONS_DB:
        raise Exception("Staged session no longer exists")
    session = SESSIONS_DB.get(staged_session_id)
    operation = session["operation"]
    if operation == "shutdown":
        if any(staged_state.get("bootArtifacts", {}).values()):
            raise Exception("Staged operation is shutdown but boot artifact have been specified")
        _copy_staged_to_desired(data)
    elif operation == "boot":
        if not all(staged_state.get("bootArtifacts", {}).values()):
            raise Exception("Staged operation is boot but some boot artifacts have not been specified")
        _copy_staged_to_desired(data)
    elif operation == "reboot":
        if not all(staged_state.get("bootArtifacts", {}).values()):
            raise Exception("Staged operation is reboot but some boot artifacts have not been specified")
        _copy_staged_to_desired(data)
        data["actualState"] = {
            "bootArtifacts": EMPTY_BOOT_ARTIFACTS,
            "bssToken": ""
        }
    else:
        raise Exception("Invalid operation in staged session")
    data["enabled"] = True
    return True


def _copy_staged_to_desired(data):
    staged_state = data.get("stagedState", {})
    data["desiredState"] = {
        "bootArtifacts": staged_state.get("bootArtifacts", {}),
        "configuration": staged_state.get("configuration", "")
    }


def _set_auto_fields(data):
    data = _populate_boot_artifacts(data)
    data = _set_last_updated(data)
    return data


def _populate_boot_artifacts(data):
    """
    If there is a BSS Token present in the actualState, 
    then look up the boot artifacts and add them to the
    actualState data.
    
    If the data contains any boot artifacts and the BSS
    token, then those boot artifacts will be overwritten.
    If there are boot artifacts and no BSS token, then
    they will not be overwritten. Further, if the boot
    artifacts are provided and the BSS token is unknown, 
    the boot artifacts will not be overwritten.
    """
    try:
        token = data['actualState']['bssToken']
    except KeyError:
        # Either actualState or bssToken was not present.
        pass
    else:
        # Populate the boot artifacts using the bssToken
        try:
            boot_artifacts = get_boot_artifacts(token)
        except BssTokenUnknown:
            LOGGER.error(f"Reported BSS Token: {token} is unknown.")
        else:
            data['actualState']['bootArtifacts'] = boot_artifacts
    return data


def _set_last_updated(data):
    timestamp = get_current_timestamp()
    for section in ['actualState', 'desiredState', 'stagedState', 'lastAction']:
        if section in data and type(data[section]) == dict and data[section].keys() != {"bssToken"}:
            data[section]['lastUpdated'] = timestamp
    return data


def _update_handler(data):
    # Allows processing of data during common patch operation
    return data