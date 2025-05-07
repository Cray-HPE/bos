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
DB-related exceptions
"""

from bos.common.types.general import JsonData

from .defs import Databases

class BosDBException(Exception):
    """
    Parent class for any exceptions originating from BOS DB classes
    """
    DEFAULT_MSG = "Database error"

    def __init__(self, db: Databases, **kwargs: str|None) -> None:
        kwargs['db'] = db.name
        if not kwargs.get('msg'):
            kwargs['msg'] = self.DEFAULT_MSG
        self.err_info: dict[str, str] = { k: v for k, v in kwargs.items() if v is not None }
        super().__init__(self.__str__())

    def __str__(self) -> str:
        err_info_list = [
            f"{k}={v}" for k, v in self.err_info.items() if k != "msg"
        ]
        msg = self.err_info.get("msg")
        if msg is not None:
            err_info_list.append(msg)
        return " ".join(err_info_list)


class BosDBEntryException(BosDBException):
    """
    Parent class for exceptions related to specific DB entries
    """
    DEFAULT_MSG = "Database entry error"

    def __init__(self, db: Databases, key: str, **kwargs: str|None) -> None:
        super().__init__(db=db, key=key, **kwargs)

    @property
    def key(self) -> str:
        return self.err_info["key"]

class NotFoundInDB(BosDBEntryException):
    """
    Raised when a requested entry is not there
    """
    DEFAULT_MSG = "Key not found in database"

    def __init__(self, db: Databases, key: str, **kwargs: str|None) -> None:
        super().__init__(db=db, key=key, **kwargs)

class InvalidDBData(BosDBEntryException):
    """
    Parent class for invalid DB data errors
    """
    DEFAULT_MSG = "Invalid data in database entry"

    def __init__(self, db: Databases, key: str, entry_data: object, **kwargs: str|None) -> None:
        super().__init__(db=db, entry_data=str(entry_data), key=key, **kwargs)

class InvalidDBDataType(InvalidDBData):
    """
    Raised when a DB lookup retrieves an item that is not JSON-deserializable
    (not a string-like object)
    """
    DEFAULT_MSG = "Invalid data type in database entry"

    def __init__(self, db: Databases, entry_data: object, key: str, **kwargs: str|None) -> None:
        super().__init__(db=db, entry_data=entry_data, key=key,
                         expected_type="byte | bytearray | str",
                         actual_type=type(entry_data).__name__, **kwargs)

class InvalidDBJsonDataType(InvalidDBData):
    """
    Raised when a DB lookup retrieves an item that decodes to JSON of the wrong type.
    In BOS DB, we always expect the entries to be dicts.
    """
    DEFAULT_MSG = "Invalid JSON data type in database entry"

    def __init__(self, db: Databases, entry_data: JsonData, key: str, **kwargs: str|None) -> None:
        super().__init__(db=db, entry_data=entry_data, key=key, expected_type="dict",
                         actual_type=type(entry_data).__name__, **kwargs)

class NonJsonDBData(InvalidDBData):
    """
    Raised when JSON decode fails
    """
    DEFAULT_MSG = "Invalid JSON in database entry"

    def __init__(self, db: Databases, entry_data: bytes | bytearray | str, key: str,
                 **kwargs: str|None) -> None:
        super().__init__(db=db, key=key, entry_data=entry_data, **kwargs)
