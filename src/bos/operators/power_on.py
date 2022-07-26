#!/usr/bin/env python
#
# MIT License
#
# (C) Copyright 2021-2022 Hewlett Packard Enterprise Development LP
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
from collections import defaultdict
import logging
from requests import HTTPError

from bos.common.values import Action, Status
import bos.operators.utils.clients.bss as bss
import bos.operators.utils.clients.capmc as capmc
from bos.operators.utils.clients.cfs import set_cfs
from bos.operators.base import BaseOperator, main
from bos.operators.filters import BOSQuery, HSMState
from bos.server.dbs.boot_artifacts import record_boot_artifacts

LOGGER = logging.getLogger('bos.operators.power_on')


class PowerOnOperator(BaseOperator):
    """
    The Power-On Operator tells capmc to power-on nodes if:
    - Enabled in the BOS database and the status is power_on_pending
    - Enabled in HSM
    """

    retry_attempt_field = "power_on_attempts"

    @property
    def name(self):
        return Action.power_on

    # Filters
    @property
    def filters(self):
        return [
            BOSQuery(enabled=True, status=Status.power_on_pending),
            HSMState(enabled=True)
        ]

    def _act(self, components):
        try:
            self._set_bss(components)
        except Exception as e:
            raise Exception("An error was encountered while setting BSS information: {}".format(e)) from e
        try:
            set_cfs(components, enabled=False, clear_state=True)
        except Exception as e:
            raise Exception("An error was encountered while setting CFS information: {}".format(e)) from e
        component_ids = [component['id'] for component in components]
        try:
            capmc.power(component_ids, state='on')
        except Exception as e:
            raise Exception("An error was encountered while calling CAPMC to power on: {}".format(e)) from e
        return components

    def _set_bss(self, components):
        """
        Set the boot artifacts (kernel, kernel parameters, and initrd) in BSS.
        Receive a BSS_REFERRAL_TOKEN from BSS.
        Map the token to the boot artifacts.
        Update each node's desired state with the token.
        """
        parameters = defaultdict(set)
        sessions = {}
        for component in components:
            # Handle the boot artifacts
            boot_artifacts = component.get('desired_state', {}).get('boot_artifacts', {})
            kernel = boot_artifacts.get('kernel')
            kernel_parameters = boot_artifacts.get('kernel_parameters')
            initrd = boot_artifacts.get('initrd')
            if not any([kernel, kernel_parameters, initrd]):
                continue
            key = (kernel, kernel_parameters, initrd)
            parameters[key].add(component['id'])
            # Handle the session
            sessions[component['id']] = component.get('session', "")
        bss_tokens = []
        for key, nodes in parameters.items():
            kernel, kernel_parameters, initrd = key
            try:
                resp = bss.set_bss(node_set=nodes, kernel_params=kernel_parameters,
                                   kernel=kernel, initrd=initrd)
                resp.raise_for_status()
            except HTTPError:
                LOGGER.error(f"Failed to set BSS for boot artifacts: {key} for"
                             "nodes: {nodes}. Error: {err}")
            else:
                token = resp.headers['bss-referral-token']
                record_boot_artifacts(token, kernel, kernel_parameters, initrd)

                for node in nodes:
                    bss_tokens.append({"id": node,
                                       "desired_state": {"bss_token": token},
                                       "session": sessions[node]})
        self.bos_client.components.update_components(bss_tokens)


if __name__ == '__main__':
    main(PowerOnOperator)
