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
from contextlib import nullcontext, AbstractContextManager
import copy
import datetime
from functools import partial
import logging
import re
import traceback
from typing import Unpack

# Third party imports
from dateutil.parser import parse
import requests
import requests_retry_session as rrs

from bos.common.types.components import ComponentRecord

LOGGER = logging.getLogger(__name__)

PROTOCOL = 'http'
TIME_DURATION_PATTERN = re.compile(r"^(\d+?)(\D+?)$", re.M | re.S)


class InvalidDurationTimestamp(Exception):
    """
    Raised by duration_to_timedelta if it is asked to parse a timestamp
    that does not fit its expected pattern
    """


def update_log_level(new_level_str: str) -> None:
    """
    If the current logging level does not match the specified new level,
    then call do_update_log_level to update it
    """
    new_level_str = new_level_str.upper()
    new_level_int = logging.getLevelName(new_level_str)
    current_level_int = LOGGER.getEffectiveLevel()
    if current_level_int != new_level_int:
        do_update_log_level(current_level_int, new_level_int, new_level_str)


def do_update_log_level(current_level_int: int, new_level_int: int, new_level_str: str) -> None:
    """
    Change the logging level of the current process to the specified new level
    """
    current_level_str = logging.getLevelName(current_level_int)
    LOGGER.log(current_level_int, 'Changing logging level from %s to %s',
               current_level_str, new_level_str)
    logging.getLogger().setLevel(new_level_int)
    LOGGER.log(new_level_int, 'Logging level changed from %s to %s',
               current_level_str, new_level_str)


# Common date and timestamps functions so that timezones and formats are handled consistently.
def get_current_time() -> datetime.datetime:
    return datetime.datetime.now()


def get_current_timestamp() -> str:
    return get_current_time().now().isoformat(timespec='seconds')


def load_timestamp(timestamp: str) -> datetime.datetime:
    return parse(timestamp).replace(tzinfo=None)


def duration_to_timedelta(timestamp: str) -> datetime.timedelta:
    """
    Converts a <digit><duration string> to a timedelta object.
    """
    # Calculate the corresponding multiplier for each time value
    seconds_table = {
        's': 1,
        'm': 60,
        'h': 60 * 60,
        'd': 60 * 60 * 24,
        'w': 60 * 60 * 24 * 7
    }
    match = TIME_DURATION_PATTERN.search(timestamp)
    if match is None:
        raise InvalidDurationTimestamp(
                f"Timestamp string does not match expected format: '{timestamp}'")
    timeval, durationval = match.groups()
    timeval = float(timeval)
    seconds = timeval * seconds_table[durationval]
    return datetime.timedelta(seconds=seconds)


DEFAULT_RETRY_ADAPTER_ARGS = rrs.RequestsRetryAdapterArgs(
    retries=10,
    backoff_factor=0.5,
    status_forcelist=(500, 502, 503, 504),
    connect_timeout=3,
    read_timeout=10)

retry_session_manager = partial(rrs.retry_session_manager,
                                protocol=PROTOCOL,
                                **DEFAULT_RETRY_ADAPTER_ARGS)


class RetrySessionManager(rrs.RetrySessionManager):
    """
    Just sets the default values we use for our requests sessions
    """

    def __init__(self,
                 protocol: str = PROTOCOL,
                 **adapter_kwargs: Unpack[rrs.RequestsRetryAdapterArgs]):
        _adapter_kwargs = copy.deepcopy(DEFAULT_RETRY_ADAPTER_ARGS)
        _adapter_kwargs.update(adapter_kwargs)
        super().__init__(protocol=protocol, **_adapter_kwargs)


def retry_session(
    session: requests.Session | None = None,
    protocol: str | None = None,
    adapter_kwargs: rrs.RequestsRetryAdapterArgs | None = None
) -> AbstractContextManager[requests.Session]:
    if session is not None:
        return nullcontext(session)
    kwargs = adapter_kwargs or {}
    if protocol is not None:
        return retry_session_manager(protocol=protocol, **kwargs)  # pylint: disable=redundant-keyword-arg
    return retry_session_manager(**kwargs)


def retry_session_get(
    url: str,
    session: requests.Session | None = None
) -> AbstractContextManager[requests.Response]:
    with retry_session(session=session) as _session:
        return _session.get(url)


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

    def __init__(self, response_text: str | None) -> None:
        self._response_text = response_text

    @property
    def response_text(self) -> str:
        return self._response_text if self._response_text is not None else "None"

    @classmethod
    def _match_group_one(cls, match_object: re.Match[str]) -> str:
        """
        Helper function for map iterator inside compact_response_text.
        This gets the first match group, strips the leading and trailing whitespace,
        and returns it
        """
        # There are evidently some weird edge cases regarding the return type of Match.group
        # https://github.com/python/typeshed/issues/12090
        # Thus, if we don't get back a string, we just return an empty string
        g1 = match_object.group(1)
        if isinstance(g1, str):
            return g1.strip()
        return ""

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


def using_sbps(component: ComponentRecord) -> bool:
    """
    If the component is using the Scalable Boot Provisioning Service (SBPS) to
    provide the root filesystem, then return True.
    Otherwise, return False.

    The kernel parameters will contain the string root=sbps-s3 if it is using
    SBPS.

    Return True if it is and False if it is not.
    """
    # Get the kernel boot parameters
    boot_artifacts = component.get('desired_state',
                                   {}).get('boot_artifacts', {})
    kernel_parameters = boot_artifacts.get('kernel_parameters', "")
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


def components_by_id(components: list[ComponentRecord]) -> dict[str, ComponentRecord]:
    """
    Input:
    * components: a list containing individual components
    Return:
    A dictionary with the name of each component as the
    key and the value being the entire component itself.

    Purpose: It makes searching more efficient because you can
    index by component name.
    """
    return {component["id"]: component for component in components}


def reverse_components_by_id(
    components_by_id_map: dict[str, ComponentRecord]
) -> list[ComponentRecord]:
    """
    Input:
    components_by_id_map: a dictionary with the name of each component as the
    key and the value being the entire component itself.
    Return:
    A list with each component as an element

    Purpose: Reverse the effect of components_by_id.
    """
    return list(components_by_id_map.values())
