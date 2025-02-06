#
# MIT License
#
# (C) Copyright 2024-2025 Hewlett Packard Enterprise Development LP
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

import json
import logging
from typing import Any

import jsonschema

LOGGER = logging.getLogger(__name__)

API_JSON_SCHEMA_PATH = "/app/lib/bos/server/openapi.jsonschema"


class Validator:

    def __init__(self):
        LOGGER.info("Loading API schema from %s", API_JSON_SCHEMA_PATH)
        with open(API_JSON_SCHEMA_PATH, "rt") as f:
            oas = json.load(f)
        self.api_schema = oas["components"]["schemas"]

    def validate(self, data: Any, schema_name: str):
        jsonschema.validate(data, self.api_schema[schema_name])

    def validate_component(self, data: Any) -> None:
        self.validate(data, "V2ComponentWithId")

    def validate_extended_session_status(self, data: Any) -> None:
        self.validate(data, "V2SessionExtendedStatus")

    def validate_options(self, data: Any) -> None:
        self.validate(data, "V2Options")

    def validate_session(self, data: Any) -> None:
        self.validate(data, "V2Session")

    def validate_session_template(self, data: Any) -> None:
        self.validate(data, "V2SessionTemplate")

    def get_schema_fields(self, schema_name: str) -> set[str]:
        return set(self.api_schema[schema_name]["properties"])

    @property
    def session_template_fields(self) -> set[str]:
        return self.get_schema_fields("V2SessionTemplate")

    @property
    def boot_set_fields(self) -> set[str]:
        return self.get_schema_fields("V2BootSet")

    @property
    def cfs_fields(self) -> set[str]:
        return self.get_schema_fields("V2CfsParameters")


validator = Validator()
