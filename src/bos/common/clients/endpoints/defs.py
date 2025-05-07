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
from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager
from typing import NamedTuple, TypedDict

import requests

type RequestsMethod = Callable[..., AbstractContextManager[requests.Response]]


class RequestOptions(TypedDict, total=False):
    """
    Kwargs definition for BaseGenericEndpoint _request method
    These are passed into the requests module request methods.

    This is not intended to list all of the supported arguments for the requests
    module methods -- only the ones that BOS uses. And even for those, these
    definitions will only cover the ways in which BOS uses them.
    """
    params: Mapping[str,object]|None
    json: object
    headers: Mapping[str,object]|None
    verify: bool


class RequestData(NamedTuple):
    """
    This class encapsulates data about an API request.
    It is passed into the exception handler, so that it is able to
    include information about the request in its logic and error messages.
    """
    method_name: str
    url: str
    request_options: RequestOptions
