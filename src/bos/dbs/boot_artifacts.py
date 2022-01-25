# Copyright 2022 Hewlett Packard Enterprise Development LP
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
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# (MIT License)

from datetime import datetime
import logging
from requests import HTTPError

from server.bos import redis_db_utils as dbutils

LOGGER = logging.getLogger('bos.dbs.boot_artifacts')
TOKENS_DB = dbutils.get_wrapper(db='bss_tokens_boot_artifacts')


def record_boot_artifacts(token, kernel, kernel_parameters, initrd):
    """
    Associate the BSS token with the boot artifacts.
    BSS returns a token after BOS asks it to create or update the boot artifacts.
    
    Raises:
      HTTPError, if one occurs 
    """
    LOGGER.info(f"Logging BSS token: {token} and boot artifacts: "
                f"kernel: {kernel}"
                f"kernel_parameters: {kernel_parameters}"
                f"initrd: {initrd}")
    resp = TOKENS_DB.put(token, {"kernel": kernel,
                                 "kernel_parameters": kernel_parameters,
                                 "initrd": initrd,
                                 "timestamp": datetime.utcnow().isoformat()
                                 })
    try:
        resp.raise_for_status()
    except HTTPError as err:
        LOGGER.error(f"Database write to capture BSS token '{token}' failed: {err}")
        raise


def get_boot_artifacts(token):
    """
    Get the boot artifacts associated with a BSS token.
    
    Returns:
      Boot artifacts (dict)
    """
    return TOKENS_DB.get(token)
