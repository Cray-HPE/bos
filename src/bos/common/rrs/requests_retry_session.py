#
# MIT License
#
# (C) Copyright 2022-2024 Hewlett Packard Enterprise Development LP
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
Return a requests session with retries, timeouts, and logging.

The purpose of this module is to provide a unified way of creating or
updating a requests retry connection whenever interacting with a
microservice; these connections are exposed as a requests session
with an HTTP retry adapter attached to it.
Created on Nov 2, 2020

@author: jsl
"""

import requests
# Because we want to support Python 3.6 and 3.9, use old-style type hint syntax
from typing import Tuple, Union

from .timeout_http_adapter import TimeoutHTTPAdapter
from .retry_with_logs import RetryWithLogs

PROTOCOL = 'http'

def requests_retry_session(retries: int = 10,
                           backoff_factor: float = 0.5,
                           status_forcelist: Tuple[int, ...] = (500, 502, 503, 504),
                           connect_timeout: int = 3,
                           read_timeout: int = 10,
                           session: Union[None, requests.Session] = None,
                           protocol: str = PROTOCOL) -> requests.Session:
    session = session or requests.Session()
    retry = RetryWithLogs(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = TimeoutHTTPAdapter(max_retries=retry, timeout=(connect_timeout, read_timeout))
    # Must mount to http://
    # Mounting to only http will not work!
    session.mount(f"{protocol}://", adapter)
    return session
