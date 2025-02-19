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
from collections.abc import Callable
from itertools import batched
import functools
import json
import logging
from typing import Generator, ParamSpec, TypeVar

import connexion
import redis

from bos.common.types.general import JsonDict
from bos.common.utils import exc_type_msg

LOGGER = logging.getLogger(__name__)
DATABASES = [
    "options", "components", "session_templates", "sessions",
    "bss_tokens_boot_artifacts", "session_status"
]  # Index is the db id.

DB_HOST = 'cray-bos-db'
DB_PORT = 6379


class DBWrapper():
    """A wrapper around a Redis database connection

    This handles creating the Redis client and provides REST-like methods for
    modifying json data in the database.

    Because the underlying Redis client is threadsafe, this class is as well,
    and can be safely shared by multiple threads.
    """

    def __init__(self, db: int|str):
        self.db_id = self._get_db_id(db)
        self.client = self._get_client(self.db_id)

    def __contains__(self, key: str) -> bool:
        return self.client.exists(key)

    def _get_db_id(self, db: int|str) -> int:
        """Converts a db name to the id used by Redis."""
        if isinstance(db, int):
            return db
        return DATABASES.index(db)

    def _get_client(self, db_id: int) -> redis.Redis:
        """Create a connection with the database."""
        try:
            LOGGER.debug(
                "Creating database connection"
                "host: %s port: %s database: %s", DB_HOST, DB_PORT, db_id)
            return redis.Redis(host=DB_HOST, port=DB_PORT, db=db_id)
        except Exception as err:
            LOGGER.error("Failed to connect to database %s : %s", db_id,
                         exc_type_msg(err))
            raise

    @property
    def db_string(self) -> str:
        """Returns the string name of the database, from the DATABASES array"""
        return DATABASES[self.db_id]

    @property
    def ready(self) -> bool:
        """
        Attempt a database query.
        Return False if an exception is raised (and log a warning)
        Return True otherwise.
        """
        try:
            self.client.get('')
        except Exception as err:
            LOGGER.warning("Failed to query database %s : %s", self.db_string, exc_type_msg(err))
            return False
        return True

    # The following methods act like REST calls for single items
    def get(self, key: str) -> JsonDict:
        """Get the data for the given key."""
        datastr = self.client.get(key)
        if not datastr:
            return None
        data = json.loads(datastr)
        return data

    def get_and_delete(self, key: str) -> JsonDict:
        """Get the data for the given key and delete it from the DB."""
        datastr = self.client.getdel(key)
        if not datastr:
            return None
        data = json.loads(datastr)
        return data

    def get_all(self) -> list[JsonDict]:
        """Get an array of data for all keys."""
        data = []
        for key in self.client.scan_iter():
            datastr = self.client.get(key)
            single_data = json.loads(datastr)
            data.append(single_data)
        return data

    def get_all_filtered(self,
                         filter_func: Callable[[JsonDict], JsonDict | None],
                         start_after_key: str | None = None,
                         page_size: int = 0) -> list[JsonDict]:
        """
        Get an array of data for all keys after passing them through the specified filter
        (discarding any for which the filter returns None)
        If start_after_id is specified, all ids lexically <= that id will be skipped.
        If page_size is specified, the number of items in the returned list will be equal
        to or less than the page_size.
        More elements may remain and additional queries will be needed to acquire them.
        """
        data = []
        for value in self.iter_values(start_after_key):
            filtered_value = filter_func(value)
            if filtered_value is not None:
                data.append(filtered_value)
                if page_size and len(data) == page_size:
                    break
        return data

    def iter_values(self, start_after_key: str | None = None) -> Generator[JsonDict, None, None]:
        """
        Iterate through every item in the database. Parse each item as JSON and yield it.
        If start_after_key is specified, skip any keys that are lexically <= the specified key.
        """
        all_keys = sorted({k.decode() for k in self.client.scan_iter()})
        if start_after_key is not None:
            all_keys = [k for k in all_keys if k > start_after_key]
        for next_keys in batched(all_keys, 500):
            for datastr in self.client.mget(next_keys):
                yield json.loads(datastr) if datastr else None

    def get_all_as_dict(self) -> dict[str, JsonDict]:
        """Return a mapping from all keys to their corresponding data
           Based on https://github.com/redis/redis-py/issues/984#issuecomment-391404875
        """
        data = {}
        cursor = '0'
        while cursor != 0:
            cursor, keys = self.client.scan(cursor=cursor, count=1000)
            values = [
                json.loads(datastr) if datastr else None
                for datastr in self.client.mget(keys)
            ]
            keys = [k.decode() for k in keys]
            data.update(dict(zip(keys, values)))
        return data

    def get_keys(self) -> list[bytes]:
        """Get an array of all keys"""
        data = []
        for key in self.client.scan_iter():
            data.append(key)
        return data

    def put(self, key: str, new_data: JsonDict) -> JsonDict:
        """Put data in to the database, replacing any old data."""
        datastr = json.dumps(new_data)
        self.client.set(key, datastr)
        return self.get(key)

    def patch(self, key: str, new_data: JsonDict,
              data_handler: Callable[[JsonDict],JsonDict] | None=None) -> JsonDict:
        """Patch data in the database.
           data_handler provides a way to operate on the full patched data"""
        datastr = self.client.get(key)
        data = json.loads(datastr)
        data = self._update(data, new_data)
        if data_handler:
            data = data_handler(data)
        datastr = json.dumps(data)
        self.client.set(key, datastr)
        return self.get(key)

    def rename(self, old_key: str, new_key: str):
        """
        Store data from old_key under new_key instead
        """
        self.client.rename(old_key, new_key)

    def _update(self, data: JsonDict, new_data: JsonDict) -> JsonDict:
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

    def delete(self, key: str) -> None:
        """Deletes data from the database."""
        self.client.delete(key)

    def info(self) -> dict:
        """Returns the database info."""
        return self.client.info()


P = ParamSpec('P')
R = TypeVar('R')

def redis_error_handler(func: Callable[P, R]) -> Callable[P, R]:
    """Decorator for returning better errors if Redis is unreachable"""

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            if 'body' in kwargs:
                # Our get/patch functions don't take body, but the **kwargs
                # in the arguments to this wrapper cause it to get passed.
                del kwargs['body']
            return func(*args, **kwargs)
        except redis.exceptions.ConnectionError as e:
            LOGGER.error('Unable to connect to the Redis database: %s', e)
            return connexion.problem(
                status=503,
                title='Unable to connect to the Redis database',
                detail=str(e))

    return wrapper


def get_wrapper(db: int|str) -> DBWrapper:
    """Returns a database object."""
    return DBWrapper(db)
