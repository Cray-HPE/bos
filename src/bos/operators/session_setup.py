#!/usr/bin/env python
# Copyright 2021 Hewlett Packard Enterprise Development LP
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

import logging
from botocore.exceptions import ClientError

from bos.operators.base import BaseOperator, main
from bos.operators.utils.clients.hsm import Inventory
from bos.operators.utils.clients.s3 import S3Object
from bos.operators.utils.boot_image_metadata.factory import BootImageMetaDataFactory
from bos.operators.utils.rootfs.factory import ProviderFactory

LOGGER = logging.getLogger('bos.operators.session_setup')


class SessionSetupOperator(BaseOperator):
    """
    The Session Setup Operator sets the desired state of components based
    on existing sessions.
    """

    @property
    def name(self):
        return 'SessionSetup'

    def _run(self) -> None:
        """ A single pass of complete sessions """
        sessions = self._get_pending_sessions()
        if not sessions:
            return
        inventory_cache = Inventory()
        for data in sessions:
            session = Session(data, inventory_cache)
            session.setup()

    def _get_pending_sessions(self):
        return self.bos_client.sessions.get_sessions(status='pending')


class Session:
    def __init__(self, data, inventory_cache):
        self.session_data = data
        self.inventory = inventory_cache
        self._template = None

    @property
    def name(self):
        return self.session_data.get('name')

    @property
    def operation_type(self):
        return self.session_data.get('operation')

    @property
    def operation(self):
        return self.OPERATIONS[self.operation_type]

    @property
    def template(self):
        if not self._template:
            template_name = self.session_data.get('templateName')
            self._template = self.bos_client.session_templates.get_session_template(template_name)
        return self._template

    def setup(self):
        self._setup_components()
        self._mark_running()

    def _setup_components(self):
        for name, boot_set in self.template.get('boot_sets', {}).items():
            components = self._get_boot_set_component_list(boot_set)
            data = []
            for component in components:
                data.append(self.operation(boot_set, component))
            self.bos_client.components.update_components(data)

    def _get_boot_set_component_list(self, boot_set):
        nodes = set()
        # Populate from nodelist
        for node_name in boot_set.get('node_list', []):
            nodes.add(node_name)
        # Populate from node_groups
        for group_name in boot_set.get('node_groups', []):
            if group_name not in self.inventory.groups:
                self._log(LOGGER.warning, "No hardware matching label {}".format(group_name))
                continue
            nodes |= self.inventory.groups[group_name]
        # Populate from node_roles_groups
        for role_name in boot_set.get('node_roles_groups', []):
            if role_name not in self.inventory.roles:
                self._log(LOGGER.warning, "No hardware matching role {}".format(role_name))
                continue
            nodes |= self.inventory.roles[role_name]
        # Filter to nodes defined by limit
        nodes = self._apply_limit(nodes)
        if not nodes:
            self._log(LOGGER.warning, "No nodes were found to act on.")
            return nodes

    def _apply_limit(self, nodes):
        session_limit = self.session_data.get('limit')
        if not session_limit:
            # No limit is defined, so all nodes are allowed
            return nodes
        self._log(LOGGER.info, 'Applying limit to session: {}'.format(session_limit))
        limit_node_set = set()
        for limit in session_limit.split(','):
            if limit[0] == '&':
                limit = limit[1:]
                op = limit_node_set.intersection
            elif limit[0] == '!':
                limit = limit[1:]
                op = limit_node_set.difference
            else:
                op = limit_node_set.union

            limit_nodes = set([limit])
            if limit == 'all' or limit == '*':
                limit_nodes = nodes
            elif limit in self.inventory:
                limit_nodes = self.inventory[limit]
            limit_node_set = op(limit_nodes)
        nodes = nodes.intersection(limit_node_set)
        return nodes

    def _mark_running(self):
        self.bos_client.session.update_session(self.name, {'status': {'status': 'running'}})
        self._log(LOGGER.info, 'Session is running')

    def _log(self, logger, message):
        logger('Session {}: {}'.format(self.name, message))

    # Operations
    def boot(self, component, boot_set, force):
        state = self._get_state_from_boot_set(boot_set)
        data = {
            'id': component['id'],
            'desiredState': state
        }
        if force:
            pass
            # data['currentState'] = {'appliedToken': ''}
        return data

    @staticmethod
    def shutdown(component, _):
        return {
            'id': component['id'],
            'desiredState': {
                'configuration': '',
                'bootArtifacts': {
                    'kernel': '',
                    'kernelParameters': '',
                    'initrd': ''
                }
            }
        }

    def stage(self, component, boot_set, _):
        state = self._get_state_from_boot_set(boot_set)
        return {
            'id': component['id'],
            'stagedState': state
        }

    @staticmethod
    def boot_from_staged(component, _, force):
        data = {
            'id': component['id'],
            'desiredState': component.get('stagedState', {})
        }
        if force:
            pass
            # data['currentState'] = {'appliedToken': ''}
        return data

    def _get_state_from_boot_set(self, boot_set):
        state = {}
        boot_artifacts = {}
        image_metadata = BootImageMetaDataFactory(boot_set)()
        artifact_info = image_metadata.artifact_summary
        boot_artifacts['kernel'] = artifact_info['kernel']
        boot_artifacts['initrd'] = image_metadata['initrd']
        boot_artifacts['kernel_parameters'] = self.assemble_kernel_boot_parameters(boot_set, artifact_info)
        state['boot_artifacts'] = boot_artifacts

        if self.session_data.get('enable_cfs', False):
            configuration = {
                'configuration': self.session_data.get('cfs', {}).get('configuration', '')}
            if configuration:
                state['cfs'] = configuration

        return state

    def assemble_kernel_boot_parameters(self, boot_set, artifact_info):
        """
        Assemble the kernel boot parameters that we want to set in the
        Boot Script Service (BSS).

        Append the kernel boot parameters together in this order.

        1. Parameters from the image itself.
        2. Parameters from the BOS Session template
        3. rootfs parameters
        4. Node Memory Dump (NMD) parameters

        Warning: We need to ensure that the 'root' parameter exists and is set correctly.
        If any of the parameter locations are empty, they are simply not used.

        Returns:
            A string containing the needed kernel boot parameters

        Raises:
            ClientError -- An S3 client error
        """

        boot_param_pieces = []

        # Parameters from the image itself if the parameters exist.
        if (artifact_info.get('boot_parameters') is not None and
            artifact_info.get('boot_parameters_etag') is not None):
            LOGGER.info("++ _get_s3_download_url %s with etag %s.",
                        artifact_info['boot_parameters'],
                        artifact_info['boot_parameters_etag'])

            try:
                s3_obj = S3Object(artifact_info['boot_parameters'],
                                  artifact_info['boot_parameters_etag'])
                image_kernel_parameters_object = s3_obj.object

                image_kernel_parameters_raw = image_kernel_parameters_object['Body'].read().decode('utf-8')
                image_kernel_parameters = image_kernel_parameters_raw.split()
                if image_kernel_parameters:
                    boot_param_pieces.extend(image_kernel_parameters)
            except ClientError as error:
                LOGGER.error("Unable to read file {}. Thus, no kernel boot parameters obtained "
                             "from image".format(artifact_info['boot_parameters']))
                LOGGER.debug(error)

        # Parameters from the BOS Session template if the parameters exist.
        if boot_set.get('kernel_parameters'):
            boot_param_pieces.append(boot_set.get('kernel_parameters'))

        # Append special parameters for the rootfs and Node Memory Dump
        pf = ProviderFactory(self)
        provider = pf()
        rootfs_parameters = str(provider)
        if rootfs_parameters:
            boot_param_pieces.append(rootfs_parameters)
        nmd_parameters = provider.nmd_field
        if nmd_parameters:
            boot_param_pieces.append(nmd_parameters)

        # Add the Session ID to the kernel parameters
        boot_param_pieces.append("bos_session_id={}".format(self.name))

        return ' '.join(boot_param_pieces)

    OPERATIONS = {
        'boot': boot,
        'shutdown': shutdown,
        'stage': stage,
        'boot_from_staged': boot_from_staged
    }


if __name__ == '__main__':
    main(SessionSetupOperator)
