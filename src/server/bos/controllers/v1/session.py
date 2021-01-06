# Cray-provided controllers for the Boot Orchestration Service
# Copyright 2019-2021 Hewlett Packard Enterprise Development LP

import connexion
import pickle
import json
import logging
import tempfile
import os
import uuid
from connexion.lifecycle import ConnexionResponse

from jinja2 import Environment, FileSystemLoader
from kubernetes import client, config, utils
from kubernetes.config.config_exception import ConfigException
from kubernetes.client.rest import ApiException

from bos.controllers.v1.sessiontemplate import get_v1_sessiontemplate
from bos.controllers.v1.status import BootSetDoesNotExist, create_v1_session_status
from bos.dbclient import BosEtcdClient, DB_HOST, DB_PORT
from bos.models.session import Session  # noqa: E501

LOGGER = logging.getLogger('bos.controllers.session')
BASEKEY = "/session"


def create_v1_session():  # noqa: E501
    """POST /v1/session
    Creates a new boot session. # noqa: E501
    :param session: A JSON object for creating sessions
    :type session: dict | bytes

    :rtype: Session
    """
    if connexion.request.is_json:
        LOGGER.debug("connexion.request.is_json")
        LOGGER.debug("type=%s", type(connexion.request.get_json()))
        LOGGER.debug("Received: %s", connexion.request.get_json())
        session = Session.from_dict(connexion.request.get_json())  # noqa: E501
    else:
        return "Post must be in JSON format", 400
    LOGGER.debug("Template UUID: %s operation: %s", session.template_uuid,
                 session.operation)
    # Check that the sessionTemplate ID exists.
    session_template_response = get_v1_sessiontemplate(session.template_uuid)
    if isinstance(session_template_response, ConnexionResponse):
        msg = "Session Template ID invalid: {}".format(session.template_uuid)
        LOGGER.error(msg)
        return msg, 404
    else:
        session_template, _ = session_template_response
    # Validate health/validity of the sessiontemplate before creating a session
    boot_sets = session_template['boot_sets']
    if not boot_sets:
        msg = "Session template '%s' must have one or more defined boot sets for " \
            "creation of a session." % (session.template_uuid)
        return msg, 400
    hardware_specifier_fields = ('node_roles_groups', 'node_list', 'node_groups')
    for bs_name, bs in session_template['boot_sets'].items():
        specified = [bs.get(field, None)
                     for field in hardware_specifier_fields]
        if not any(specified):
            msg = "Session template '%s' boot set '%s' must have at least one " \
                "hardware specifier field provided (%s); None defined." \
                % (session.template_uuid, bs_name,
                   ', '.join(sorted(hardware_specifier_fields)))
            return msg, 400
    # Handle empty limit so that the environment var is not set to "None"
    if not session.limit:
        session.limit = ''
    # Kubernetes set-up
    # Get the Kubernetes configuration
    try:
        config.load_incluster_config()
    except ConfigException:  # pragma: no cover
        config.load_kube_config()  # Development
    # Create API endpoint instance and API resource instances
    k8s_client = client.ApiClient()
    try:
        api_instance = client.CoreV1Api(k8s_client)
    except ApiException as err:
        LOGGER.error("Exception when calling CoreV1API to create an API instance: %s\n", err)
        raise
    # Create the configMap for the BOA
    json_data = {'data.json': json.dumps(session_template)}
    namespace = os.getenv("NAMESPACE", 'services')
    # Determine the session ID and BOA K8s job name
    session_id, boa_job_name = _get_boa_naming_for_session()
    LOGGER.debug("session_id: %s", session_id)
    LOGGER.debug("boa_job_name: %s", boa_job_name)
    body = client.V1ConfigMap(data=json_data)
    body.metadata = client.V1ObjectMeta(namespace=namespace, name=session_id)
    try:
        api_response = api_instance.create_namespaced_config_map(namespace, body)
    except ApiException as err:
        LOGGER.error("Exception when calling CoreV1API to create a configMap: %s\n", err)
        raise
    LOGGER.debug("ConfigMap: %s", api_response)
    # Create the BOA master job
    # Fill out the template first with the input parameters
    env = Environment(loader=FileSystemLoader('/mnt/bos/job_templates/'))
    template = env.get_template('boa_job_create.yaml.j2')
    try:
        log_level = os.getenv("LOG_LEVEL", "DEBUG")
        bos_boa_image = os.getenv("BOS_BOA_IMAGE")
        s3_credentials = os.getenv("S3_CREDENTIALS")
        s3_protocol = os.getenv("S3_PROTOCOL")
        s3_gateway = os.getenv("S3_GATEWAY")
        nbr_retries = os.getenv("NODE_STATE_CHECK_NUMBER_OF_RETRIES")
        graceful_shutdown_timeout = os.getenv("GRACEFUL_SHUTDOWN_TIMEOUT")
        forceful_shutdown_timeout = os.getenv("FORCEFUL_SHUTDOWN_TIMEOUT")
        graceful_shutdown_prewait = os.getenv("GRACEFUL_SHUTDOWN_PREWAIT")
        power_status_frequency = os.getenv("POWER_STATUS_FREQUENCY")
    except KeyError as error:
        LOGGER.error("Missing information necessary to create session %s", error)
        raise
    # Render the job submission template
    rendered_template = template.render(boa_job_name=boa_job_name,
                                        boa_image=bos_boa_image,
                                        session_id=session_id,
                                        session_template_id=str(session.template_uuid),
                                        session_limit=session.limit,
                                        operation=session.operation,
                                        DATABASE_NAME=str(DB_HOST),
                                        DATABASE_PORT=str(DB_PORT),
                                        log_level=log_level,
                                        s3_credentials=s3_credentials,
                                        S3_PROTOCOL=s3_protocol,
                                        S3_GATEWAY=s3_gateway,
                                        NODE_STATE_CHECK_NUMBER_OF_RETRIES=nbr_retries,
                                        graceful_shutdown_timeout=graceful_shutdown_timeout,
                                        forceful_shutdown_timeout=forceful_shutdown_timeout,
                                        graceful_shutdown_prewait=graceful_shutdown_prewait,
                                        power_status_frequency=power_status_frequency)
    LOGGER.debug(rendered_template)
    # Write the rendered job template
    ntf = tempfile.NamedTemporaryFile(delete=False).name
    with open(ntf, 'w') as outf:
        outf.write(rendered_template)
    try:
        utils.create_from_yaml(k8s_client, ntf)
    except utils.FailToCreateError as err:
        LOGGER.error("Failed to create BOA Job: %s", err)
        raise
    with BosEtcdClient() as bec:
        key = "{}/{}/templateUuid".format(BASEKEY, session_id)
        bec.put(key=key, value=session.template_uuid)
        key = "{}/{}/operation".format(BASEKEY, session_id)
        bec.put(key=key, value=session.operation)
        key = "{}/{}/boa_job_name".format(BASEKEY, session_id)
        bec.put(key=key, value=boa_job_name)
        key = "{}/{}/status_link".format(BASEKEY, session_id)
        bec.put(key=key, value="/v1/session/{}/status".format(session_id))
    return_json_data = {
        "operation": session.operation,
        "templateUuid": session.template_uuid,
        "links":
        [
            {
                "rel": "session",
                "href": "/v1/session/{}".format(session_id),
                "jobId": boa_job_name,
                "type": "GET"
            },
            {
                "rel": "status",
                "href": "/v1/session/{}/status".format(session_id),
                "type": "GET"
            }
        ]
    }
    if session.limit:
        return_json_data['limit'] = session.limit
    # Create a Session Status Record whenever we create a session
    create_v1_session_status(session_id)
    return return_json_data, 201


