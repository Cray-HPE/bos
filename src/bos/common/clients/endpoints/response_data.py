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
import json
from typing import NamedTuple, Self

import requests

from .defs import JsonData, JsonDict


class ResponseData(NamedTuple):
    """
    Encapsulates data from a response to an API request. This allows the
    response itself to be cleaned up when its context manager exits.
    """
    headers: JsonDict
    ok: bool
    reason: str
    status_code: int
    text: bytes | None

    @property
    def body(self) -> JsonData:
        return json.loads(self.text) if self.text else None

    @classmethod
    def from_response(cls, resp: requests.Response) -> Self:
        return cls(headers=resp.headers,
                   ok=resp.ok,
                   reason=resp.reason,
                   status_code=resp.status_code,
                   text=resp.text)
