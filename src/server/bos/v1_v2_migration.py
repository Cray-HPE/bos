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
from bos.dbclient import BosEtcdClient
import bos.redis_db_utils as dbutils
LOGGER = logging.getLogger('bos.v1_v2_migration')
DB = dbutils.get_wrapper(db='session_templates')
BASEKEY = "/sessionTemplate"


def migrate_v1_to_v2_session_templates():
    """
    Read the session templates out of the V1 etcd key/value store and
    write them into the v2 Redis database.
    Delete them from etcd once they have been successfully migrated, so
    they are not migrated more than once. 
    """
    with BosEtcdClient() as bec:
        for session_template_byte_str, _meta in bec.get_prefix('{}/'.format(BASEKEY)):
            st = json.loads(session_template_byte_str.decode("utf-8"))
            _ = DB.put(st['name'], st)
            # bec.delete('{}/{}'.format(BASEKEY, st['name']))


if __name__ == "__main__":
  migrate_v1_to_v2_session_templates()
