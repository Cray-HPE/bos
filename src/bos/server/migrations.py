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
import logging

from bos.common.tenant_utils import get_tenant_aware_key
import bos.server.redis_db_utils as dbutils


LOGGER = logging.getLogger('bos.server.migration')

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


if __name__ == "__main__":
    perform_migrations()
