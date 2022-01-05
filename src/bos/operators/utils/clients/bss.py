# Copyright 2019-2021 Hewlett Packard Enterprise Development LP
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
from requests.exceptions import HTTPError
import logging
import json

from bos.operators.utils import requests_retry_session, PROTOCOL

LOGGER = logging.getLogger(__name__)
SERVICE_NAME = 'cray-bss'
ENDPOINT = "%s://%s/boot/v1" % (PROTOCOL, SERVICE_NAME)


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
        Nothing

    Raises:
        KeyError -- If the boot_artifacts does not find either the initrd
                    or kernel keys, this error is raised.
        ValueError -- if the kernel_parameters contains an 'initrd'
        requests.exceptions.HTTPError -- An HTTP error encountered while
                                         communicating with the
                                         Hardware State Manager
    '''
    session = session or requests_retry_session()
    LOGGER.info("Params: {}".format(kernel_params))
    url = "%s/bootparameters" % (ENDPOINT)

    if not node_set:
        return

    # Assignment payload
    payload = {"hosts": list(node_set),
               "params": kernel_params,
               "kernel": kernel,
               "initrd": initrd}

    try:
        resp = session.put(url, data=json.dumps(payload), verify=False)
        resp.raise_for_status()
    except HTTPError as err:
        LOGGER.error("%s" % err)
        raise
