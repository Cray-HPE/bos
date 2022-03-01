# Copyright 2022 Hewlett Packard Enterprise Development LP
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

import json
import logging
import requests

from bos.server.dbclient import BosEtcdClient
from bos.operators.utils import requests_retry_session
import bos.server.redis_db_utils as dbutils

LOGGER = logging.getLogger('bos.server.v1_v2_migration')
DB = dbutils.get_wrapper(db='session_templates')
BASEKEY = "/sessionTemplate"

PROTOCOL = 'http'
SERVICE_NAME = 'cray-bos'
ENDPOINT = "%s://%s/v2" % (PROTOCOL, SERVICE_NAME)


def convert_v1_to_v2(v1_st):
    """
    Convert a v1 session template to a v2 session template.
    Prune extraneous v1 attributes. 
    
    Input:
      v1_st: A v1 session template
    
    Returns:
      v2_st: A v2 session template
    """
    session_template_keys = ['templateUrl', 'name', 'description',
                             'enable_cfs', 'cfs', 'partition',
                             'boot_sets', 'links']
    boot_set_keys = ['name', 'path', 'type', 'etag', 'kernel_parameters',
                     'node_list', 'node_roles_groups', 'node_groups',
                     'rootfs_provider', 'rootfs_provider_passthrough']

    v2_st = {'boot_sets': {}}
    for k, v in v1_st.items():
        if k in session_template_keys:
            if k != "boot_sets":
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
    return v2_st


def migrate_v1_to_v2_session_templates():
    """
    Read the session templates out of the V1 etcd key/value store and
    write them into the v2 Redis database.
    Do not overwrite existing session templates.
    Sanitize the V1 session templates so they conform to the V2 session
    template standards.
    """
    session = requests_retry_session()
    with BosEtcdClient() as bec:
        st_endpoint = "{}/sessiontemplates".format(ENDPOINT)
        for session_template_byte_str, _meta in bec.get_prefix('{}/'.format(BASEKEY)):
            v1_st = json.loads(session_template_byte_str.decode("utf-8"))
            response = session.get("{}/{}".format(st_endpoint, v1_st['name']))
            if response.status_code == 200:
                LOGGER.warning("Session template: '{}' already exists. Not "
                               "overwriting.".format(v1_st['name']))
            elif response.status_code == 404:
                LOGGER.info("Migrating v1 session template: '{}' to v2 "
                            "database".format(v1_st['name']))
                v2_st = convert_v1_to_v2(v1_st)
                response = session.put("{}/{}".format(st_endpoint,
                                                       v2_st['name']),
                                                       json=v2_st)
                if not response.ok:
                    LOGGER.error("Session template: '{}' was not migrated due "
                                 "to error: {}".format(v1_st['name'],
                                                       response.reason))
                    LOGGER.error("Error specifics: {}".format(response.text))
            else:
                LOGGER.error("Session template: '{}' was not migrated due "
                                 "to error: {}".format(v1_st['name'],
                                                       response.reason))
                LOGGER.error("Error specifics: {}".format(response.text))


if __name__ == "__main__":
  migrate_v1_to_v2_session_templates()
