#
# MIT License
#
# (C) Copyright 2023 Hewlett Packard Enterprise Development LP
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
from dateutil.parser import parse
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

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


def requests_retry_session(retries=10, backoff_factor=0.5,
                           status_forcelist=(500, 502, 503, 504),
                           session=None, protocol=PROTOCOL):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    # Must mount to http://
    # Mounting to only http will not work!
    session.mount("%s://" % protocol, adapter)
    return session
