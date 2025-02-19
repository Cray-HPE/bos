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
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from functools import partial
import logging
import re
from typing import Literal
import uuid

import connexion
from connexion.lifecycle import ConnexionResponse

from bos.common.tenant_utils import (get_tenant_aware_key,
                                     get_tenant_from_header,
                                     reject_invalid_tenant)
from bos.common.types.general import JsonDict
from bos.common.utils import exc_type_msg, get_current_time, get_current_timestamp, load_timestamp
from bos.common.values import Phase, Status
from bos.server import redis_db_utils as dbutils
from bos.server.controllers.utils import _400_bad_request, _404_resource_not_found
from bos.server.controllers.v2.boot_set import BootSetStatus, validate_boot_sets
from bos.server.controllers.v2.components import get_v2_components_data
from bos.server.controllers.v2.options import OptionsData
from bos.server.controllers.v2.sessiontemplates import get_v2_sessiontemplate
from bos.server.models.v2_session import V2Session as Session  # noqa: E501
from bos.server.models.v2_session_create import V2SessionCreate as SessionCreate  # noqa: E501
from bos.server.utils import get_request_json, ParsingException

LOGGER = logging.getLogger(__name__)
DB = dbutils.get_wrapper(db='sessions')
COMPONENTS_DB = dbutils.get_wrapper(db='components')
STATUS_DB = dbutils.get_wrapper(db='session_status')
MAX_COMPONENTS_IN_ERROR_DETAILS = 10
LIMIT_NID_RE = re.compile(r'^[&!]*nid')


@reject_invalid_tenant
@dbutils.redis_error_handler
def post_v2_session() -> tuple[JsonDict, Literal[201]] | ConnexionResponse:  # noqa: E501
    """POST /v2/session
    Creates a new session. # noqa: E501
    :param session: A JSON object for creating sessions
    :type session: dict | bytes

    :rtype: Session
    """
    LOGGER.debug("POST /v2/sessions invoked post_v2_session")
    # -- Validation --
    try:
        session_create = SessionCreate.from_dict(
            get_request_json())  # noqa: E501
    except Exception as err:
        LOGGER.error("Error parsing POST request data: %s", exc_type_msg(err))
        return _400_bad_request(f"Error parsing the data provided: {err}")

    options_data = OptionsData()

    # If no limit is specified, check to see if we require one
    if not session_create.limit and options_data.session_limit_required:
        msg = "session_limit_required option is set, but this session has no limit specified"
        LOGGER.error(msg)
        return _400_bad_request(msg)

    # If a limit is specified, check it for nids
    if session_create.limit and any(
            LIMIT_NID_RE.match(limit_item)
            for limit_item in session_create.limit.split(',')):
        msg = f"session limit appears to contain NIDs: {session_create.limit}"
        if options_data.reject_nids:
            msg = f"reject_nids: {msg}"
            LOGGER.error(msg)
            return _400_bad_request(msg)
        # Since BOS does not support NIDs, still log this as a warning.
        # There is a chance that a node group has a name with a name resembling
        # a NID
        LOGGER.warning(msg)

    template_name = session_create.template_name
    LOGGER.debug("Template Name: %s operation: %s", template_name,
                 session_create.operation)
    # Check that the template_name exists.
    session_template_response = get_v2_sessiontemplate(template_name)
    if isinstance(session_template_response, ConnexionResponse):
        msg = f"Session Template Name invalid: {template_name}"
        LOGGER.error(msg)
        return _400_bad_request(msg)
    session_template, _ = session_template_response

    # Validate health/validity of the sessiontemplate before creating a session
    error_code, msg = validate_boot_sets(session_template,
                                         session_create.operation,
                                         template_name,
                                         options_data=options_data)
    if error_code >= BootSetStatus.ERROR:
        msg = f"Session template fails check: {msg}"
        LOGGER.error(msg)
        return _400_bad_request(msg)

    # -- Setup Record --
    tenant = get_tenant_from_header()
    session = _create_session(session_create, tenant)
    session_key = get_tenant_aware_key(session.name, tenant)
    if session_key in DB:
        LOGGER.warning("v2 session named %s already exists", session.name)
        return _409_session_already_exists(session.name)
    session_data = session.to_dict()
    response = DB.put(session_key, session_data)
    return response, 201


