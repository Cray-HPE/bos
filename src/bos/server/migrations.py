#
# MIT License
#
# (C) Copyright 2023-2024 Hewlett Packard Enterprise Development LP
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
import json
from kubernetes import client, config
import logging
import os

from bos.server.controllers.v1.sessiontemplate import strip_v1_only_fields
from bos.server.dbclient import BosEtcdClient
from bos.common.utils import requests_retry_session
from bos.common.tenant_utils import get_tenant_aware_key
import bos.server.redis_db_utils as dbutils


LOGGER = logging.getLogger('bos.server.migration')
BASEKEY = "/sessionTemplate"

PROTOCOL = 'http'
SERVICE_NAME = 'cray-bos'

def MissingName():
    """
    The session template's name is missing
    """
    pass


def pod_ip():
    """
    Find the IP address for the pod that corresponds to the correct labels;
    specifically 'cray-bos' and the version number of this version of BOS.
    """
    pod_ip = None
    config.load_incluster_config()
    v1 = client.CoreV1Api()
    # Find the correct version of the cray-bos pod
    version = os.getenv('APP_VERSION')
    if not version:
        msg = "Could not determine application's version. Therefore could not contact the correct BOS pod. Aborting."
        LOGGER.error(msg)
        raise ValueError(msg)
    pods = v1.list_namespaced_pod("services",
                                  label_selector=f"app.kubernetes.io/name=cray-bos,app.kubernetes.io/version={version}")
    # Get the pod's IP address
    if pods and pods.items:
        return pods.items[0].status.pod_ip
    msg = "Could not determine BOS pod IP address. Aborting."
    LOGGER.error(msg)
    raise ValueError(msg)


def convert_v1_to_v2(v1_st):
    """
    Convert a v1 session template to a v2 session template.
    Prune extraneous v1 attributes.

    Input:
      v1_st: A v1 session template

    Returns:
      v2_st: A v2 session template
      name: The name of the session template

    Raises:
      MissingName: If the session template's name is missing, then raise this
                   exception.
    """
    session_template_keys = ['name', 'description',
                             'enable_cfs', 'cfs', 'boot_sets', 'links']
    boot_set_keys = ['name', 'path', 'type', 'etag', 'kernel_parameters',
                     'node_list', 'node_roles_groups', 'node_groups',
                     'rootfs_provider', 'rootfs_provider_passthrough']

    v2_st = {'boot_sets': {}}
    try:
        name = v1_st['name']
    except KeyError:
        raise MissingName()
    for k, v in v1_st.items():
        if k in session_template_keys:
            if k != "boot_sets" and k != "name" and k!= "links":
                v2_st[k] = v
        else:
            LOGGER.warning("Discarding attribute: '{}' from session template: '{}'".format(k, v1_st['name']))

    for boot_set, bs_values in v1_st['boot_sets'].items():
        v2_st['boot_sets'][boot_set] = {}
        for k, v in bs_values.items():
            if k in boot_set_keys:
                v2_st['boot_sets'][boot_set][k] = v
            else:
                LOGGER.warning("Discarding attribute: '{}' from boot set: '{}' from session template: '{}'".format(k,
                                                                                                                  boot_set,
                                                                                                                  v1_st['name']))
    return v2_st, name


def migrate_v1_etcd_to_v2_redis_session_templates():
    """
    Read the session templates out of the V1 etcd key/value store and
    write them into the v2 Redis database.
    Do not overwrite existing session templates.
    Sanitize the V1 session templates so they conform to the V2 session
    template standards.
    """
    pod_ip_addr = pod_ip()
    pod_port = os.getenv('BOS_CONTAINER_PORT')
    endpoint = f"{PROTOCOL}://{pod_ip_addr}:{pod_port}"
    st_v2_endpoint = f"{endpoint}/v2/sessiontemplates"
    st_v1_endpoint = f"{endpoint}/v1/sessiontemplate"
    session = requests_retry_session()
    with BosEtcdClient() as bec:
        for session_template_byte_str, _meta in bec.get_prefix('{}/'.format(BASEKEY)):
            v1_st = json.loads(session_template_byte_str.decode("utf-8"))
            response = session.get("{}/{}".format(st_v1_endpoint, v1_st['name']))
            if response.status_code == 200:
                LOGGER.warning("Session template: '{}' already exists. Not "
                               "overwriting.".format(v1_st['name']))
            elif response.status_code == 404:
                LOGGER.info("Migrating v1 session template: '{}' to v2 "
                            "database".format(v1_st['name']))
                try:
                    v2_st, name = convert_v1_to_v2(v1_st)
                except MissingName as err:
                    if 'name' in v1_st:
                        # We should probably never get here.
                        LOGGER.error("Session template: '{}' was not migrated because it was missing its name.".format(v1_st['name']))
                    else:
                        LOGGER.error("A session template: '{}' was not migrated because it was missing its name.".format(name))
                response = session.put("{}/{}".format(st_v2_endpoint, name),
                                                      json=v2_st)
                if not response.ok:
                    LOGGER.error("Session template: '{}' was not migrated for v2 due "
                                 "to error: {}".format(v1_st['name'],
                                                       response.reason))
                    LOGGER.error("Error specifics: {}".format(response.text))
            else:
                LOGGER.error("Session template: '{}' was not migrated due "
                                 "to error: {}".format(v1_st['name'],
                                                       response.reason))
                LOGGER.error("Error specifics: {}".format(response.text))

# Convert existing v1 session templates to v2 format
def convert_v1_to_v2_session_templates():
    db=dbutils.get_wrapper(db='session_templates')
    response = db.get_keys()
    for st_key in response:
        data = db.get(st_key)
        if strip_v1_only_fields(data):
            name = data.get("name")
            LOGGER.info(f"Converting {name} to BOS v2")
            db.put(st_key, data)

# Multi-tenancy key migrations

def migrate_database(db):
    response = db.get_keys()
    for old_key in response:
        data = db.get(old_key)
        name = data.get("name")
        tenant = data.get("tenant")
        new_key = get_tenant_aware_key(name, tenant).encode()
        if new_key != old_key:
            LOGGER.info(f"Migrating {name} to new database key structure")
            db.put(new_key, data)
            db.delete(old_key)


def migrate_to_tenant_aware_keys():
    migrate_database(dbutils.get_wrapper(db='session_templates'))
    migrate_database(dbutils.get_wrapper(db='sessions'))


def perform_migrations():
    migrate_v1_etcd_to_v2_redis_session_templates()
    migrate_to_tenant_aware_keys()
    convert_v1_to_v2_session_templates()


if __name__ == "__main__":
    perform_migrations()
