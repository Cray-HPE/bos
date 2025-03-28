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

from itertools import batched
import logging
from typing import Any, Generator

import redis

from bos.common.utils import exc_type_msg

from .defs import DB_HOST, DB_PORT, Databases
from .exceptions import BosDBException, InvalidDBDataType, NotFoundInDB

LOGGER = logging.getLogger(__name__)

class DBWrapper:
    """A wrapper around a Redis database connection

    Because the underlying Redis client is threadsafe, this class is as well,
    and can be safely shared by multiple threads.
    """

    def __init__(self, db: Databases):
        self._db = db
        self._client = self._get_client()

    @property
    def db(self) -> Databases:
        """Return the database identifer"""
        return self._db

    @property
    def db_name(self) -> str:
        """Returns the str representation of the database identifier"""
        return self.db.name

    @property
    def db_id(self) -> int:
        """Returns the int representation of the database identifier"""
        return self.db.value

    def __contains__(self, key: str) -> bool:
        return self.client.exists(key)

    @property
    def client(self) -> redis.Redis:
        return self._client

    def info(self) -> dict:
        """Returns the database info."""
        return self.client.info()

    def _get_client(self) -> redis.Redis:
        """Create a connection with the database."""
        try:
            LOGGER.debug(
                "Creating database connection"
                "host: %s port: %s database: %d", DB_HOST, DB_PORT, self.db_id)
            return redis.Redis(host=DB_HOST, port=DB_PORT, db=self.db_id)
        except Exception as err:
            LOGGER.error("Failed to connect to database %d (%s) : %s", self.db_name,
                         self.db_id, exc_type_msg(err))
            raise BosDBException(db=self.db, msg="Failed to connect to database",
                                 exc=exc_type_msg(err)) from err

    @property
    def ready(self) -> bool:
        """
        Attempt a database query.
        Return False if an exception is raised (and log a warning)
        Return True otherwise.
        """
        try:
            self.info()
        except Exception as err:
            LOGGER.warning("Failed to query database %s : %s", self.db_name, exc_type_msg(err))
            return False
        return True

    def _load_str(self, key: str, data: Any) -> str:
        """
        Converts the DB entry into a str, or raises an appropriate exception
        """
        if data is None:
            # If the client returns None, it means there is no entry for that key
            raise NotFoundInDB(db=self.db, key=key)
        if isinstance(data, (bytes, bytearray)):
            return data.decode()
        if isinstance(data, str):
            return data
        raise InvalidDBDataType(db=self.db, entry_data=data, key=key)

    def get(self, key: str) -> str:
        """Get the data for the given key."""
        data = self.client.get(key)
        return self._load_str(key, data)

    def getdel(self, key: str) -> str:
        """Get the data for the given key and delete it from the DB."""
        data = self.client.getdel(key)
        return self._load_str(key, data)

    def get_all(self) -> list[str]:
        """Get an array of data for all keys."""
        return list(self.iter_values())

    def get_all_as_dict(self) -> dict[str, str]:
        """Return a mapping from all keys to their corresponding data
        """
        return dict(self.iter_items())

    def delete(self, key: str) -> None:
        """
        Deletes data from the database. No need to make this data-type specific, since we don't
        actually return the data.
        """
        # Use get_and_delete so we can raise a Not Found exception if appropriate
        if self.client.getdel(key) is None:
            raise NotFoundInDB(db=self.db, key=key)

    def set(self, key: str, datastr: str) -> None:
        """
        Writes the specified string to the database under the specified key
        """
        self.client.set(key, datastr)

    def keys(self) -> list[str]:
        """
        Sorted list of all current keys in DB
        """
        return sorted({k.decode() for k in self.client.scan_iter()})

    def iter_values(self,
                    start_after_key: str | None = None) -> Generator[str, None, None]:
        """
        Iterate through every item in the database. Parse each item as a string and yield it.
        If start_after_key is specified, skip any keys that are lexically <= the specified key.
        """
        for _, data in self.iter_items(start_after_key=start_after_key):
            yield data

    def iter_items(
        self, start_after_key: str | None = None
    ) -> Generator[tuple[str, str], None, None]:
        """
        Iterate through every item in the database. Parse each item as str and yield it.
        If start_after_key is specified, skip any keys that are lexically <= the specified key.
        """
        if start_after_key is None:
            all_keys = self.keys()
        else:
            all_keys = filter(lambda k: k > start_after_key, self.keys())
        for next_keys in batched(all_keys, 500):
            for key, data in zip(next_keys, self.client.mget(next_keys)):
                if data is not None:
                    yield key, self._load_str(key, data)
