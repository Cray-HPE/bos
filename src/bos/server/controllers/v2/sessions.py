#
# MIT License
#
# (C) Copyright 2021-2022 Hewlett Packard Enterprise Development LP
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

from bos.common.utils import get_current_time, get_current_timestamp, load_timestamp
from bos.common.values import Phase, Status
from bos.server import redis_db_utils as dbutils
from bos.server.controllers.v2.components import get_v2_components_data
from bos.server.controllers.v2.sessiontemplates import get_v2_sessiontemplate
from bos.server.models.v2_session import V2Session as Session  # noqa: E501
from bos.server.models.v2_session_create import V2SessionCreate as SessionCreate  # noqa: E501

from bos.operators.utils.boot_image_metadata.factory import BootImageMetaDataFactory
from bos.operators.utils.clients.s3 import S3Object

LOGGER = logging.getLogger('bos.server.controllers.v2.session')
DB = dbutils.get_wrapper(db='sessions')
COMPONENTS_DB = dbutils.get_wrapper(db='components')
STATUS_DB = dbutils.get_wrapper(db='session_status')
BASEKEY = "/sessions"
MAX_COMPONENTS_IN_ERROR_DETAILS = 10


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
    # Check that the templateName exists.
    session_template_response = get_v2_sessiontemplate(template_name)
    if isinstance(session_template_response, ConnexionResponse):
        msg = "Session Template Name invalid: {}".format(template_name)
        LOGGER.error(msg)
        return msg, 400
    else:
        session_template, _ = session_template_response

    # Validate health/validity of the sessiontemplate before creating a session
    msg, err = _validate_boot_sets(session_template, session_create.operation)
    if msg:
        return msg, err

    # -- Setup Record --
    session = _create_session(session_create)
    session = session.to_dict()
    data = dbutils.snake_to_camel_json(session)
    response = DB.put(session['name'], data)
    return response, 201


def _validate_boot_sets(session_template: dict, operation: str) -> tuple[str, int]:
    """
    Validates the boot sets listed in a session template.
    It ensures that there are boot sets.
    It checks that each boot set specifies nodes via one of the specifier fields.
    Ensures that the boot artifacts exist.  
    
    Inputs:
      session_template (dict): Session template
      operation (str): Requested operation  
    Returns:
        On success, returns (None, 200)
        On failure, returns a tuple containing an error string and an HTTP error code
      
    """
    template_name = session_template['name']

    # Verify boot sets exist.
    if 'boot_sets' not in session_template or not session_template['boot_sets']:
        msg = f"Session template '{template_name}' must have one or more defined boot sets for " \
        "the creation of a session. It has none."
        return msg, 400

    hardware_specifier_fields = ('node_roles_groups', 'node_list', 'node_groups')
    for bs_name, bs in session_template['boot_sets'].items():
        # Verify that the hardware is specified
        specified = [bs.get(field, None)
                     for field in hardware_specifier_fields]
        if not any(specified):
            msg = "Session template '%s' boot set '%s' must have at least one " \
                "hardware specifier field provided (%s); None were provided." \
                % (template_name, bs_name,
                   ', '.join(sorted(hardware_specifier_fields)))
            LOGGER.error(msg)
            return msg, 400

        if operation in ['boot', 'reboot']:
            # Verify that the boot artifacts exist
            try:
                image_metadata = BootImageMetaDataFactory(bs)()
            except Exception as err:
                msg = f"Session template: {template_name} boot set: {bs_name} " \
                    f"could not locate its boot artifacts. Error: {err}"
                LOGGER.error(msg)
                return msg, 400

            # Check boot artifacts' S3 headers
            for boot_artifact in ["kernel", "initrd", "boot_parameters"]:
                try:
                    artifact = getattr(image_metadata.boot_artifacts, boot_artifact)
                    path = artifact ['link']['path']
                    etag = artifact['link']['etag']
                    obj = S3Object(path, etag)
                    _ = obj.object_header
                except Exception as err:
                    msg = f"Session template: {template_name} boot set: {bs_name} " \
                    f"could not locate its {boot_artifact}. Error: {err}"
                    LOGGER.error(msg)
                    return msg, 400
    return None, 200


