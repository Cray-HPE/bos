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
import datetime
import re
import traceback
from dateutil.parser import parse
from functools import partial

from bos.common.base_requests_retry_session import requests_retry_session as base_requests_retry_session

PROTOCOL = 'http'
TIME_DURATION_PATTERN = re.compile("^(\d+?)(\D+?)$", re.M|re.S)

# Common date and timestamps functions so that timezones and formats are handled consistently.
def get_current_time() -> datetime.datetime:
    return datetime.datetime.now()


def get_current_timestamp() -> str:
    return get_current_time().now().isoformat(timespec='seconds')


def load_timestamp(timestamp: str) -> datetime.datetime:
    return parse(timestamp).replace(tzinfo=None)


def duration_to_timedelta(timestamp: str):
    """
    Converts a <digit><duration string> to a timedelta object.
    """
    # Calculate the corresponding multiplier for each time value
    seconds_table = {'s': 1,
                     'm': 60,
                     'h': 60*60,
                     'd': 60*60*24,
                     'w': 60*60*24*7}
    timeval, durationval = TIME_DURATION_PATTERN.search(timestamp).groups()
    timeval = float(timeval)
    seconds = timeval * seconds_table[durationval]
    return datetime.timedelta(seconds=seconds)


requests_retry_session = partial(base_requests_retry_session,
                                 retries=10, backoff_factor=0.5,
                                 status_forcelist=(500, 502, 503, 504),
                                 connect_timeout=3, read_timeout=30,
                                 session=None, protocol=PROTOCOL)


def compact_response_text(response_text: str) -> str:
    """
    Often JSON is "pretty printed" in response text, which is undesirable for our logging.
    This function transforms the response text into a single line, stripping leading and trailing whitespace from each line,
    and then returns it.
    """
    if response_text:
        return ' '.join([ line.strip() for line in response_text.split('\n') ])
    return str(response_text)


def exc_type_msg(exc: Exception) -> str:
    """
    Given an exception, returns a string of its type and its text (e.g. TypeError: 'int' object is not subscriptable)
    """
    return ''.join(traceback.format_exception_only(type(exc), exc))
