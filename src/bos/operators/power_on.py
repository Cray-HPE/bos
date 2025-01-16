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

# Standard imports
from collections import defaultdict
import logging
from typing import Dict, List, Set, Tuple, Union

# Third party imports
from requests import HTTPError

# BOS module imports
from bos.common.utils import exc_type_msg, using_sbps_check_kernel_parameters, \
                             components_by_id
from bos.common.values import Action, Status
from bos.operators.utils.clients import bss
from bos.operators.utils.clients import pcs
from bos.operators.utils.clients.ims import get_ims_id_from_s3_url, tag_image
from bos.operators.utils.clients.cfs import set_cfs
from bos.operators.utils.clients.s3 import S3Url
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

    def _act(self, components: Union[List[dict],None]):
        if not components:
            return components
        self._preset_last_action(components)

        boot_artifacts, sessions = self._sort_components_by_boot_artifacts(components)

        try:
            self._tag_images(boot_artifacts, components)
        except Exception as e:
            raise Exception(f"Error encountered tagging images {e}.") from e
        try:
            self._set_bss(boot_artifacts, bos_sessions=sessions)
        except Exception as e:
            raise Exception(f"Error encountered setting BSS information: {e}") from e
        try:
            set_cfs(components, enabled=False, clear_state=True)
        except Exception as e:
            raise Exception(f"Error encountered setting CFS information: {e}") from e
        component_ids = [component['id'] for component in components]
        try:
            pcs.power_on(component_ids)
        except Exception as e:
            raise Exception(f"Error encountered calling CAPMC to power on: {e}") from e
        return components

    def _sort_components_by_boot_artifacts(self, components: List[dict]) -> tuple[Dict, Dict]:
        """
        Create a two dictionaries.
        The first dictionary has keys with a unique combination of boot artifacts associated with
        a single boot image. They appear in this order:
         * kernel
         * kernel parameters
         * initrd
        The first dictionary's values are a set of the nodes that boot with those boot
        artifacts.

        The second dictionary has keys that are nodes and values are that node's BOS
        session.

        Inputs:
        * components: A list where each element is a component describe by a dictionary

        Returns: A tuple containing the first and second dictionary.
        """
        boot_artifacts = defaultdict(set)
        bos_sessions = {}
        for component in components:
            # Handle the boot artifacts
            nodes_boot_artifacts = component.get('desired_state', {}).get('boot_artifacts', {})
            kernel = nodes_boot_artifacts.get('kernel')
            kernel_parameters = nodes_boot_artifacts.get('kernel_parameters')
            initrd = nodes_boot_artifacts.get('initrd')
            if not any([kernel, kernel_parameters, initrd]):
                continue
            key = (kernel, kernel_parameters, initrd)
            boot_artifacts[key].add(component['id'])
            # Handle the session
            bos_sessions[component['id']] = component.get('session', "")

        return (boot_artifacts, bos_sessions)

    def _set_bss(self, boot_artifacts, bos_sessions, retries=5):
        """
        Set the boot artifacts (kernel, kernel parameters, and initrd) in BSS.
        Receive a BSS_REFERRAL_TOKEN from BSS.
        Map the token to the boot artifacts.
        Update each node's desired state with the token.

        Because the connection to the BSS tokens database can be lost due to
        infrequent use, retry up to retries number of times.
        """
        if not boot_artifacts:
            # If we have been passed an empty list, there is nothing to do.
            LOGGER.debug("_set_bss: No components to act on")
            return
        bss_tokens = []
        for key, nodes in boot_artifacts.items():
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
                                       "session": bos_sessions[node]})
        LOGGER.info('Found %d components that require BSS token updates', len(bss_tokens))
        if not bss_tokens:
            return
        redacted_component_updates = [
            { "id": comp["id"],
              "session": comp["session"]
            }
            for comp in bss_tokens ]
        LOGGER.debug('Updated components (minus desired_state data): %s',
                     redacted_component_updates)
        self.bos_client.components.update_components(bss_tokens)

    def _tag_images(self, boot_artifacts: Dict[Tuple[str, str, str], Set[str]],
                    components: List[dict]) -> None:
        """
        If the component is receiving its root file system via the SBPS provisioner,
        then tag that image in IMS, so that SBPS makes it available.
        This requires finding the IMS image ID associated with each component.
        Many components may be booted with the same image, but the image only needs to
        be tagged once.

        Inputs:
        * boot_artifacts: A dictionary keyed with a unique combination of boot artifacts
                          in this order:
                          * kernel
                          * kernel parameters
                          * initrd
                          These boot artifacts together represent a unique boot image
                          and are used to identify that image.
                          The values are the set of components being booted with that image.
        * components: A list where each element is a component describe by a dictionary
                      This is used to update the component with an error should one
                      occur.
        """
        if not boot_artifacts:
            # If we have been passed an empty dictionary, there is nothing to do.
            LOGGER.debug("_tag_images: No components to act on.")
            return

        image_id_to_nodes = defaultdict(set)
        err_msg_to_nodes = defaultdict(set)
        for boot_artifact, components_list in boot_artifacts.items():
            kernel_parameters = boot_artifact[1]
            if using_sbps_check_kernel_parameters(kernel_parameters):
                # Get the image ID
                err_msg = None

                # Get the path to the kernel
                kernel = boot_artifact[0]

                # Parse kernel patch as an S3 URL (the only supported boot artifact type for BOS)
                kernel_s3_url = S3Url(kernel)

                # Extract IMS ID from S3 URL
                image_id = get_ims_id_from_s3_url(kernel_s3_url) or None

                if image_id is None:
                    err_msg = f"Unable to extract IMS ID from kernel path: {kernel}"
                elif image_id == 'deleted':
                    # Soft deleted images in IMS move their S3 artifacts to have paths like s3://boot-images/deleted/<ims-id>/...
                    err_msg = f"Kernel path appears to refer to soft-deleted IMS image: '{kernel}'"

                if err_msg is None:
                    # Map image IDs to nodes
                    image_id_to_nodes[image_id].update(components_list)
                    continue

                LOGGER.error(err_msg)
                err_msg_to_nodes[err_msg].update(components_list)

        my_components_by_id = components_by_id(components)
        for err_msg, component_set in err_msg_to_nodes.items():
            self._record_component_errors(my_components_by_id, component_set, err_msg)

        for image in image_id_to_nodes:
            try:
                tag_image(image, "set", "sbps-project", "true")
            except Exception as e:
                self._record_component_errors(my_components_by_id, image_id_to_nodes[image],
                                              str(e))

    def _record_component_errors(self, my_components_by_id: Dict[str, dict],
                                 component_set: Set[str], err_msg: str) -> None:
        """
        my_components_by_id: Mapping from BOS component ID to component dictionary.
        component_set: Set of component IDs that need their error status updated.
        err_msg: Error message to use for updating their status.

        This updates the error status for each of the specified components, and then
        calls _update_database to update them in BOS.
        """
        components_to_update = []
        for node in component_set:
            my_components_by_id[node]["error"] = err_msg
            components_to_update.append(my_components_by_id[node])
        self._update_database(components_to_update)


if __name__ == '__main__':
    main(PowerOnOperator)
