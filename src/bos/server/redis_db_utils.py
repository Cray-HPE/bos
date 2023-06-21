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
import functools
import json
import logging
import redis

LOGGER = logging.getLogger(__name__)
DATABASES = ["options", "components", "session_templates", "sessions", "bss_tokens_boot_artifacts", "session_status"]  # Index is the db id.

DB_HOST = 'cray-bos-db'
DB_PORT = 6379


class DBWrapper():
    """A wrapper around a Redis database connection

    This handles creating the Redis client and provides REST-like methods for
    modifying json data in the database.

    Because the underlying Redis client is threadsafe, this class is as well,
    and can be safely shared by multiple threads.
    """

    def __init__(self, db):
        db_id = self._get_db_id(db)
        self.client = self._get_client(db_id)

    def __contains__(self, key):
        return self.client.exists(key)

    def _get_db_id(self, db):
        """Converts a db name to the id used by Redis."""
        if isinstance(db, int):
            return db
        else:
            return DATABASES.index(db)

    def _get_client(self, db_id):
        """Create a connection with the database."""
        try:
            LOGGER.debug("Creating database connection"
                         "host: %s port: %s database: %s",
                         DB_HOST, DB_PORT, db_id)
            return redis.Redis(host=DB_HOST, port=DB_PORT, db=db_id)
        except Exception as err:
            LOGGER.error("Failed to connect to database %s : %s",
                         db_id, err)
            raise

    # The following methods act like REST calls for single items
    def get(self, key):
        """Get the data for the given key."""
        datastr = self.client.get(key)
        if not datastr:
            return None
        data = json.loads(datastr)
        return data

    def get_all(self):
        """Get an array of data for all keys."""
        data = []
        for key in self.client.scan_iter():
            datastr = self.client.get(key)
            single_data = json.loads(datastr)
            data.append(single_data)
        return data

    def get_keys(self):
        """Get an array of all keys"""
        data = []
        for key in self.client.scan_iter():
            data.append(key)
        return data

    def put(self, key, new_data):
        """Put data in to the database, replacing any old data."""
        datastr = json.dumps(new_data)
        self.client.set(key, datastr)
        return self.get(key)

    def patch(self, key, new_data, data_handler=None):
        """Patch data in the database."""
        """data_handler provides a way to operate on the full patched data"""
        datastr = self.client.get(key)
        data = json.loads(datastr)
        data = self._update(data, new_data)
        if data_handler:
            data = data_handler(data)
        datastr = json.dumps(data)
        self.client.set(key, datastr)
        return self.get(key)

    def _update(self, data, new_data):
        """Recursively patches json to allow sub-fields to be patched.

        Keyword arguments:
        data -- A dictionary of json data
        new_data -- A dictionary of json data in the same format as "data"
        """
        for k, v in new_data.items():
            if isinstance(v, dict):
                data[k] = self._update(data.get(k, {}), v)
            else:
                data[k] = v
        return data

    def delete(self, key):
        """Deletes data from the database."""
        self.client.delete(key)

    def info(self):
        """Returns the database info."""
        return self.client.info()


def redis_error_handler(func):
    """Decorator for returning better errors if Redis is unreachable"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            if 'body' in kwargs:
                # Our get/patch functions don't take body, but the **kwargs
                # in the arguments to this wrapper cause it to get passed.
                del kwargs['body']
            return func(*args, **kwargs)
        except redis.exceptions.ConnectionError as e:
            LOGGER.error('Unable to connect to the Redis database: {}'.format(e))
            return connexion.problem(
                status=503, title='Unable to connect to the Redis database',
                detail=str(e))

    return wrapper


def get_wrapper(db):
    """Returns a database object."""
    return DBWrapper(db)
