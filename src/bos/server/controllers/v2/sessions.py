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
from typing import Literal, cast
import uuid

import connexion
from connexion.lifecycle import ConnexionResponse as CxResponse

from bos.common.tenant_utils import (get_tenant_from_header,
                                     reject_invalid_tenant)
from bos.common.types.session_extended_status import SessionExtendedStatus
from bos.common.types.sessions import Session as SessionRecordT
from bos.common.types.sessions import SessionCreate as SessionCreateT
from bos.common.types.sessions import SessionUpdate as SessionUpdateT
from bos.common.types.sessions import update_session_record
from bos.common.utils import exc_type_msg, get_current_time, get_current_timestamp, load_timestamp
from bos.common.values import Phase, Status
from bos.server import redis_db_utils as dbutils
from bos.server.controllers.utils import _400_bad_request, _404_tenanted_resource_not_found
from bos.server.controllers.v2.boot_set import BootSetStatus, validate_boot_sets
from bos.server.controllers.v2.components import get_v2_components_data
from bos.server.options import OptionsData
from bos.server.controllers.v2.sessiontemplates import get_v2_sessiontemplate
from bos.server.models.v2_session import V2Session as Session  # noqa: E501
from bos.server.models.v2_session_create import V2SessionCreate as SessionCreate  # noqa: E501
from bos.server.options import update_server_log_level
from bos.server.utils import get_request_json, ParsingException

LOGGER = logging.getLogger(__name__)
DB = dbutils.SessionDBWrapper()
COMPONENTS_DB = dbutils.ComponentDBWrapper()
STATUS_DB = dbutils.SessionStatusDBWrapper()
MAX_COMPONENTS_IN_ERROR_DETAILS = 10
LIMIT_NID_RE = re.compile(r'^[&!]*nid')


@reject_invalid_tenant
@dbutils.redis_error_handler
def post_v2_session() -> tuple[SessionRecordT, Literal[201]] | CxResponse:  # noqa: E501
    """POST /v2/session
    Creates a new session. # noqa: E501
    :param session: A JSON object for creating sessions
    :type session: dict | bytes

    :rtype: Session
    """
    # For all entry points into the server, first refresh options and update log level if needed
    update_server_log_level()

    LOGGER.debug("POST /v2/sessions invoked post_v2_session")
    # -- Validation --
    try:
        session_create = SessionCreate.from_dict(
            cast(SessionCreateT, get_request_json()))  # noqa: E501
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
    if isinstance(session_template_response, CxResponse):
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
    if DB.has_tenanted_entry(session.name, tenant):
        LOGGER.warning("v2 session named %s already exists (tenant = '%s')", session.name, tenant)
        return _409_session_already_exists(session.name, tenant)
    session_data: SessionRecordT = session.to_dict()
    DB.tenanted_put(session.name, tenant, session_data)
    return session_data, 201


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
def patch_v2_session(session_id: str) -> tuple[SessionRecordT, Literal[200]] | CxResponse:
    """PATCH /v2/session
    Patch the session identified by session_id
    Args:
      session_id (str): Session ID
    Returns:
      Session Dictionary, Status Code
    """
    # For all entry points into the server, first refresh options and update log level if needed
    update_server_log_level()

    LOGGER.debug("PATCH /v2/sessions/%s invoked patch_v2_session", session_id)
    try:
        patch_data = cast(SessionUpdateT, get_request_json())
    except Exception as err:
        LOGGER.error("Error parsing PATCH '%s' request data: %s", session_id,
                     exc_type_msg(err))
        return _400_bad_request(f"Error parsing the data provided: {err}")

    tenant = get_tenant_from_header()
    try:
        session_data = DB.tenanted_get(session_id, tenant)
    except dbutils.NotFoundInDB:
        LOGGER.warning("Could not find v2 session %s (tenant = '%s')", session_id, tenant)
        return _404_session_not_found(resource_id=session_id, tenant=tenant)  # pylint: disable=redundant-keyword-arg

    try:
        update_session_record(session_data, patch_data)
    except Exception as err:
        LOGGER.error("Error parsing PATCH '%s' request with data: %s", session_id,
                     exc_type_msg(err))
        return _400_bad_request(f"Error patching with the data provided: {err}")

    DB.tenanted_put(session_id, tenant, session_data)
    return session_data, 200


@dbutils.redis_error_handler
def get_v2_session(
        session_id: str) -> tuple[SessionRecordT, Literal[200]] | CxResponse:  # noqa: E501
    """GET /v2/session
    Get the session by session ID
    Args:
      session_id (str): Session ID
    Return:
      Session Dictionary, Status Code
    """
    # For all entry points into the server, first refresh options and update log level if needed
    update_server_log_level()

    LOGGER.debug("GET /v2/sessions/%s invoked get_v2_session", session_id)
    tenant = get_tenant_from_header()
    try:
        session = DB.tenanted_get(session_id, tenant)
    except dbutils.NotFoundInDB:
        LOGGER.warning("Could not find v2 session %s (tenant = '%s')", session_id, tenant)
        return _404_session_not_found(resource_id=session_id, tenant=tenant)  # pylint: disable=redundant-keyword-arg
    return session, 200