def _create_session(session_create: SessionCreate, tenant: str | None) -> Session:
    initial_status = {
        'status': 'pending',
        'start_time': get_current_timestamp(),
    }
    body = {
        'name': session_create.name or str(uuid.uuid4()),
        'operation': session_create.operation,
        'template_name': session_create.template_name or '',
        'limit': session_create.limit or '',
        'stage': session_create.stage,
        'components': '',
        'status': initial_status,
        'include_disabled': session_create.include_disabled
    }
    if tenant:
        body["tenant"] = tenant
    return Session.from_dict(body)


@dbutils.redis_error_handler
def patch_v2_session(session_id: str) -> tuple[JsonDict, Literal[200]] | ConnexionResponse:
    """PATCH /v2/session
    Patch the session identified by session_id
    Args:
      session_id (str): Session ID
    Returns:
      Session Dictionary, Status Code
    """
    LOGGER.debug("PATCH /v2/sessions/%s invoked patch_v2_session", session_id)
    try:
        patch_data_json = get_request_json()
    except Exception as err:
        LOGGER.error("Error parsing PATCH '%s' request data: %s", session_id,
                     exc_type_msg(err))
        return _400_bad_request(f"Error parsing the data provided: {err}")

    session_key = get_tenant_aware_key(session_id, get_tenant_from_header())
    if session_key not in DB:
        LOGGER.warning("Could not find v2 session %s", session_id)
        return _404_session_not_found(resource_id=session_id)  # pylint: disable=redundant-keyword-arg

    component = DB.patch(session_key, patch_data_json)
    return component, 200


@dbutils.redis_error_handler
def get_v2_session(
        session_id: str) -> tuple[JsonDict, Literal[200]] | ConnexionResponse:  # noqa: E501
    """GET /v2/session
    Get the session by session ID
    Args:
      session_id (str): Session ID
    Return:
      Session Dictionary, Status Code
    """
    LOGGER.debug("GET /v2/sessions/%s invoked get_v2_session", session_id)
    session_key = get_tenant_aware_key(session_id, get_tenant_from_header())
    if session_key not in DB:
        LOGGER.warning("Could not find v2 session %s", session_id)
        return _404_session_not_found(resource_id=session_id)  # pylint: disable=redundant-keyword-arg
    session = DB.get(session_key)
    return session, 200


@dbutils.redis_error_handler
def get_v2_sessions(min_age: str | None=None, max_age: str | None=None,
                    status: str | None=None) -> tuple[list[JsonDict],
                                                         Literal[200]]:  # noqa: E501
    """GET /v2/session

    List all sessions
    """
    LOGGER.debug(
        "GET /v2/sessions invoked get_v2_sessions with min_age=%s max_age=%s status=%s",
        min_age, max_age, status)
    response = _get_filtered_sessions(tenant=get_tenant_from_header(),
                                      min_age=min_age,
                                      max_age=max_age,
                                      status=status)
    LOGGER.debug("get_v2_sessions returning %d sessions", len(response))
    return response, 200


@dbutils.redis_error_handler
def delete_v2_session(
        session_id: str) -> tuple[None, Literal[204]] | ConnexionResponse:  # noqa: E501
    """DELETE /v2/session

    Delete the session by session id
    """
    LOGGER.debug("DELETE /v2/sessions/%s invoked delete_v2_session",
                 session_id)
    session_key = get_tenant_aware_key(session_id, get_tenant_from_header())
    if session_key not in DB:
        LOGGER.warning("Could not find v2 session %s", session_id)
        return _404_session_not_found(resource_id=session_id)  # pylint: disable=redundant-keyword-arg
    if session_key in STATUS_DB:
        STATUS_DB.delete(session_key)
    return DB.delete(session_key), 204


