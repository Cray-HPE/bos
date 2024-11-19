#
# MIT License
#
# (C) Copyright 2019, 2021-2022, 2024 Hewlett Packard Enterprise Development LP
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
import re

import connexion

from bos.common.utils import ParsingException

LOGGER = logging.getLogger('bos.server.utils')


def canonize_xname(xname):
    """Ensure the xname is canonical.
    * Its components should be lowercase.
    * Any leading zeros should be stripped off.

    :param xname: xname to canonize
    :type xname: string

    :return: canonized xname
    :rtype: string
    """
    return re.sub(r'x0*(\d+)c0*(\d+)s0*(\d+)b0*(\d+)n0*(\d+)', r'x\1c\2s\3b\4n\5', xname.lower())


def get_request_json(log_data = True):
    """
    Used by endpoints which are expecting a JSON payload in the request body.
    Returns the JSON payload.
    Raises an Exception otherwise
    """
    if not connexion.request.is_json:
        raise ParsingException("Non-JSON request received")
    json_data = connexion.request.get_json()
    if log_data:
        LOGGER.debug("type=%s content=%s", type(json_data).__name__, json_data)
    return json_data
