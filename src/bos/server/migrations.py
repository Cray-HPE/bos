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

from bos.common.utils import requests_retry_session
from bos.common.tenant_utils import get_tenant_aware_key
import bos.server.redis_db_utils as dbutils


LOGGER = logging.getLogger('bos.server.migration')


def MissingName():
    """
    The session template's name is missing
    """
    pass


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
    migrate_to_tenant_aware_keys()
    convert_v1_to_v2_session_templates()


if __name__ == "__main__":
    perform_migrations()