@dbutils.redis_error_handler
def delete_v2_sessions(
        min_age: str | None=None, max_age: str | None=None,
        status: str | None=None) -> tuple[None, Literal[204]] | ConnexionResponse:  # noqa: E501
    LOGGER.debug(
        "DELETE /v2/sessions invoked delete_v2_sessions with min_age=%s max_age=%s status=%s",
        min_age, max_age, status)
    tenant = get_tenant_from_header()
    try:
        sessions = _get_filtered_sessions(tenant=tenant,
                                          min_age=min_age,
                                          max_age=max_age,
                                          status=status)
    except ParsingException as err:
        LOGGER.error("Error parsing age field: %s", exc_type_msg(err))
        return _400_bad_request(f"Error parsing age field: {err}")

    for session in sessions:
        session_key = get_tenant_aware_key(session['name'], tenant)
        if session_key in STATUS_DB:
            STATUS_DB.delete(session_key)
        DB.delete(session_key)

    return None, 204


@dbutils.redis_error_handler
def get_v2_session_status(
        session_id: str) -> tuple[JsonDict, Literal[200]] | ConnexionResponse:  # noqa: E501
    """GET /v2/session/status
    Get the session status by session ID
    Args:
      session_id (str): Session ID
    Return:
      Session Status Dictionary, Status Code
    """
    LOGGER.debug("GET /v2/sessions/status/%s invoked get_v2_session_status",
                 session_id)
    session_key = get_tenant_aware_key(session_id, get_tenant_from_header())
    if session_key not in DB:
        LOGGER.warning("Could not find v2 session %s", session_id)
        return _404_session_not_found(resource_id=session_id)  # pylint: disable=redundant-keyword-arg
    session = DB.get(session_key)
    if session.get(
            "status",
        {}).get("status") == "complete" and session_key in STATUS_DB:
        # If the session is complete and the status is saved,
        # return the status from completion time
        return STATUS_DB.get(session_key), 200
    return _get_v2_session_status(session_key, session), 200


@dbutils.redis_error_handler
def save_v2_session_status(
        session_id: str) -> tuple[JsonDict, Literal[200]] | ConnexionResponse:  # noqa: E501
    """POST /v2/session/status
    Get the session status by session ID
    Args:
      session_id (str): Session ID
    Return:
      Session Status Dictionary, Status Code
    """
    LOGGER.debug("POST /v2/sessions/status/%s invoked save_v2_session_status",
                 session_id)
    session_key = get_tenant_aware_key(session_id, get_tenant_from_header())
    if session_key not in DB:
        LOGGER.warning("Could not find v2 session %s", session_id)
        return _404_session_not_found(resource_id=session_id)  # pylint: disable=redundant-keyword-arg
    return STATUS_DB.put(session_key, _get_v2_session_status(session_key)), 200


def _get_filtered_sessions(tenant: str | None, min_age: str | None, max_age: str | None,
                           status: str | None) -> list[JsonDict]:
    response = DB.get_all()
    min_start = None
    max_start = None
    if min_age:
        try:
            max_start = _age_to_timestamp(min_age)
        except Exception as e:
            LOGGER.warning('Unable to parse min_age: %s', min_age)
            raise ParsingException(e) from e
    if max_age:
        try:
            min_start = _age_to_timestamp(max_age)
        except Exception as e:
            LOGGER.warning('Unable to parse max_age: %s', max_age)
            raise ParsingException(e) from e
    if any([min_start, max_start, status, tenant]):
        response = [
            r for r in response
            if _matches_filter(r, tenant, min_start, max_start, status)
        ]
    return response