def _create_session(session_create):
    initial_status = {
        'status': 'pending',
        'startTime': get_current_timestamp(),
    }
    body = {
        'name': str(uuid.uuid4()),
        'operation': session_create.operation,
        'templateName': session_create.template_name or '',
        'limit': session_create.limit or '',
        'stage': session_create.stage,
        'components': '',
        'status': initial_status,
    }
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
    if session_id not in DB:
        return connexion.problem(
            status=404, title="Session could not found.",
            detail="Session {} could not be found".format(session_id))

    if not connexion.request.is_json:
        return "Post must be in JSON format", 400
    data = dbutils.snake_to_camel_json(connexion.request.get_json())
    component = DB.patch(session_id, data)
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
    if session_id not in DB:
        return connexion.problem(
            status=404, title="Session could not found.",
            detail="Session {} could not be found".format(session_id))
    session = DB.get(session_id)
    return session, 200


@dbutils.redis_error_handler
def get_v2_sessions(min_age=None, max_age=None, status=None):  # noqa: E501
    """GET /v2/session

    List all sessions
    """
    LOGGER.info("Called get v2 sessions")
    response = _get_filtered_sessions(min_age=min_age, max_age=max_age, status=status)
    return response, 200


@dbutils.redis_error_handler
def delete_v2_session(session_id):  # noqa: E501
    """DELETE /v2/session

    Delete the session by session id
    """
    if session_id not in DB:
        return connexion.problem(
            status=404, title="Session could not found.",
            detail="Session {} could not be found".format(session_id))
    if session_id in STATUS_DB:
        STATUS_DB.delete(session_id)
    return DB.delete(session_id), 204


@dbutils.redis_error_handler
def delete_v2_sessions(min_age=None, max_age=None, status=None):  # noqa: E501
    try:
        sessions = _get_filtered_sessions(min_age=min_age, max_age=max_age,
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
    if session_id not in DB:
        return connexion.problem(
            status=404, title="Session could not found.",
            detail="Session {} could not be found".format(session_id))
    session = DB.get(session_id)
    if session.get("status", {}).get("status") == "complete" and session_id in STATUS_DB:
        # If the session is complete and the status is saved, return the status from completion time
        return STATUS_DB.get(session_id), 200
    return _get_v2_session_status(session_id, session), 200


@dbutils.redis_error_handler
def save_v2_session_status(session_id):  # noqa: E501
    """POST /v2/session/status
    Get the session status by session ID
    Args:
      session_id (str): Session ID
    Return:
      Session Status Dictionary, Status Code
    """
    if session_id not in DB:
        return connexion.problem(
            status=404, title="Session could not found.",
            detail="Session {} could not be found".format(session_id))
    return STATUS_DB.put(session_id, _get_v2_session_status(session_id)), 200


def _get_filtered_sessions(min_age, max_age, status):
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
    if any([min_start, max_start, status]):
        response = [r for r in response if _matches_filter(r, min_start, max_start, status)]
    return response


def _matches_filter(data, min_start, max_start, status):
    session_status = data.get('status', {})
    if status and status != session_status.get('status'):
        return False
    start_time = session_status['startTime']
    session_start = None
    if start_time:
        session_start = load_timestamp(start_time)
    if min_start and (not session_start or session_start < min_start):
        return False
    if max_start and (not session_start or session_start > max_start):
        return False
    return True


def _get_v2_session_status(session_id, session=None):
    if not session:
        session = DB.get(session_id)
    components = get_v2_components_data(session=session_id)
    staged_components = get_v2_components_data(staged_session=session_id)
    num_managed_components = len(components) + len(staged_components)
    if num_managed_components:
        component_phase_counts = Counter([c.get('status', {}).get('phase') for c in components])
        component_phase_counts['successful'] = len([c for c in components if c.get('status', {}).get('status') == Status.stable])
        component_phase_counts['failed'] = len([c for c in components if c.get('status', {}).get('status') == Status.failed])
        component_phase_counts['staged'] = len(staged_components)
        component_phase_percents = {phase: (component_phase_counts[phase]/num_managed_components)*100 for phase in component_phase_counts}
    else:
        component_phase_percents = {}
    component_errors_data = defaultdict(set)
    for component in components:
        if component.get('error'):
            component_errors_data[component.get('error')].add(component.get('id'))
    component_errors = {}
    for error, components in component_errors_data.items():
        component_list = ','.join(components[:MAX_COMPONENTS_IN_ERROR_DETAILS])
        if len(components) > MAX_COMPONENTS_IN_ERROR_DETAILS:
            component_list += '...'
        component_errors[error] = {'count': len(components), 'list': component_list}
    session_status = session.get('status', {})
    start_time = session_status.get('startTime')
    end_time = session_status.get('endTime')
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
