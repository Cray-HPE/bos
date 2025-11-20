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
from collections.abc import Callable, Generator, Iterable
from itertools import batched, islice
import json
import logging
from typing import (ClassVar,
                    Generic,
                    Protocol,
                    cast)

import redis
from redis.maint_notifications import MaintNotificationsConfig

from bos.common.types.general import JsonData, JsonDict
from bos.common.utils import exc_type_msg

from .defs import DB_HOST, DB_PORT, Databases
from .defs import BosDataRecord as DataT
from .exceptions import (BosDBException,
                         InvalidDBDataType,
                         InvalidDBJsonDataType,
                         NonJsonDBData,
                         NotFoundInDB)

LOGGER = logging.getLogger(__name__)

class SpecificDatabase(Protocol): # pylint: disable=too-few-public-methods
    """ Require that some classes set the _Database class variable """
    _Database: ClassVar[Databases]

# If you list Generic[DataT] before SpecificDatabase, you get a MRO TypeError at runtime
class DBWrapper(SpecificDatabase, Generic[DataT], ABC):
    """A wrapper around a Redis database connection

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
        Return False if an exception is raised
        Return True otherwise.
        """
        try:
            self.info()
        except Exception as err:
            LOGGER.debug("Failed to query database %s : %s", self.db.name, exc_type_msg(err))
            return False
        return True

    def __contains__(self, key: str, /) -> bool:
        # The redis type annotations are not ideal, so we need to use cast here
        return cast(bool, self.client.exists(key))

    @abstractmethod
    def _jsondict_to_bosdata(self, key: str, jsondict: JsonDict, /) -> DataT: ...

    def _load_jsondict(self, key: str, data: object, /) -> JsonDict:
        """
        Parses entry as JSON and verifies it is a dict, or raises an appropriate exception.
        """
        if data is None:
            raise NotFoundInDB(db=self.db, key=key)

        # Make sure the data is str, bytes, or bytearray (the valid inputs for JSON decoding)
        if not isinstance(data, (bytes, bytearray, str)):
            raise InvalidDBDataType(db=self.db, entry_data=data, key=key)

        try:
            jsondata = json.loads(data)
        except json.decoder.JSONDecodeError as exc:
            raise NonJsonDBData(self.db, key=key, entry_data=data,
                                exc=exc_type_msg(exc)) from exc

        # Because we just loaded the data using json.load, we know the format is JSON
        # The only thing we really need to make sure of is that it's a dict
        if not isinstance(jsondata, dict):
            # Cast the entry data for poor mypy, since we know it is JsonData
            raise InvalidDBJsonDataType(db=self.db, key=key, entry_data=cast(JsonData, jsondata))

        # Cast the type as JsonDict, so mypy has no doubts
        return cast(JsonDict, jsondata)

    def _load_bosdata(self, key: str, data: object, /) -> DataT:
        jsondict = self._load_jsondict(key, data)
        return self._jsondict_to_bosdata(key, jsondict)

    def get(self, key: str, /) -> DataT:
        """Get the data for the given key."""
        # The redis type annotations are not ideal, so we need to use cast here
        # But we cast to object to avoid making any assumptions about its type
        # We do this rather than casting to Any since the Any type bypasses type checking
        data = cast(object, self.client.get(key))
        return self._load_bosdata(key, data)

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

    def get_and_delete_raw(self, key: str, /) -> JsonDict:
        """Get the data for the given key and delete it from the DB."""
        # The redis type annotations are not ideal, so we need to use cast here
        # But we cast to object to avoid making any assumptions about its type
        # We do this rather than casting to Any since the Any type bypasses type checking
        data = cast(object, self.client.getdel(key))
        return self._load_jsondict(key, data)

    def get_and_delete(self, key: str, /) -> DataT:
        jsondict = self.get_and_delete_raw(key)
        return self._jsondict_to_bosdata(key, jsondict)

    def get_all(self) -> list[DataT]:
        """Get an array of data for all keys."""
        return list(self.iter_values())

    def get_all_as_raw_dict(self) -> dict[str, JsonDict]:
        """Return a mapping from all keys to their corresponding data, only JSON
           decoding and not otherwise parsing the data
        """
        return dict(self.iter_items_raw())

    def get_all_filtered[OutDataT](self,
                         filter_func: Callable[[DataT], OutDataT | None], *,
                         start_after_key: str | None = None,
                         specific_keys: Iterable[str] | None = None,
                         page_size: int = 0) -> list[OutDataT]:
        """
        Get an array of data for all keys after passing them through the specified filter
        (discarding any for which the filter returns None)
        If start_after_id is specified, all ids lexically <= that id will be skipped.
        If page_size is specified, the number of items in the returned list will be equal
        to or less than the page_size.
        More elements may remain and additional queries will be needed to acquire them.
        """
        filtered_values_including_nones = map(filter_func,
                                              self.iter_values(start_after_key=start_after_key,
                                                               specific_keys=specific_keys))
        filtered_values = (data for data in filtered_values_including_nones if data is not None)
        if page_size:
            return list(islice(filtered_values, page_size))
        return list(filtered_values)

    def mget(self, keys: Iterable[str], /) -> dict[str, DataT]:
        """
        Returns a mapping from the specified keys to the corresponding BOS data records.
        Raises exception if any are not found.
        """
        raw_data_list: list[object] = []
        for key_sublist in batched(keys, 500):
            # The redis type annotations are not ideal, so we need to use cast here
            # But we cast to object to avoid making any assumptions about its type
            # We do this rather than casting to Any since the Any type bypasses type checking
            raw_data_sublist = cast(list[object], self.client.mget(key_sublist))
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
        return { key: self._load_bosdata(key, data) for key, data in zip(keys, raw_data_list) }

    def mget_skip_bad_keys(self, keys: Iterable[str], /) -> dict[str, DataT]:
        """
        Returns a mapping from the specified keys to the corresponding BOS data records.
        Omits from the mapping any keys which do not exist in the DB.
        """
        # The redis type annotations are not ideal, so we need to use cast here
        # But we cast to object to avoid making any assumptions about its type
        # We do this rather than casting to Any since the Any type bypasses type checking
        raw_data_list: list[object] = cast(list[object], self.client.mget(keys))
        return { key: self._load_bosdata(key, data)
                 for key, data in zip(keys, raw_data_list) if data is not None }

    def mput(self, key_data_map: dict[str, DataT] | dict[str, JsonDict], /) -> None:
        """
        JSON-encode all data and then write each item to the database under its respective key
        """
        self.client.mset({ key: json.dumps(data) for key, data in key_data_map.items()})

    def iter_values(self, /, *,
                    start_after_key: str | None = None,
                    specific_keys: Iterable[str] | None = None) -> Generator[DataT, None, None]:
        """
        Iterate through every item in the database. Parse each item as a string and yield it.
        If start_after_key is specified, skip any keys that are lexically <= the specified key.
        """
        for _, data in self.iter_items(start_after_key=start_after_key,
                                       specific_keys=specific_keys):
            yield data

    def iter_keys(self, /, *,
                  start_after_key: str | None = None,
                  specific_keys: Iterable[str] | None = None) -> Generator[str, None, None]:
        """
        Sorted list of all current keys in DB
        """
        all_keys_set = {k.decode() for k in self.client.scan_iter()}
        if specific_keys is not None:
            all_keys_set.intersection_update(specific_keys)
        all_keys_list = sorted(all_keys_set)
        if start_after_key is None:
            yield from all_keys_list
        else:
            yield from filter(lambda k: k > start_after_key, all_keys_list)

    def _iter_items[DataFormat](
        self, /, *, start_after_key: str | None,
        load_func: Callable[[str, object], DataFormat],
        specific_keys: Iterable[str] | None
    ) -> Generator[tuple[str, DataFormat], None, None]:
        """
        Iterate through every item in the database. Parse each item using the specified function
        and yield it.
        If start_after_key is specified, skip any keys that are lexically <= the specified key.
        """
        for next_keys in batched(self.iter_keys(start_after_key=start_after_key,
                                                specific_keys=specific_keys), 500):
            # The redis type annotations are not ideal, so we need to use cast here
            # But we cast to object to avoid making any assumptions about its type
            # We do this rather than casting to Any since the Any type bypasses type checking
            data_list = cast(Iterable[object], self.client.mget(next_keys))
            for key, data in zip(next_keys, data_list):
                if data is not None:
                    yield key, load_func(key, data)

    def iter_items(
        self, /, *, start_after_key: str | None = None,
        specific_keys: Iterable[str] | None = None
    ) -> Generator[tuple[str, DataT], None, None]:
        """
        Wrapper for _iter_items that specified the appropriate BOS data type loading function,
        and defaults start_after_key to None.
        """
        yield from self._iter_items(start_after_key=start_after_key, load_func=self._load_bosdata,
                                    specific_keys=specific_keys)

    def iter_items_raw(self) -> Generator[tuple[str, JsonDict], None, None]:
        """
        Intended for use by the BOS migration job. Wrapper for _iter_items that only does JSON
        decoding, not any further data processing.
        """
        yield from self._iter_items(start_after_key=None, load_func=self._load_jsondict,
                                    specific_keys=None)

def _get_redis_client(db: Databases) -> redis.client.Redis:
    """Create a connection with the database."""
    LOGGER.debug("Creating database connection host: %s port: %s database: %d (%s)",
                 DB_HOST, DB_PORT, db.value, db.name)
    try:
        # explicitly disabling maint_notifications, to avoid a warning message being logged, as
        # they're not supported (although it causes no problems beyond the warning message)
        mn_config = MaintNotificationsConfig(enabled=False)
        rclient: redis.client.Redis = redis.Redis(host=DB_HOST,
                                                  port=DB_PORT,
                                                  db=db.value,
                                                  protocol=3,
                                                  maint_notifications_config=mn_config)
    except Exception as err:
        LOGGER.error("Failed to connect to database %d (%s) : %s", db.value, db.name,
                     exc_type_msg(err))
        raise BosDBException(db=db, msg="Failed to connect to database",
                             exc=exc_type_msg(err)) from err
    return rclient
