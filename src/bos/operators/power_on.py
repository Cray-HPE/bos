#!/usr/bin/env python
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
from collections import defaultdict
import logging
from requests import HTTPError

from bos.common.utils import exc_type_msg
from bos.common.values import Action, Status
import bos.operators.utils.clients.bss as bss
import bos.operators.utils.clients.pcs as pcs
from bos.operators.utils.clients.cfs import set_cfs
from bos.operators.base import BaseOperator, main
from bos.operators.filters import BOSQuery, HSMState
from bos.server.dbs.boot_artifacts import record_boot_artifacts

LOGGER = logging.getLogger('bos.operators.power_on')


class PowerOnOperator(BaseOperator):
    """
    The Power-On Operator tells pcs to power-on nodes if:
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
            HSMState()
        ]

    def _act(self, components):
        if not components:
            return components
        self._preset_last_action(components)
        try:
            self._set_bss(components)
        except Exception as e:
            raise Exception("An error was encountered while setting BSS information: {}".format(exc_type_msg(e))) from e
        try:
            set_cfs(components, enabled=False, clear_state=True)
        except Exception as e:
            raise Exception("An error was encountered while setting CFS information: {}".format(exc_type_msg(e))) from e
        component_ids = [component['id'] for component in components]
        try:
            pcs.power_on(component_ids)
        except Exception as e:
            raise Exception("An error was encountered while calling CAPMC to power on: {}".format(exc_type_msg(e))) from e
        return components

    def _set_bss(self, components, retries=5):
        """
        Set the boot artifacts (kernel, kernel parameters, and initrd) in BSS.
        Receive a BSS_REFERRAL_TOKEN from BSS.
        Map the token to the boot artifacts.
        Update each node's desired state with the token.

        Because the connection to the BSS tokens database can be lost due to
        infrequent use, retry up to retries number of times.
        """
        if not components:
            # If we have been passed an empty list, there is nothing to do.
            LOGGER.debug("_set_bss: No components to act on")
            return
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
            except HTTPError as err:
                LOGGER.error("Failed to set BSS for boot artifacts: %s for nodes: %s. Error: %s",
                             key, nodes, exc_type_msg(err))
            else:
                token = resp.headers['bss-referral-token']
                attempts = 0
                while attempts <= retries:
                    try:
                        record_boot_artifacts(token, kernel, kernel_parameters, initrd)
                        break
                    except Exception as err:
                        attempts += 1
                        LOGGER.error("An error occurred attempting to record the BSS token: %s",
                                     exc_type_msg(err))
                        if attempts > retries:
                            raise
                        LOGGER.info("Retrying to record the BSS token.")

                for node in nodes:
                    bss_tokens.append({"id": node,
                                       "desired_state": {"bss_token": token},
                                       "session": sessions[node]})
        LOGGER.info('Found %d components that require BSS token updates', len(bss_tokens))
        if not bss_tokens:
            return
        redacted_component_updates = [
            { "id": comp["id"],
              "session": comp["session"]
            }
            for comp in bss_tokens ]
        LOGGER.debug('Updated components (minus desired_state data): {}'.format(redacted_component_updates))
        self.bos_client.components.update_components(bss_tokens)

if __name__ == '__main__':
    main(PowerOnOperator)


