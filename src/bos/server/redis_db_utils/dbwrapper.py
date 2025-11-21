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
from collections.abc import (
                                Callable,
                                Collection,
                                Generator,
                                Iterable,
                                Mapping,
                                MutableMapping
                            )
import copy
from dataclasses import dataclass
from itertools import batched, islice
import json
import logging
import time
from typing import (ClassVar,
                    Generic,
                    Literal,
                    Protocol,
                    Self,
                    cast)

import redis
from redis.maint_notifications import MaintNotificationsConfig

from bos.common.types.general import JsonData, JsonDict
from bos.common.utils import exc_type_msg

from .convert_db_watch_errors import convert_db_watch_errors
from .defs import DB_BATCH_SIZE, DB_BUSY_SECONDS, DB_HOST, DB_PORT, Databases
from .defs import BosDataRecord as DataT
from .exceptions import (BosDBException,
                         InvalidDBDataType,
                         InvalidDBJsonDataType,
                         NonJsonDBData,
                         NotFoundInDB)
from .redis_pipeline import redis_pipeline

LOGGER = logging.getLogger(__name__)

class EntryChecker[DataT](Protocol):
    def __call__(self, data: DataT, /) -> bool: ...

class PatchHandler[DataT, PatchDataFormat](Protocol):
    def __call__(self, data: DataT, patch_data: PatchDataFormat, /) -> None: ...


@dataclass(slots=True, frozen=True)
class BulkDictPatchOptions[DataT, PatchDataFormat]:
    key_patch_data_map: Mapping[str, PatchDataFormat]
    patch_handler: PatchHandler[DataT, PatchDataFormat]
    skip_nonexistent_keys: bool
    data_filter: None = None

    def apply_patch(self, key: str, data: DataT, /) -> None:
        self.patch_handler(data, self.key_patch_data_map[key])

@dataclass(slots=True, frozen=True)
class BulkPatchOptions[DataT, PatchDataFormat]:
    patch_data: PatchDataFormat
    patch_handler: PatchHandler[DataT, PatchDataFormat]
    data_filter: EntryChecker[DataT]
    skip_nonexistent_keys: Literal[True] = True

    def apply_patch(self, _: str, data: DataT, /) -> None:
        """
        String argument present to make this function signature
        match the one in BulkDictPatchOptions
        """
        self.patch_handler(data, self.patch_data)

