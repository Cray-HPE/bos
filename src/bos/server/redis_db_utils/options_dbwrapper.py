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
OptionsDBWrapper class
"""

from bos.common.types.options import OptionsDict

from .dbwrapper import DBWrapper
from .defs import Databases

# We store all options as json under this key so that the data format is
# similar to other data stored in the database, and to make retrieval of all
# options simpler
OPTIONS_KEY = 'options'

class OptionsDBWrapper(DBWrapper[OptionsDict]):
    """
    Options database wrapper
    """

    @property
    def db_id(self) -> Databases:
        return Databases.OPTIONS

    @property
    def options_exist(self) -> bool:
        return OPTIONS_KEY in self

    def get_options(self) -> OptionsDict | None:
        return self.get(OPTIONS_KEY)

    def put_options(self, data: OptionsDict) -> OptionsDict | None:
        return self.put(OPTIONS_KEY, data)

    def patch_options(self, data: OptionsDict) -> OptionsDict | None:
        return self._patch(OPTIONS_KEY, data)