def get_v1_sessions():  # noqa: E501
    """GET /v1/session

    List all sessions
    """
    LOGGER.info("Called get v1 sessions")
    with BosEtcdClient() as bec:
        key = "{}/".format(BASEKEY)
        sessions = set()
        for _, metadata in bec.get_prefix(key):
            sessions.add(metadata.key.decode('utf-8').split('/')[2])
        if not sessions:
            LOGGER.debug("No Sessions were found.")
        return list(sessions), 200


def get_v1_session(session_id):  # noqa: E501
    """GET /v1/session
    Get the session by session ID
    Args:
      session_id (str): Session ID
    Return:
      Session Dictionary, Status Code
      The session dictionary contains keys which are attributes about the Session
      and the values for those attributes. Additional values from session status
      are appended regarding start/stop/completion time.
      Example:
      Key       | Value
      operation | boot, shutdown, reboot, configure
    """
    with BosEtcdClient() as bec:
        key = "{}/{}/".format(BASEKEY, session_id)
        session = {}
        for value, metadata in bec.get_prefix(key):
            # The metadata split looks like this:
            # ['', 'session', '<session-id>', '<session-id attribute>']
            attribute = metadata.key.decode('utf-8').split('/')[3]
            if attribute == 'status':
                # Subset of status metadata information is handled separately below
                continue
            session[attribute] = value.decode('utf-8')
    if not session:
        return session, 404
    # CASMCMS-5128: cherry-pick forward metadata keys if they're set
    metadata_defaults = {'start_time': '',
                         'stop_time': '',
                         'complete': '',
                         'in_progress': '',
                         "error_count": ''}
    session.update(metadata_defaults)
    with BosEtcdClient() as bec:
        status_key = "%sstatus" % (key)
        try:
            value, _ = bec.get(status_key)
        except (ValueError, AttributeError):
            # No status available
            return session, 200
        if not value:
            return session, 200
        status = pickle.loads(value)

        for key in metadata_defaults.keys():
            try:
                session[key] = getattr(status.metadata, key)
            except (AttributeError, BootSetDoesNotExist):
                # The key doesn't exist (yet?) Use the default.
                pass
    return session, 200


def delete_v1_session(session_id):  # noqa: E501
    """DELETE /v1/session

    Delete the session by session id
    """
    with BosEtcdClient() as bec:
        key = "{}/{}/".format(BASEKEY, session_id)
        resp = bec.delete_prefix(key)
        if resp.deleted >= 1:
            return '', 204
        else:
            return 'Sesssion: {} not found'.format(session_id), 404


def _get_boa_naming_for_session():
    """ Return the BOA session ID and Kubernetes
        BOA job name for this session.

        This method consolidates the logic of session ID and
        K8s job name creation into a single place.  The BOA
        job template will use the boa_k8s_job_name returned here
        and will not prepend or make further changes.  This job
        name is also returned as part of the session creation
        result for use in monitoring BOA job completion.
    """
    # Generate the session name.
    session_id = str(uuid.uuid4())

    # Construct the K8s BOA job name.
    # Any future changes here should ensure that the name does not exceed 63
    # characters (k8s job name max). It must also conform to Kubernetes
    # naming standards. See CASMCMS-3638.
    # For now this is fine as len('boa-'+str(uuid.uuid4())) = 40
    # and uuid4 is valid for use in the Kubernetes job name.
    boa_k8s_job_name = 'boa-' + session_id

    return session_id, boa_k8s_job_name
