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
"""
DBWrapper class
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from itertools import batched
import json
import logging
from typing import Any, Generator, cast

import redis

from bos.common.types.general import BosDataRecord
from bos.common.utils import exc_type_msg

from .defs import DB_HOST, DB_PORT, Databases
from .exceptions import NotFoundInDB

LOGGER = logging.getLogger(__name__)

class DBWrapper[DataT: BosDataRecord](ABC):
    """A wrapper around a Redis database connection

    This handles creating the Redis client and provides REST-like methods for
    modifying json data in the database.

    Because the underlying Redis client is threadsafe, this class is as well,
    and can be safely shared by multiple threads.
    """

    def __init__(self):
        self.client = self._get_client()

    def __contains__(self, key: str) -> bool:
        return self.client.exists(key)

    # @property has to be listed before @abstractmethod, or you get runtime errors
    @property
    @abstractmethod
    def db_id(self) -> Databases:
        """Return the integer database ID"""

    def _get_client(self) -> redis.Redis:
        """Create a connection with the database."""
        try:
            LOGGER.debug(
                "Creating database connection"
                "host: %s port: %s database: %d", DB_HOST, DB_PORT, self.db_id)
            return redis.Redis(host=DB_HOST, port=DB_PORT, db=int(self.db_id))
        except Exception as err:
            LOGGER.error("Failed to connect to database %d : %s", self.db_id,
                         exc_type_msg(err))
            raise

    @property
    def db_string(self) -> str:
        """Returns the string name of the database"""
        return self.db_id.name

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

    def _load_entry(self, key: str, data: Any, /) -> DataT:
        if data is None:
            raise NotFoundInDB(db=self.db_id, key=key)
        return cast(DataT, json.loads(data))

    # The following methods act like REST calls for single items
    def get(self, key: str) -> DataT:
        """Get the data for the given key."""
        data = self.client.get(key)
        return self._load_entry(key, data)

    def get_and_delete(self, key: str) -> DataT:
        """Get the data for the given key and delete it from the DB."""
        data = self.client.getdel(key)
        return self._load_entry(key, data)

    def get_all(self) -> list[DataT]:
        """Get an array of data for all keys."""
        return list(self._iter_values())

    def get_all_as_dict(self) -> dict[str, DataT]:
        """Return a mapping from all keys to their corresponding data
           Based on https://github.com/redis/redis-py/issues/984#issuecomment-391404875
        """
        data = {}
        cursor = '0'
        while cursor != 0:
            cursor, keys = self.client.scan(cursor=cursor, count=1000)
            values = [
                None if datastr is None else self._load_entry(key, datastr)
                for key, datastr in zip(keys, self.client.mget(keys))
            ]
            keys = [k.decode() for k in keys]
            data.update(dict(zip(keys, values)))
        return data

    def get_all_filtered(self,
                         filter_func: Callable[[DataT], DataT | None],
                         start_after_key: str | None = None,
                         page_size: int = 0) -> list[DataT]:
        """
        Get an array of data for all keys after passing them through the specified filter
        (discarding any for which the filter returns None)
        If start_after_id is specified, all ids lexically <= that id will be skipped.
        If page_size is specified, the number of items in the returned list will be equal
        to or less than the page_size.
        More elements may remain and additional queries will be needed to acquire them.
        """
        data = []
        for value in self._iter_values(start_after_key):
            filtered_value = filter_func(value)
            if filtered_value is not None:
                data.append(filtered_value)
                if page_size and len(data) == page_size:
                    break
        return data

    def _iter_values(self, start_after_key: str | None = None) -> Generator[DataT, None, None]:
        """
        Iterate through every item in the database. Parse each item as JSON and yield it.
        If start_after_key is specified, skip any keys that are lexically <= the specified key.
        """
        all_keys = sorted({k.decode() for k in self.client.scan_iter()})
        if start_after_key is not None:
            all_keys = [k for k in all_keys if k > start_after_key]
        for next_keys in batched(all_keys, 500):
            for key, data in zip(next_keys, self.client.mget(next_keys)):
                if data is not None:
                    yield self._load_entry(key, data)

    def put(self, key: str, new_data: DataT) -> None:
        """Put data in to the database, replacing any old data."""
        datastr = json.dumps(new_data)
        self.client.set(key, datastr)

    def delete(self, key: str) -> None:
        """Deletes data from the database."""
        # Use get_and_delete so we can raise a Not Found exception if appropriate
        if self.client.getdel(key) is None:
            raise NotFoundInDB(db=self.db_id, key=key)

    def info(self) -> dict:
        """Returns the database info."""
        return self.client.info()
