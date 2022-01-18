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
from datetime import datetime
import logging

from bos import redis_db_utils as dbutils

LOGGER = logging.getLogger('bos.controllers.v2.components')
DB = dbutils.get_wrapper(db='components')


@dbutils.redis_error_handler
def get_v2_components(ids="", enabled=None, session=None):
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
    response = get_v2_components_data(id_list=id_list, enabled=enabled, session=session)
    return response, 200


def get_v2_components_data(id_list=None, enabled=None, session=None):
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
    if enabled is not None:
        response = [r for r in response if _matches_filter(r, enabled, session)]
    return response


def _matches_filter(data, enabled, session):
    if enabled is not None and data.get('enabled', None) != enabled:
        return False
    if session is not None and data.get('session', None) != session:
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


def _set_auto_fields(data):
    data = _set_last_updated(data)
    return data


def _set_last_updated(data):
    timestamp = datetime.utcnow().isoformat()
    for section in ['actualState', 'desiredState', 'lastAction']:
        if section in data and type(data[section]) == dict:
            data[section]['lastUpdated'] = timestamp
    return data


def _update_handler(data):
    # Allows processing of data during common patch operation
    return data
