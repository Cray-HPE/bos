#
# MIT License
#
# (C) Copyright 2019-2024 Hewlett Packard Enterprise Development LP
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
import json

from requests.exceptions import HTTPError

from bos.common.utils import compact_response_text, exc_type_msg, requests_retry_session, PROTOCOL
from bos.operators.utils.clients.bos.options import options

LOGGER = logging.getLogger(__name__)
SERVICE_NAME = 'cray-bss'
ENDPOINT = f"{PROTOCOL}://{SERVICE_NAME}/boot/v1"


def set_bss(node_set, kernel_params, kernel, initrd, session=None):
    '''
    Tell the Boot Script Service (BSS) which boot artifacts are associated
    with each node.

    Currently, this is biased towards 'hosts' (i.e. xnames) rather than
    NIDS.

    Args:
        node_set (set): A list of nodes to assign the boot artifacts to
        kernel_params (string): Kernel parameters to assign to the node
        kernel (string): The kernel to assign to the node
        initrd (string): The initrd to assign to the node
        session (requests Session instance): An existing session to use

    Returns:
        The response from BSS.

    Raises:
        KeyError -- If the boot_artifacts does not find either the initrd
                    or kernel keys, this error is raised.
        ValueError -- if the kernel_parameters contains an 'initrd'
        requests.exceptions.HTTPError -- An HTTP error encountered while
                                         communicating with the
                                         Hardware State Manager
    '''
    if not node_set:
        # Cannot simply return if no nodes are specified, as this function
        # is intended to return the response object from BSS.
        # Accordingly, an Exception is raised.
        raise Exception("set_bss called with empty node_set")

    session = session or requests_retry_session(read_timeout=options.bss_read_timeout)  # pylint: disable=redundant-keyword-arg
    LOGGER.info("Params: %s", kernel_params)
    url = f"{ENDPOINT}/bootparameters"

    # Assignment payload
    payload = {"hosts": list(node_set),
               "params": kernel_params,
               "kernel": kernel,
               "initrd": initrd}

    LOGGER.debug("PUT %s for hosts %s", url, node_set)
    try:
        resp = session.put(url, data=json.dumps(payload), verify=False)
        LOGGER.debug("Response status code=%d, reason=%s, body=%s", resp.status_code,
                     resp.reason, compact_response_text(resp.text))
        resp.raise_for_status()
        return resp
    except HTTPError as err:
        LOGGER.error(exc_type_msg(err))
        raise
