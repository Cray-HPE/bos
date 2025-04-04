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
from typing import Any, ClassVar, Generator, Iterable, Protocol, cast

import redis

from bos.common.types.general import BosDataRecord, JsonDict
from bos.common.utils import exc_type_msg

from .defs import DB_HOST, DB_PORT, Databases
from .exceptions import BosDBException, NotFoundInDB

LOGGER = logging.getLogger(__name__)

class SpecificDatabase(Protocol): # pylint: disable=too-few-public-methods
    """ Require that some classes set the _Database class variable """
    _Database: ClassVar[Databases]

class DBWrapper[DataT: BosDataRecord](SpecificDatabase, ABC):
    """A wrapper around a Redis database connection

    This handles creating the Redis client and provides REST-like methods for
    modifying json data in the database.

    Because the underlying Redis client is threadsafe, this class is as well,
    and can be safely shared by multiple threads.
    """

    def __init__(self) -> None:
        self._client = _get_redis_client(self.db)

    @property
    def db(self) -> Databases:
        """Return the database identifer"""
        return self._Database

    @property
    def client(self) -> redis.Redis:
        return self._client

    def info(self) -> dict:
        """Returns the database info."""
        # The redis type annotations are not ideal, so we need to use cast here
        return cast(dict, self.client.info())

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
            LOGGER.warning("Failed to query database %s : %s", self.db.name, exc_type_msg(err))
            return False
        return True

    def __contains__(self, key: str, /) -> bool:
        # The redis type annotations are not ideal, so we need to use cast here
        return cast(bool, self.client.exists(key))

    def _load_entry(self, key: str, data: Any, /) -> DataT:
        if data is None:
            raise NotFoundInDB(db=self.db, key=key)
        return cast(DataT, json.loads(data))

    def get(self, key: str, /) -> DataT:
        """Get the data for the given key."""
        data = self.client.get(key)
        return self._load_entry(key, data)

    def delete(self, key: str, /) -> None:
        """
        Deletes data from the database. No need to make this data-type specific, since we don't
        actually return the data.
        """
        # Use get_and_delete so we can raise a Not Found exception if appropriate
        if self.client.getdel(key) is None:
            raise NotFoundInDB(db=self.db, key=key)

    def put(self, key: str, data: DataT | JsonDict, /) -> None:
        """
        JSON-encode the specified data and write it to the database under the specified key
        """
        self.client.set(key, json.dumps(data))

    def get_and_delete(self, key: str, /) -> DataT:
        """Get the data for the given key and delete it from the DB."""
        data = self.client.getdel(key)
        return self._load_entry(key, data)

    def get_all(self) -> list[DataT]:
        """Get an array of data for all keys."""
        return list(self._iter_values())

    def get_all_as_raw_dict(self) -> dict[str, JsonDict]:
        """Return a mapping from all keys to their corresponding data, only JSON
           decoding and not otherwise parsing the data
           Based on https://github.com/redis/redis-py/issues/984#issuecomment-391404875
        """
        datadict: dict[str, JsonDict] = {}
        cursor = '0'
        while cursor != 0:
            cursor, keys = self.client.scan(cursor=cursor, count=1000)
            datadict.update({
                key.decode(): json.loads(data)
                for key, data in zip(keys, self.client.mget(keys))
                if data is not None
            })
        return datadict

    def get_all_filtered(self,
                         filter_func: Callable[[DataT], DataT | None], *,
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
        for value in self._iter_values(start_after_key=start_after_key):
            filtered_value = filter_func(value)
            if filtered_value is not None:
                data.append(filtered_value)
                if page_size and len(data) == page_size:
                    break
        return data

    def mget(self, keys: Iterable[str], /) -> dict[str, DataT]:
        """
        Returns a mapping from the specified keys to the corresponding BOS data records.
        Raises exception if any are not found.
        """
        raw_data_list: list[Any] = []
        for key_sublist in batched(keys, 500):
            raw_data_sublist = cast(list[Any], self.client.mget(key_sublist))
            try:
                none_index = raw_data_sublist.index(None)
            except ValueError:
                # This means we got back no None values from the mget call,
                # meaning that all of the keys exist in the database.
                raw_data_list.extend(raw_data_sublist)
            else:
                # No ValueError was raised -- meaning none_index is set to the
                # first index with a None value
                raise NotFoundInDB(db=self.db, key=key_sublist[none_index])
        return { key: self._load_entry(key, data) for key, data in zip(keys, raw_data_list) }

    def mput(self, key_data_map: dict[str, DataT] | dict[str, JsonDict], /) -> None:
        """
        JSON-encode all data and then write each item to the database under its respective key
        """
        self.client.mset({ key: json.dumps(data) for key, data in key_data_map.items()})

    def _iter_values(self, /, *,
                    start_after_key: str | None = None) -> Generator[DataT, None, None]:
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

def _get_redis_client(db: Databases) -> redis.Redis:
    """Create a connection with the database."""
    LOGGER.debug("Creating database connection host: %s port: %s database: %d (%s)",
                 DB_HOST, DB_PORT, db.value, db.name)
    try:
        return redis.Redis(host=DB_HOST, port=DB_PORT, db=db.value)
    except Exception as err:
        LOGGER.error("Failed to connect to database %d (%s) : %s", db.value, db.name,
                     exc_type_msg(err))
        raise BosDBException(db=db, msg="Failed to connect to database",
                             exc=exc_type_msg(err)) from err