def _matches_filter(data: dict, tenant: str | None, min_start: datetime | None,
                    max_start: datetime | None, status: str | None) -> bool:
    if tenant and tenant != data.get("tenant"):
        return False
    session_status = data.get('status', {})
    if status and status != session_status.get('status'):
        return False
    start_time = session_status['start_time']
    session_start = None
    if start_time:
        session_start = load_timestamp(start_time)
    if min_start and (not session_start or session_start < min_start):
        return False
    if max_start and (not session_start or session_start > max_start):
        return False
    return True


def _get_v2_session_status(session_key: str|bytes, session: JsonDict | None=None) -> JsonDict:
    if not session:
        session = DB.get(session_key)
    session_id = session.get("name", {})
    tenant_id = session.get("tenant")
    components = get_v2_components_data(session=session_id, tenant=tenant_id)
    staged_components = get_v2_components_data(staged_session=session_id,
                                               tenant=tenant_id)
    num_managed_components = len(components) + len(staged_components)
    if num_managed_components:
        component_phase_counts = Counter([
            c.get('status', {}).get('phase') for c in components
            if (c.get('enabled')
                and c.get('status').get('status_override') != Status.on_hold)
        ])
        component_phase_counts['successful'] = len([
            c for c in components
            if c.get('status', {}).get('status') == Status.stable
        ])
        component_phase_counts['failed'] = len([
            c for c in components
            if c.get('status', {}).get('status') == Status.failed
        ])
        component_phase_counts['staged'] = len(staged_components)
        component_phase_percents = {
            phase:
            (component_phase_counts[phase] / num_managed_components) * 100
            for phase in component_phase_counts
        }
    else:
        component_phase_percents = {}
    component_errors_data = defaultdict(set)
    for component in components:
        if component.get('error'):
            component_errors_data[component.get('error')].add(
                component.get('id'))
    component_errors = {}
    for error, components in component_errors_data.items():
        component_list = ','.join(
            list(components)[:MAX_COMPONENTS_IN_ERROR_DETAILS])
        if len(components) > MAX_COMPONENTS_IN_ERROR_DETAILS:
            component_list += '...'
        component_errors[error] = {
            'count': len(components),
            'list': component_list
        }
    session_status = session.get('status', {})
    start_time = session_status.get('start_time')
    end_time = session_status.get('end_time')
    if end_time:
        duration = str(load_timestamp(end_time) - load_timestamp(start_time))
    else:
        duration = str(get_current_time() - load_timestamp(start_time))
    status = {
        'status':
        session_status.get('status', ''),
        'managed_components_count':
        num_managed_components,
        'phases': {
            'percent_complete':
            round(
                component_phase_percents.get('successful', 0) +
                component_phase_percents.get('failed', 0), 2),
            'percent_powering_on':
            round(component_phase_percents.get(Phase.powering_on, 0), 2),
            'percent_powering_off':
            round(component_phase_percents.get(Phase.powering_off, 0), 2),
            'percent_configuring':
            round(component_phase_percents.get(Phase.configuring, 0), 2),
        },
        'percent_staged':
        round(component_phase_percents.get('staged', 0), 2),
        'percent_successful':
        round(component_phase_percents.get('successful', 0), 2),
        'percent_failed':
        round(component_phase_percents.get('failed', 0), 2),
        'error_summary':
        component_errors,
        'timing': {
            'start_time': start_time,
            'end_time': end_time,
            'duration': duration
        }
    }
    return status


def _age_to_timestamp(age: str) -> datetime:
    delta = {}
    for interval in ['weeks', 'days', 'hours', 'minutes']:
        result = re.search(fr'(\d+)\w*{interval[0]}', age, re.IGNORECASE)
        if result:
            delta[interval] = int(result.groups()[0])
    delta = timedelta(**delta)
    return get_current_time() - delta


_404_session_not_found = partial(_404_resource_not_found, resource_type="Session")


def _409_session_already_exists(session_id: str) -> ConnexionResponse:
    """
    ProblemAlreadyExists
    """
    return connexion.problem(
        status=409,
        title="The resource to be created already exists",
        detail=f"Session '{session_id}' already exists")
