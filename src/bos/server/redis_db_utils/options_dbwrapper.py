#
# MIT License
#
# (C) Copyright 2025-2026 Hewlett Packard Enterprise Development LP
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
import logging
import re
from typing import cast

from bos.common.types.general import JsonDict
from bos.common.types.options import OptionsDict

from .dbwrapper import DBWrapper
from .defs import Databases

LOGGER = logging.getLogger(__name__)

# We store all options as json under this key so that the data format is
# similar to other data stored in the database, and to make retrieval of all
# options simpler
OPTIONS_KEY = 'options'

# CASMCMS-9618 changed the legal values for the component_actual_state_ttl option
# Specifically, it no longer allows values less than 1 hour. All valid values
# will be in the form of the following regex
_ACTUAL_STATE_TTL_PATTERN = r'^[1-9][0-9]*[hHdDwW]$'
_ACTUAL_STATE_TTL_RE = re.compile(_ACTUAL_STATE_TTL_PATTERN)

class OptionsDBWrapper(DBWrapper[OptionsDict]):
    """
    Options database wrapper
    """

    _Database = Databases.OPTIONS

    @property
    def options_exist(self) -> bool:
        return OPTIONS_KEY in self

    def get_options(self) -> OptionsDict:
        """
        This retrieves the current option values from the database. Except for one thing:

        See the comment above the _ACTUAL_STATE_TTL_PATTERN definition.

        The change in legal values for the component_actual_state_ttl option does
        not cover the case where the value had previously been set to a now-illegal
        value.

        This function checks to see if that option is present and set to an illegal value.
        If so, it deletes the option before returning the options dictionary. That will cause
        higher levels to use a default value for it.
        """
        options_dict = self.get(OPTIONS_KEY)
        if "component_actual_state_ttl" not in options_dict:
            # The component_actual_state_ttl option is not set in the DB, so no need
            # to validate it
            return options_dict
        if _ACTUAL_STATE_TTL_RE.match(options_dict["component_actual_state_ttl"]) is not None:
            # The component_actual_state_ttl option is set to a valid value in the DB, so no need
            # to remove it
            return options_dict
        # The component_actual_state_ttl option is set to an invalid value in the DB. Remove it
        # before returning the options dictionary.
        invalid_value = options_dict.pop("component_actual_state_ttl")
        LOGGER.info("Options database has now-illegal value for component_actual_state_ttl (%s); "
                    "clearing it so default value can be used instead", invalid_value)
        return options_dict

    def put_options(self, data: OptionsDict) -> None:
        self.put(OPTIONS_KEY, data)

    def _jsondict_to_bosdata(self, key: str, jsondict: JsonDict, /) -> OptionsDict:
        """
        Eventually this should probably actually make sure that the record being returned is in the
        correct format. But for now, we'll just satisfy mypy
        """
        return cast(OptionsDict, jsondict)
