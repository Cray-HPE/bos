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
import connexion
from datetime import timedelta
from collections import defaultdict, Counter
import re
import logging
import uuid
from connexion.lifecycle import ConnexionResponse

from bos.common.tenant_utils import get_tenant_from_header, get_tenant_aware_key, reject_invalid_tenant
from bos.common.utils import get_current_time, get_current_timestamp, load_timestamp
from bos.common.values import Phase, Status
from bos.server import redis_db_utils as dbutils
from bos.server.controllers.v2.components import get_v2_components_data
from bos.server.controllers.v2.sessiontemplates import get_v2_sessiontemplate
from bos.server.models.v2_session import V2Session as Session  # noqa: E501
from bos.server.models.v2_session_create import V2SessionCreate as SessionCreate  # noqa: E501
from .boot_set import validate_boot_sets, BOOT_SET_ERROR

LOGGER = logging.getLogger('bos.server.controllers.v2.session')
DB = dbutils.get_wrapper(db='sessions')
COMPONENTS_DB = dbutils.get_wrapper(db='components')
STATUS_DB = dbutils.get_wrapper(db='session_status')
BASEKEY = "/sessions"
MAX_COMPONENTS_IN_ERROR_DETAILS = 10


@reject_invalid_tenant
@dbutils.redis_error_handler
def post_v2_session():  # noqa: E501
    """POST /v2/session
    Creates a new session. # noqa: E501
    :param session: A JSON object for creating sessions
    :type session: dict | bytes

    :rtype: Session
    """
    # -- Validation --
    if connexion.request.is_json:
        LOGGER.debug("connexion.request.is_json")
        LOGGER.debug("type=%s", type(connexion.request.get_json()))
        LOGGER.debug("Received: %s", connexion.request.get_json())
        session_create = SessionCreate.from_dict(connexion.request.get_json())  # noqa: E501
    else:
        msg = "Post must be in JSON format"
        LOGGER.error(msg)
        return msg, 400
    template_name = session_create.template_name
    LOGGER.debug(f"Template Name: {template_name} operation: {session_create.operation}")
    # Check that the template_name exists.
    session_template_response = get_v2_sessiontemplate(template_name)
    if isinstance(session_template_response, ConnexionResponse):
        msg = "Session Template Name invalid: {}".format(template_name)
        LOGGER.error(msg)
        return msg, 400
    else:
        session_template, _ = session_template_response

    # Validate health/validity of the sessiontemplate before creating a session
    error_code, msg = validate_boot_sets(session_template, session_create.operation, template_name)
    if error_code >= BOOT_SET_ERROR:
        return msg, 400

    # -- Setup Record --
    tenant = get_tenant_from_header()
    session = _create_session(session_create, tenant)
    session_key =  get_tenant_aware_key(session.name, tenant)
    if session_key in DB:
        return connexion.problem(
            detail="A session with the name {} already exists".format(session.name),
            status=409,
            title="Conflicting session name"
        )
    session_data = session.to_dict()
    response = DB.put(session_key, session_data)
    return response, 201


def _create_session(session_create, tenant):
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
    }
    if tenant:
        body["tenant"] = tenant
    return Session.from_dict(body)


@dbutils.redis_error_handler
def patch_v2_session(session_id):
    """PATCH /v2/session
    Patch the session identified by session_id
    Args:
      session_id (str): Session ID
    Returns:
      Session Dictionary, Status Code
    """
    session_key = get_tenant_aware_key(session_id, get_tenant_from_header())
    if session_key not in DB:
        return connexion.problem(
            status=404, title="Session could not found.",
            detail="Session {} could not be found".format(session_id))

    if not connexion.request.is_json:
        return "Post must be in JSON format", 400
    data = connexion.request.get_json()
    component = DB.patch(session_key, data)
    return component, 200


@dbutils.redis_error_handler
def get_v2_session(session_id):  # noqa: E501
    """GET /v2/session
    Get the session by session ID
    Args:
      session_id (str): Session ID
    Return:
      Session Dictionary, Status Code
    """
    session_key = get_tenant_aware_key(session_id, get_tenant_from_header())
    if session_key not in DB:
        return connexion.problem(
            status=404, title="Session could not found.",
            detail="Session {} could not be found".format(session_id))
    session = DB.get(session_key)
    return session, 200


@dbutils.redis_error_handler
def get_v2_sessions(min_age=None, max_age=None, status=None):  # noqa: E501
    """GET /v2/session

    List all sessions
    """
    LOGGER.info("Called get v2 sessions")
    response = _get_filtered_sessions(tenant=get_tenant_from_header(),
                                      min_age=min_age, max_age=max_age,
                                      status=status)
    return response, 200


@dbutils.redis_error_handler
def delete_v2_session(session_id):  # noqa: E501
    """DELETE /v2/session

    Delete the session by session id
    """
    session_key = get_tenant_aware_key(session_id, get_tenant_from_header())
    if session_key not in DB:
        return connexion.problem(
            status=404, title="Session could not found.",
            detail="Session {} could not be found".format(session_id))
    if session_key in STATUS_DB:
        STATUS_DB.delete(session_key)
    return DB.delete(session_key), 204