@dbutils.redis_error_handler
def get_v2_sessions(min_age: str | None=None, max_age: str | None=None,
                    status: str | None=None) -> tuple[list[SessionRecordT],
                                                         Literal[200]]:  # noqa: E501
    """GET /v2/session

    List all sessions
    """
    # For all entry points into the server, first refresh options and update log level if needed
    update_server_log_level()

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
        session_id: str) -> tuple[None, Literal[204]] | CxResponse:  # noqa: E501
    """DELETE /v2/session

    Delete the session by session id
    """
    # For all entry points into the server, first refresh options and update log level if needed
    update_server_log_level()

    LOGGER.debug("DELETE /v2/sessions/%s invoked delete_v2_session",
                 session_id)
    tenant = get_tenant_from_header()
    try:
        DB.tenanted_delete(session_id, tenant)
    except dbutils.NotFoundInDB:
        LOGGER.warning("Could not find v2 session %s (tenant = '%s')", session_id, tenant)
        return _404_session_not_found(resource_id=session_id, tenant=tenant)  # pylint: disable=redundant-keyword-arg
    # If there isn't an entry in the status DB for this session, that's okay
    _tenanted_delete_if_present(STATUS_DB, session_id, tenant)
    return None, 204


@dbutils.redis_error_handler
def delete_v2_sessions(
        min_age: str | None=None, max_age: str | None=None,
        status: str | None=None) -> tuple[None, Literal[204]] | CxResponse:  # noqa: E501
    # For all entry points into the server, first refresh options and update log level if needed
    update_server_log_level()

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
        _tenanted_delete_if_present(STATUS_DB, session['name'], tenant)
        _tenanted_delete_if_present(DB, session['name'], tenant)

    return None, 204


def _tenanted_delete_if_present(db: dbutils.TenantAwareDBWrapper, session_id: str,
                                tenant: str | None) -> None:
    """
    Attempt to remove the specified session for the specified tenant in the specified DB,
    logging a debug entry if it is not found.
    """
    try:
        db.tenanted_delete(session_id, tenant)
    except dbutils.NotFoundInDB:
        LOGGER.debug("No %s DB entry to delete for session %s (tenant = '%s')", db.db.name,
                     session_id, tenant)


@dbutils.redis_error_handler
def get_v2_session_status(
        session_id: str) -> tuple[SessionExtendedStatus, Literal[200]] | CxResponse:  # noqa: E501
    """GET /v2/session/status
    Get the session status by session ID
    Args:
      session_id (str): Session ID
    Return:
      Session Status Dictionary, Status Code
    """
    # For all entry points into the server, first refresh options and update log level if needed
    update_server_log_level()

    LOGGER.debug("GET /v2/sessions/status/%s invoked get_v2_session_status",
                 session_id)
    tenant = get_tenant_from_header()
    try:
        session = DB.tenanted_get(session_id, tenant)
    except dbutils.NotFoundInDB:
        LOGGER.warning("Could not find v2 session %s (tenant = '%s')", session_id, tenant)
        return _404_session_not_found(resource_id=session_id, tenant=tenant)  # pylint: disable=redundant-keyword-arg
    if session.get("status",{}).get("status") == "complete":
        try:
            session_status = STATUS_DB.tenanted_get(session_id, tenant)
        except dbutils.NotFoundInDB:
            pass
        else: # No exception raised by DB get --> session status exists
            # The session is complete and the status is saved, so
            # return the status from completion time
            return session_status, 200
    return _get_v2_session_status(session_id, tenant, session), 200


@dbutils.redis_error_handler
def save_v2_session_status(
        session_id: str) -> tuple[SessionExtendedStatus, Literal[200]] | CxResponse:  # noqa: E501
    """POST /v2/session/status
    Get the session status by session ID
    Args:
      session_id (str): Session ID
    Return:
      Session Status Dictionary, Status Code
    """
    # For all entry points into the server, first refresh options and update log level if needed
    update_server_log_level()

    LOGGER.debug("POST /v2/sessions/status/%s invoked save_v2_session_status",
                 session_id)
    tenant = get_tenant_from_header()
    try:
        session = DB.tenanted_get(session_id, tenant)
    except dbutils.NotFoundInDB:
        LOGGER.warning("Could not find v2 session %s (tenant = '%s')", session_id, tenant)
        return _404_session_not_found(resource_id=session_id, tenant=tenant)  # pylint: disable=redundant-keyword-arg
    extended_status = _get_v2_session_status(session_id, tenant, session)
    STATUS_DB.tenanted_put(session_id, tenant, extended_status)
    return extended_status, 200


def _get_filtered_sessions(tenant: str | None, min_age: str | None, max_age: str | None,
                           status: str | None) -> list[SessionRecordT]:
    if not any([tenant, min_age, max_age, status]):
        return DB.get_all()
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
    return DB.get_all_filtered(filter_func=partial(_matches_filter, tenant=tenant,
                                                   min_start=min_start, max_start=max_start,
                                                   status=status))


def _matches_filter(data: SessionRecordT, tenant: str | None, min_start: datetime | None,
                    max_start: datetime | None, status: str | None) -> SessionRecordT | None:
    if tenant and tenant != data.get("tenant"):
        return None
    session_status = data.get('status', {})
    if status and status != session_status.get('status'):
        return None
    if min_start or max_start:
        start_time = session_status['start_time']
        session_start = load_timestamp(start_time) if start_time else None
        if min_start and (not session_start or session_start < min_start):
            return None
        if max_start and (not session_start or session_start > max_start):
            return None
    return data


def _get_v2_session_status(session_id: str, tenant_id: str | None,
                           session: SessionRecordT) -> SessionExtendedStatus:
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


_404_session_not_found = partial(_404_tenanted_resource_not_found, resource_type="Session")


def _409_session_already_exists(session_id: str, tenant: str | None) -> CxResponse:
    """
    ProblemAlreadyExists
    """
    if tenant:
        detail=f"Session '{session_id}' already exists for tenant '{tenant}'"
    else:
        detail=f"Session '{session_id}' already exists"
    return connexion.problem(
        status=409,
        title="The resource to be created already exists",
        detail=detail)
