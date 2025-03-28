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

import json
from typing import Generator, cast

from bos.common.types.general import JsonData, JsonDict
from bos.common.utils import exc_type_msg

from .dbwrapper import DBWrapper
from .defs import Databases
from .exceptions import InvalidDBDataType, InvalidDBJsonDataType, NonJsonDBData, NotFoundInDB

class DictDBWrapper:
    """A higher-level wrapper around a Redis database connection
    """

    def __init__(self, db: Databases):
        self._dbwrapper = DBWrapper(db)

    @property
    def client(self) -> DBWrapper:
        return self._dbwrapper

    @property
    def db(self) -> Databases:
        return self.client.db

    @property
    def db_name(self) -> str:
        return self.client.db_name

    def info(self) -> str:
        return self.client.info()

    def __contains__(self, key: str) -> bool:
        return self.client.__contains__(key)

    @property
    def ready(self) -> bool:
        return self.client.ready

    def _load_dict(self, key: str, datastr: str) -> JsonDict:
        """
        Converts the DB entry into a JSON dict, or raises an appropriate exception
        """
        try:
            data = json.loads(datastr)
        except json.decoder.JSONDecodeError as exc:
            raise NonJsonDBData(self.db, key=key, entry_data=datastr,
                                exc=exc_type_msg(exc)) from exc
        # Because we just loaded the data using json.load, we know the format is JSON
        # The only thing we really need to make sure of is that it's a dict
        if isinstance(data, dict):
            # Cast the return type, so mypy has no doubts
            return cast(JsonDict, data)
        # Cast the entry data for poor mypy, since we know it is JsonData
        raise InvalidDBJsonDataType(db=self.db, key=key, entry_data=cast(JsonData, data))

    def delete(self, key: str) -> None:
        """
        Deletes data from the database. No need to give this method a name that is data-type
        specific, since we don't actually validate or return data. This will, however,
        raise an exception if the entry does not exist in the DB.
        """
        self.client.delete(key)

    # The following methods act like REST calls for single items
    def dict_get(self, key: str) -> JsonDict:
        """Get the data for the given key."""
        data = self.client.get(key)
        return self._load_dict(key, data)

    def dict_get_and_delete(self, key: str) -> JsonDict:
        """Get the data for the given key and delete it from the DB."""
        data = self.client.getdel(key)
        return self._load_dict(key, data)

    def dict_put(self, key: str, new_data: JsonDict) -> None:
        """Put data in to the database, replacing any old data."""
        datastr = json.dumps(new_data)
        self.client.set(key, datastr)

    def dict_get_all(self) -> list[JsonDict]:
        """Get an array of data for all keys."""
        return list(self.dict_iter_values())

    def dict_get_all_as_dict(self) -> dict[str, JsonDict]:
        """Return a mapping from all keys to their corresponding data
        """
        return dict(self.dict_iter_items())

    def dict_iter_values(self,
                         start_after_key: str | None = None) -> Generator[JsonDict, None, None]:
        """
        Iterate through every item in the database. Parse each item as JSON and yield it.
        If start_after_key is specified, skip any keys that are lexically <= the specified key.
        """
        for _, data in self.dict_iter_items(start_after_key=start_after_key):
            yield data

    def dict_iter_items(
        self, start_after_key: str | None = None
    ) -> Generator[tuple[str, JsonDict], None, None]:
        """
        Iterate through every item in the database. Parse each item as JSON and yield it.
        If start_after_key is specified, skip any keys that are lexically <= the specified key.
        """
        for key, datastr in self.client.iter_items(start_after_key=start_after_key):
            yield self._load_dict(key, datastr)