@dbutils.redis_error_handler
def delete_v2_sessions(min_age=None, max_age=None, status=None):  # noqa: E501
    try:
        tenant = get_tenant_from_header()
        sessions = _get_filtered_sessions(tenant=get_tenant_from_header(),
                                          min_age=min_age, max_age=max_age,
                                          status=status)
        for session in sessions:
            session_name = session['name']
            DB.delete(session_name)
            if session_name in STATUS_DB:
                STATUS_DB.delete(session_name)
    except ParsingException as err:
        return connexion.problem(
            detail=str(err),
            status=400,
            title='Error parsing age field'
        )
    return None, 204


@dbutils.redis_error_handler
def get_v2_session_status(session_id):  # noqa: E501
    """GET /v2/session/status
    Get the session status by session ID
    Args:
      session_id (str): Session ID
    Return:
      Session Status Dictionary, Status Code
    """
    session_key = get_tenant_aware_key(session_id, get_tenant_from_header())
    if session_key not in DB:
        return connexion.problem(
            status=404, title="Session could not found.",
            detail="Session {} could not be found".format(session_id))
    session = DB.get(session_key)
    if session.get("status", {}).get("status") == "complete" and session_key in STATUS_DB:
        # If the session is complete and the status is saved, return the status from completion time
        return STATUS_DB.get(session_key), 200
    return _get_v2_session_status(session_key, session), 200


@dbutils.redis_error_handler
def save_v2_session_status(session_id):  # noqa: E501
    """POST /v2/session/status
    Get the session status by session ID
    Args:
      session_id (str): Session ID
    Return:
      Session Status Dictionary, Status Code
    """
    session_key = get_tenant_aware_key(session_id, get_tenant_from_header())
    if session_key not in DB:
        return connexion.problem(
            status=404, title="Session could not found.",
            detail="Session {} could not be found".format(session_id))
    return STATUS_DB.put(session_key, _get_v2_session_status(session_key)), 200


def _get_filtered_sessions(tenant, min_age, max_age, status):
    response = DB.get_all()
    min_start = None
    max_start = None
    if min_age:
        try:
            max_start = _age_to_timestamp(min_age)
        except Exception as e:
            LOGGER.warning('Unable to parse age: {}'.format(min_age))
            raise ParsingException(e) from e
    if max_age:
        try:
            min_start = _age_to_timestamp(max_age)
        except Exception as e:
            LOGGER.warning('Unable to parse age: {}'.format(max_age))
            raise ParsingException(e) from e
    if any([min_start, max_start, status, tenant]):
        response = [r for r in response if _matches_filter(r, tenant, min_start, max_start, status)]
    return response


def _matches_filter(data, tenant, min_start, max_start, status):
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


def _get_v2_session_status(session_key, session=None):
    if not session:
        session = DB.get(session_key)
    session_id = session.get("name", {})
    tenant_id = session.get("tenant")
    components = get_v2_components_data(session=session_id, tenant=tenant_id)
    staged_components = get_v2_components_data(staged_session=session_id, tenant=tenant_id)
    num_managed_components = len(components) + len(staged_components)
    if num_managed_components:
        component_phase_counts = Counter([c.get('status', {}).get('phase') for c in components])
        component_phase_counts['successful'] = len([c for c in components if c.get('status', {}).get('status') == Status.stable])
        component_phase_counts['failed'] = len([c for c in components if c.get('status', {}).get('status') == Status.failed])
        component_phase_counts['staged'] = len(staged_components)
        component_phase_percents = {phase: (component_phase_counts[phase] / num_managed_components) * 100 for phase in component_phase_counts}
    else:
        component_phase_percents = {}
    component_errors_data = defaultdict(set)
    for component in components:
        if component.get('error'):
            component_errors_data[component.get('error')].add(component.get('id'))
    component_errors = {}
    for error, components in component_errors_data.items():
        component_list = ','.join(list(components)[:MAX_COMPONENTS_IN_ERROR_DETAILS])
        if len(components) > MAX_COMPONENTS_IN_ERROR_DETAILS:
            component_list += '...'
        component_errors[error] = {'count': len(components), 'list': component_list}
    session_status = session.get('status', {})
    start_time = session_status.get('start_time')
    end_time = session_status.get('end_time')
    if end_time:
        duration = str(load_timestamp(end_time) - load_timestamp(start_time))
    else:
        duration = str(get_current_time() - load_timestamp(start_time))
    status = {
        'status': session_status.get('status', ''),
        'managed_components_count': num_managed_components,
        'phases': {
            'percent_complete': component_phase_percents.get('successful', 0) + component_phase_percents.get('failed', 0),
            'percent_powering_on': component_phase_percents.get(Phase.powering_on, 0),
            'percent_powering_off': component_phase_percents.get(Phase.powering_off, 0),
            'percent_configuring': component_phase_percents.get(Phase.configuring, 0),
        },
        'percent_staged': component_phase_percents.get('staged', 0),
        'percent_successful': component_phase_percents.get('successful', 0),
        'percent_failed': component_phase_percents.get('failed', 0),
        'error_summary': component_errors,
        'timing': {
            'start_time': start_time,
            'end_time': end_time,
            'duration': duration
        }
    }
    return status


def _age_to_timestamp(age):
    delta = {}
    for interval in ['weeks', 'days', 'hours', 'minutes']:
        result = re.search('(\d+)\w*{}'.format(interval[0]), age, re.IGNORECASE)
        if result:
            delta[interval] = int(result.groups()[0])
    delta = timedelta(**delta)
    return get_current_time() - delta


class ParsingException(Exception):
    pass
