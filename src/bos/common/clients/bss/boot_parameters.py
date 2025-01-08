#
# MIT License
#
# (C) Copyright 2021-2025 Hewlett Packard Enterprise Development LP
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

from .base import BaseBssEndpoint

LOGGER = logging.getLogger(__name__)


class BootParametersEndpoint(BaseBssEndpoint):

    @property
    def ENDPOINT(self) -> str:
        return 'bootparameters'

    def set_bss(self, node_set, kernel_params, kernel, initrd) -> str:
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
            The 'bss-referral-token' value from the header of the response from BSS.

        Raises:
            KeyError -- 'bss-referral-token' not found in header
            requests.exceptions.HTTPError -- An HTTP error encountered while
                                             communicating with the
                                             Hardware State Manager
            Exception -- called with empty node_set
        '''
        if not node_set:
            # Cannot simply return if no nodes are specified, as this function
            # is intended to return the response object from BSS.
            # Accordingly, an Exception is raised.
            raise Exception("set_bss called with empty node_set")

        LOGGER.info("Params: %s", kernel_params)

        # Assignment payload
        payload = {
            "hosts": list(node_set),
            "params": kernel_params,
            "kernel": kernel,
            "initrd": initrd
        }

        return self.put(json=payload,
                        verify=False).headers['bss-referral-token']
