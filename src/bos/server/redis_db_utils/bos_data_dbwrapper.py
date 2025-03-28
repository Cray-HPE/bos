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
import logging
from typing import Protocol
from typing_extensions import ClassVar

from bos.common.types.general import BosDataRecord, JsonDict

from .defs import Databases
from .dict_dbwrapper import DictDBWrapper

LOGGER = logging.getLogger(__name__)

class SpecificDatabase(Protocol):
    """ Require that some classes set the _Database class variable """
    _Database: ClassVar[Databases]

class BosDataDBWrapper[DataType: BosDataRecord](DictDBWrapper, SpecificDatabase, ABC):
    """A wrapper around a Redis database connection

    This handles creating the Redis client and provides REST-like methods for
    modifying json data in the database.

    Because the underlying Redis client is threadsafe, this class is as well,
    and can be safely shared by multiple threads.
    """

    def __init__(self) -> None:
        super().__init__(db=self._Database)

    @classmethod
    @abstractmethod
    def _load_bosdata(cls, data: JsonDict) -> DataType: ...

    # The following methods act like REST calls for single items
    def get(self, key: str) -> DataType:
        """Get the data for the given key."""
        return self._load_bosdata(self.dict_get(key))

    def get_and_delete(self, key: str) -> DataType:
        """Get the data for the given key and delete it from the DB."""
        return self._load_bosdata(self.dict_get_and_delete(key))

    def put(self, key: str, new_data: DataType) -> None:
        """Put data in to the database, replacing any old data."""
        self.dict_put(key, new_data)

    def get_all(self) -> list[DataType]:
        """Get an array of data for all keys."""
        return [ self._load_bosdata(json_dict) for json_dict in self.dict_get_all() ]

    def get_all_filtered(self,
                         filter_func: Callable[[DataType], DataType | None],
                         start_after_key: str | None = None,
                         page_size: int = 0) -> list[DataType]:
        """
        Get an array of data for all keys after passing them through the specified filter
        (discarding any for which the filter returns None)
        If start_after_id is specified, all ids lexically <= that id will be skipped.
        If page_size is specified, the number of items in the returned list will be equal
        to or less than the page_size.
        More elements may remain and additional queries will be needed to acquire them.
        """
        data = []
        all_entries = map(self._load_bosdata, self.dict_iter_values(start_after_key))
        for filtered_value in map(filter_func, all_entries):
            if filtered_value is None:
                continue
            data.append(filtered_value)
            if page_size and len(data) == page_size:
                break
        return data

    def get_all_as_dict(self) -> dict[str, DataType]:
        """Return a mapping from all keys to their corresponding data
           Based on https://github.com/redis/redis-py/issues/984#issuecomment-391404875
        """
        return { key: self._load_bosdata(value) for key, value in self.dict_iter_items() }
