#
# MIT License
#
# (C) Copyright 2025 Hewlett Packard Enterprise Development LP
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
ComponentDBWrapper class
"""
from typing import cast

from bos.common.types.components import ComponentRecord
from bos.common.types.general import JsonDict

from .dbwrapper import DBWrapper
from .defs import Databases

class ComponentDBWrapper(DBWrapper[ComponentRecord]):
    """
    Components database wrapper
    """

    _Database = Databases.COMPONENTS

    def _jsondict_to_bosdata(self, key: str, jsondict: JsonDict, /) -> ComponentRecord:
        """
        Eventually this should probably actually make sure that the record being returned is in the
        correct format. But for now, we'll just satisfy mypy
        """
        return cast(ComponentRecord, jsondict)
