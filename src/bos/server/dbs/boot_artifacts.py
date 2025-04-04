#
# MIT License
#
# (C) Copyright 2022, 2024-2025 Hewlett Packard Enterprise Development LP
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
import logging

from bos.common.types.components import TimestampedBootArtifacts
from bos.common.utils import get_current_timestamp
from bos.server.redis_db_utils import BootArtifactsDBWrapper, NotFoundInDB

LOGGER = logging.getLogger(__name__)
TOKENS_DB = BootArtifactsDBWrapper()


class BssTokenException(Exception):
    pass


class BssTokenUnknown(BssTokenException):
    """
    The BSS Token is not present in the database.
    """


def record_boot_artifacts(token: str, kernel: str, kernel_parameters: str,
                          initrd: str) -> None:
    """
    Associate the BSS token with the boot artifacts.
    BSS returns a token after BOS asks it to create or update the boot artifacts.
    """
    LOGGER.info(
        "Logging BSS token and boot artifacts: token='%s' kernel='%s' "
        "kernel_parameters='%s' initrd='%s'", token, kernel, kernel_parameters,
        initrd)
    TOKENS_DB.put(
        token, {
            "kernel": kernel,
            "kernel_parameters": kernel_parameters,
            "initrd": initrd,
            "timestamp": get_current_timestamp()
        })


def get_boot_artifacts(token: str) -> TimestampedBootArtifacts:
    """
    Get the boot artifacts associated with a BSS token.

    Returns:
      Boot artifacts (dict)

    Raises:
      BssTokenUnknown
    """
    try:
        return TOKENS_DB.get(token)
    except NotFoundInDB as exc:
        raise BssTokenUnknown from exc