@dataclass(slots=True)
class BulkPatchStatus[DataT]:
    patched_data_map: MutableMapping[str, DataT]
    keys_done: set[str]
    keys_left: list[str]
    no_retries_after: float
    batch_size: int = DB_BATCH_SIZE

    def patch_applied(self, key: str, data: DataT, /) -> None:
        self.patched_data_map[key] = data
        self.keys_done.add(key)

    def patches_applied(self, key_data_map: Mapping[str, DataT], /) -> None:
        self.patched_data_map.update(key_data_map)
        self.keys_done.update(key_data_map)

    def skip_key(self, key: str, /) -> None:
        self.keys_done.add(key)

    def update_keys_left(self) -> None:
        if not self.keys_done:
            # Nothing to do
            return

        # Create a new keys_left list without the keys from keys_done
        self.keys_left = [ k for k in self.keys_left if k not in self.keys_done ]

        # Clear the keys_done set
        self.keys_done.clear()

    @property
    def timed_out(self) -> bool:
        return time.time() > self.no_retries_after

    def __bool__(self) -> bool:
        """
        Updates keys_left
        Then returns True if any keys are left, false otherwise
        """
        self.update_keys_left()
        return bool(self.keys_left)

    @classmethod
    def new_bulk_patch(cls, keys_left: list[str], batch_size: int|None = None) -> Self:
        keys_done: set[str] = set()
        patched_data_map: dict[str, DataT] = {}
        # Set the time after which we will perform no more DB retries.
        # Note that this is not the same as it being a hard timeout. If no Redis
        # WatchErrors are raised after this time limit has been passed, then the method
        # will run to completion, regardless of how long it takes. This is solely
        # present to avoid a method which endlessly keeps retrying.
        no_retries_after: float = time.time() + DB_BUSY_SECONDS

        if batch_size is None:
            return cls(keys_left=keys_left, keys_done=keys_done, patched_data_map=patched_data_map,
                       no_retries_after=no_retries_after)
        return cls(keys_left=keys_left, keys_done=keys_done, patched_data_map=patched_data_map,
                   no_retries_after=no_retries_after, batch_size=batch_size)

    @property
    def key_batches(self) -> Generator[tuple[str, ...], None, None]:
        yield from batched(self.keys_left, self.batch_size)

    @property
    def patched_data_list(self) -> list[DataT]:
        return [ self.patched_data_map[key] for key in sorted(self.patched_data_map) ]

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

    @redis_pipeline
    def _conditional_put(self,
                         pipe: redis.client.Pipeline,
                         *,
                         key: str,
                         new_data: DataT,
                         checker: EntryChecker[DataT]) -> bool:
        """
        Note:
        The pipe argument does not exist as far as the caller of this method is concerned.
        That argument is automatically provided by the @redis_pipeline wrapper.
        """
        pipe.watch(key)
        # The redis type annotations are not ideal, so we need to use cast here
        # But we cast to object to avoid making any assumptions about its type
        # We do this rather than casting to Any since the Any type bypasses type checking
        db_data_raw = cast(object, pipe.get(key))
        db_data = self._load_bosdata(key, db_data_raw)
        if not checker(db_data):
            return False
        # Encode the updated data as a JSON string
        new_data_str = json.dumps(new_data)
        pipe.multi()
        pipe.set(key, new_data_str)
        pipe.execute()
        return True

    @convert_db_watch_errors
    def conditional_put(self, key: str, data: DataT, /, checker: EntryChecker[DataT]) -> bool:
        """
        Reads key entry from DB and decodes it into DataT.
        Calls checker on it.
        If checker is True, encodes data as JSON and writes it to key.
        Returns the return value of checker.
        Will automatically retry if the DB value of key changes while we are doing this.
        """
        while True:
            try:
                # At the time of this writing, pylint is not clever enough to understand
                # the function signature mutation performed by the @redis_pipeline
                # decorator, and so it falsely reports that we are missing an argument
                # here.
                # pylint: disable=no-value-for-parameter
                return self._conditional_put(key=key, new_data=data, checker=checker)
            except redis.exceptions.WatchError:
                pass

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

    def mput(self, key_data_map: Mapping[str, DataT] | Mapping[str, JsonDict], /) -> None:
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

    @redis_pipeline
    def _patch[PatchDataFormat](
        self,
        pipe: redis.client.Pipeline,
        *,
        key: str,
        patch_data: PatchDataFormat,
        patch_handler: PatchHandler[DataT, PatchDataFormat],
        default_entry: DataT | None
    ) -> DataT:
        """
        Helper function for patch, which tries to apply the patch inside a Redis pipeline.
        Returns the updated entry data if successful.
        The pipeline will raise a Redis WatchError otherwise.

        Note:
        The pipe argument does not exist as far as the caller of this method is concerned.
        That argument is automatically provided by the @redis_pipeline wrapper.
        """
        # Mark this key for monitoring before we retrieve its data,
        # so that we know if it changes underneath us.
        pipe.watch(key)

        # Because we have not yet called pipe.multi(), this DB
        # get call will execute immediately and return the data.
        #
        # The redis type annotations are not ideal, so we need to use cast here
        # But we cast to object to avoid making any assumptions about its type
        # We do this rather than casting to Any since the Any type bypasses type checking
        raw_data = cast(object, pipe.get(key))

        orig_data: DataT | None
        new_data: DataT
        if raw_data is not None:
            orig_data = self._load_bosdata(key, raw_data)

            # Start by making a copy of the data, so that we can compare
            # the final patched version to it, and see if it has been changed
            # (this is necessary because many of the BOS patching functions change the
            # data in place, as well as returning it)
            new_data = copy.deepcopy(orig_data)

            # Apply the patch_data to the current data
            patch_handler(new_data, patch_data)
        elif default_entry is not None:
            # A default entry was specified, so we will apply the patch
            # on that.
            orig_data = None
            new_data = copy.deepcopy(default_entry)
            patch_handler(new_data, patch_data)
        else:
            # No default entry specified
            # Raise an exception if no or null entry.
            raise NotFoundInDB(db=self.db, key=key)

        # If the data has not changed, no need to continue
        if orig_data == new_data:
            return new_data

        # Encode the updated data as a JSON string
        data_str = json.dumps(new_data)

        # Begin our transaction.
        pipe.multi()

        # Because this is after the pipe.multi() call, the following
        # set command is not executed immediately, and instead is
        # queued up. The return value from this call is not the
        # return value for the actual DB call.
        pipe.set(key, data_str)

        # Calling pipe.execute() does one of two things:
        # 1. If the key we are watching has not changed since we started
        #    watching it, then our DB set operation will be executed.
        #    The return value of pipe.execute() is a list of the responses
        #    from all of the queued DB commands (in our case, just a single
        #    command -- the set). We don't really care about the response.
        #    If the set failed, Redis would raise an exception, and that's
        #    all we're really concerned about.
        # 2. If they key we are watching DID change, then the queued DB
        #    operations (the set, in our case) are aborted and a Redis WatchError
        #    exception will be raised, and the caller will have to decide how
        #    to deal with it.
        pipe.execute()

        # If we get here, it means no exception was raised by pipe.execute, so we
        # should return the updated data.
        return new_data

    @convert_db_watch_errors
    def patch[PatchDataFormat](
        self,
        key: str,
        patch_data: PatchDataFormat,
        /, *,
        patch_handler: PatchHandler[DataT, PatchDataFormat],
        default_entry: DataT | None = None
    ) -> DataT:
        """
        Patch data in the database.
        If the entry does not exist in the DB:
            If default_entry is None, then DBNoEntryError is raised.
            Otherwise, the patch is applied on top of the specified default entry
            (and written to the DB).
        patch_handler provides an option to specify a non-default patch function.
        """
        # Set the time after which we will perform no more DB retries.
        # Note that this is not the same as it being a hard timeout. If no Redis
        # WatchErrors are raised after this time limit has been passed, then the method
        # will run to completion, regardless of how long it takes. This is solely
        # present to avoid a method which endlessly keeps retrying.
        no_retries_after: float = time.time() + DB_BUSY_SECONDS

        # The loop condition is a simple True because the logic for exiting the loop is
        # contained inside the loop itself.
        while True:
            try:
                # Call a helper function to try and patch the entry. If it is successful,
                # it will return the updated data, which we will return to our caller.
                # If it is unsuccessful, an exception will be raised.
                #
                # At the time of this writing, pylint is not clever enough to understand
                # the function signature mutation performed by the @redis_pipeline
                # decorator, and so it falsely reports that we are missing an argument
                # here.
                # pylint: disable=no-value-for-parameter
                return self._patch(key=key,
                                   patch_data=patch_data,
                                   patch_handler=patch_handler,
                                   default_entry=default_entry)
            except redis.exceptions.WatchError as err:
                # This means the entry changed values while the helper function was
                # trying to patch it.
                if time.time() > no_retries_after:
                    # We are past the last allowed retry time, so re-raise the exception
                    raise err

                # We are not past the time limit, so just log a warning and we'll go back to the
                # top of the loop.
                LOGGER.warning("Key '%s' changed (%s); retrying", key, err)


    @redis_pipeline
    def _bulk_patch[PatchDataFormat](
        self,
        pipe: redis.client.Pipeline,
        *,
        keys: Collection[str],
        patch_options: BulkPatchOptions[DataT, PatchDataFormat] | BulkDictPatchOptions[DataT, PatchDataFormat],
        patch_status: BulkPatchStatus[DataT]
    ) -> None:
        # Mapping from keys to the updated data to be written to the DB
        pending_patched_data_map: dict[str, DataT] = {}

        # If no keys were specified we're done already
        if not keys:
            return

        # Mapping from keys to the updated JSON-encoded data strings
        pending_patched_raw_data_map: dict[str, str] = {}

        # Start by watching all of the keys in this batch
        # This has to be done before we call mget for them.
        pipe.watch(*keys)

        # Retrieve all of the specified keys from the database
        # All database calls to pipe will be executed immediately,
        # since we have not yet called pipe.multi()
        #
        # The redis type annotations are not ideal, so we need to use cast here
        # But we cast to object to avoid making any assumptions about its type
        # We do this rather than casting to Any since the Any type bypasses type checking
        raw_data_list = cast(list[object], pipe.mget(*keys))

        if not patch_options.skip_nonexistent_keys:
            # In this case, check for None values before parsing
            # any of the data further, since the parsing is more
            # time consuming
            for key, raw_data in zip(keys, raw_data_list):
                if raw_data is None:
                    raise NotFoundInDB(db=self.db, key=key)

        for key, raw_data in zip(keys, raw_data_list):
            if not raw_data:
                # Already empty, cannot patch it
                # skip_nonexistent_keys must be True, or else we would have
                # failed earlier from this. So add this one to our keys done
                # list and skip it
                patch_status.skip_key(key)
                continue
            orig_data = self._load_bosdata(key, raw_data)
            # Data filtering happens here rather than after due to paging/memory constraints;
            # we can't load all data and then filter on the results
            if patch_options.data_filter is not None and not patch_options.data_filter(orig_data):
                # This data does not match our filter, so skip it
                patch_status.skip_key(key)
                continue

            # This key should be patched

            # Start by making a copy of the data, so that we can compare
            # the final patched version to it, and see if it has been changed
            # (this is necessary because many BOS patching functions change the
            # data in place)
            new_data = copy.deepcopy(orig_data)

            # Apply the patch to the current data
            patch_options.apply_patch(key, new_data)

            if new_data == orig_data:
                # If this did not actually change the entry, then there is no need to
                # actually update the DB. We will just report to the caller that it was
                # patched.
                patch_status.patch_applied(key, new_data)
                continue

            pending_patched_data_map[key] = new_data
            pending_patched_raw_data_map[key] = json.dumps(new_data)

        if pending_patched_raw_data_map:
            # Begin our transaction
            # After this call to pipe.multi(), the database calls are NOT executed immediately.
            pipe.multi()

            # Queue the DB command to updated the specified keys with the patched data
            pipe.mset(pending_patched_raw_data_map)

            # Execute the pipeline
            #
            # At this point, if any entries still being watched have been changed since we
            # started watching them (including being created or deleted), then a Redis
            # WatchError exception will be raised and the mset command will not be executed.
            # The caller of this function will include logic that decides how to handle this.
            #
            # Instead, if none of those entries has changed, then Redis will atomically execute
            # all of the queued database commands. The return value of the pipe.execute()
            # call is a list with the return values for all of the queued DB commands. In this
            # case, that is just the mset call, and we do not care about its return value.
            # If the mset failed, it would raise an exception, and that's all we really care
            # about.
            pipe.execute()

        # If we get here, it means that either the pipe executed successfully, or (if we had no
        # keys to be patched in this batch) it was not executed at all. Either way, add the
        # patched keys (if any) to the done list, and update the patched data map.
        patch_status.patches_applied(pending_patched_data_map)

    def _bulk_patch_loop[PatchDataFormat](
        self, *,
        patch_options: BulkPatchOptions[DataT, PatchDataFormat] | BulkDictPatchOptions[DataT, PatchDataFormat],
        patch_status: BulkPatchStatus[DataT]
    ) -> list[DataT]:
        # Keep looping until either we have processed all of the keys in our keys_left list -- we
        # do not worry about keys that are created after this method starts running.
        #
        # The DB busy scenario is handled by an exception being raised, so it bypasses the
        # regular loop logic.
        while patch_status:
            # The main work in the loop is enclosed in this try/except block.
            # This is to catch Redis WatchErrors, which are raised when a change to the database
            # caused one of our patch operations to abort. Any other exceptions that arise are
            # not handled at this layer.
            try:
                # Process the keys in batches, rather than all at once.
                # See defs.py for details on DB_BATCH_SIZE.
                for key_batch in patch_status.key_batches:
                    # Call our helper function on this batch of keys
                    # At the time of this writing, pylint is not clever enough to understand
                    # the function signature mutation performed by the @redis_pipeline
                    # decorator, and so it falsely reports that we are missing an argument
                    # here.
                    # pylint: disable=no-value-for-parameter
                    self._bulk_patch(keys=key_batch,
                                     patch_options=patch_options,
                                     patch_status=patch_status)
                    # If we get here, it means the patches (if any) completed successfully.
                    # The helper function will have already:
                    # * updated keys_done with any keys that did not need to be patched
                    # * updated keys_done with any keys that were patched
                    # * updated patched_data_map with patches that were applied
            except redis.exceptions.WatchError as err:
                # This means one of the keys changed values between when we filtered it and when
                # we went to update the DB with the patched data.
                if patch_status.timed_out:
                    # We are past the last allowed retry time, so re-raise the exception
                    raise err

                # We are not past the time limit, so just log a warning and we'll go back to the
                # top of the loop.
                LOGGER.warning("Key changed (%s); retrying", err)

        # If we get here, it means we ended up processing all of the keys in our starting list.
        # So return a list of the patched data.
        # Sort the list by key, to preserve the previous behavior of this function.
        return patch_status.patched_data_list


    @convert_db_watch_errors
    def bulk_patch_by_dict[PatchDataFormat](
        self,
        key_patch_data_map: Mapping[str, PatchDataFormat],
        /, *,
        skip_nonexistent_keys: bool,
        patch_handler: PatchHandler[DataT, PatchDataFormat]
    ) -> list[DataT]:
        # keys_left starts being set to all of the keys in the patch data map
        keys_left: list[str] = list(key_patch_data_map)
        patch_status: BulkPatchStatus[DataT] = BulkPatchStatus.new_bulk_patch(
                                                keys_left,
                                                batch_size=len(keys_left)
                                               )

        opts: BulkDictPatchOptions[DataT,
                                   PatchDataFormat] = BulkDictPatchOptions(
                                                       key_patch_data_map=key_patch_data_map,
                                                       patch_handler=patch_handler,
                                                       skip_nonexistent_keys=skip_nonexistent_keys
                                                      )
                                         

        return self._bulk_patch_loop(patch_options=opts, patch_status=patch_status)


    @convert_db_watch_errors
    def bulk_patch_by_filter[PatchDataFormat](
        self,
        data_filter: EntryChecker[DataT],
        patch_data: PatchDataFormat,
        /, *,
        patch_handler: PatchHandler[DataT, PatchDataFormat],
        specific_keys: Iterable[str] | None = None
    ) -> list[DataT]:
        # keys_left starts being set to all of the keys in the database
        # (intersected with our list of specific keys, if set)
        # We will remove keys from it as we process them (either by patching
        # them or determining that they do not need to be patched).
        keys_left: list[str] = list(self.iter_keys(specific_keys=specific_keys))

        patch_status: BulkPatchStatus[DataT] = BulkPatchStatus.new_bulk_patch(keys_left)

        opts: BulkPatchOptions[DataT, PatchDataFormat] = BulkPatchOptions(
                                                          patch_data=patch_data,
                                                          patch_handler=patch_handler,
                                                          data_filter=data_filter
                                                         )

        return self._bulk_patch_loop(patch_options=opts, patch_status=patch_status)


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
