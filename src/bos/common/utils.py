#
# MIT License
#
# (C) Copyright 2022-2025 Hewlett Packard Enterprise Development LP
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

# Standard imports
import datetime
from functools import partial
import re
import traceback
from typing import List, Optional

# Third party imports
from dateutil.parser import parse
from requests_retry_session import requests_retry_session as base_requests_retry_session

PROTOCOL = 'http'
TIME_DURATION_PATTERN = re.compile(r"^(\d+?)(\D+?)$", re.M|re.S)

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
                                 connect_timeout=3, read_timeout=10,
                                 session=None, protocol=PROTOCOL)


class compact_response_text:
    """
    Often JSON is "pretty printed" in response text, which is undesirable for our logging.
    This callable class transforms the response text into a single line, stripping leading and
    trailing whitespace from each line, and then returns it. It uses iterators for this,
    to limit memory use when handling large responses. It is implemented as a class because
    this is used with logging, and by implementing the logic in the __str__ method, this
    prevents it from being run at all when the logging level would not require it.
    """
    _SPLIT_PAT = re.compile(r'([^\n]+)(?:$|\n)')

    def __init__(self, response_text: Optional[str]) -> None:
        self._response_text = response_text

    @property
    def response_text(self) -> str:
        return self._response_text if self._response_text is not None else "None"

    @classmethod
    def _match_group_one(cls, match_object: re.Match) -> str:
        """
        Helper function for map iterator inside compact_response_text.
        This gets the first match group, strips the leading and trailing whitespace,
        and returns it
        """
        return match_object.group(1).strip()

    def __str__(self) -> str:
        """
        finditer returns an iterator of match objects -- returning each instance matching
        the _SPLIT_PAT pattern.
        Creating a map of the _match_group_one method onto this iterator
        acts like an iterable version of the string split() method, called with \n as its
        argument. The one difference is that the _match_group_one method also does a strip()
        on the result.
        Any non-empty lines that come out of the above pipeline are joined by whitespace
        and returned.
        """
        return ' '.join(
            line for line in map(self._match_group_one,
                                 self._SPLIT_PAT.finditer(self.response_text)) if line
        )


def exc_type_msg(exc: Exception) -> str:
    """
    Given an exception, returns a string of its type and its text
    (e.g. TypeError: 'int' object is not subscriptable)
    """
    return ''.join(traceback.format_exception_only(type(exc), exc))

def using_sbps(component: str) -> bool:
    """
    If the component is using the Scalable Boot Provisioning Service (SBPS) to
    provide the root filesystem, then return True.
    Otherwise, return False.

    The kernel parameters will contain the string root=sbps-s3 if it is using
    SBPS.

    Return True if it is and False if it is not.
    """
    # Get the kernel boot parameters
    boot_artifacts = component.get('desired_state', {}).get('boot_artifacts', {})
    kernel_parameters = boot_artifacts.get('kernel_parameters')
    return using_sbps_check_kernel_parameters(kernel_parameters)

def using_sbps_check_kernel_parameters(kernel_parameters: str) -> bool:
    """
    Check the kernel boot parameters to see if the image is using the
    rootfs provider 'sbps'.
    SBPS is the Scalable Boot Provisioning Service (SBPS).
    The kernel parameters will contain the string root=sbps-s3 if it is using
    SBPS.

    Return True if it is and False if it is not.
    """
    # Check for the 'root=sbps-s3' string.
    return "root=sbps-s3" in kernel_parameters

def components_by_id(components: List[dict]) -> dict:
    """
    Input:
    * components: a list containing individual components
    Return:
    A dictionary with the name of each component as the
    key and the value being the entire component itself.

    Purpose: It makes searching more efficient because you can
    index by component name.
    """
    return { component["id"]: component for component in components }

def reverse_components_by_id(components_by_id_map: dict) -> List[dict]:
    """
    Input:
    components_by_id_map: a dictionary with the name of each component as the
    key and the value being the entire component itself.
    Return:
    A list with each component as an element

    Purpose: Reverse the effect of components_by_id.
    """
    return list(components_by_id_map.values())
