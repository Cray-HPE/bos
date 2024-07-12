#!/usr/bin/env python
#
# MIT License
#
# (C) Copyright 2021-2024 Hewlett Packard Enterprise Development LP
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
import copy
import logging
from typing import Set
from botocore.exceptions import ClientError

from bos.operators.base import BaseOperator, main
from bos.operators.filters.filters import HSMState
from bos.operators.utils.clients.hsm import Inventory
from bos.operators.utils.clients.s3 import S3Object, S3ObjectNotFound
from bos.operators.utils.boot_image_metadata.factory import BootImageMetaDataFactory
from bos.operators.utils.clients.bos.options import options
from bos.operators.utils.rootfs.factory import ProviderFactory
from bos.operators.session_completion import SessionCompletionOperator
from bos.common.utils import exc_type_msg
from bos.common.values import Action, EMPTY_ACTUAL_STATE, EMPTY_DESIRED_STATE, EMPTY_STAGED_STATE
from bos.common.tenant_utils import get_tenant_component_set, InvalidTenantException

LOGGER = logging.getLogger('bos.operators.session_setup')


class SessionSetupException(Exception):
    """ The Session Set-up experienced a fatal error """


class SessionSetupOperator(BaseOperator):
    """
    The Session Setup Operator sets the desired state of components based
    on existing sessions.
    """

    @property
    def name(self):
        return 'SessionSetup'

    # This operator overrides _run and does not use "filters" or "_act", but they are defined here
    # because they are abstract methods in the base class and must be implemented.
    @property
    def filters(self):
        return []

    def _act(self, components):
        return components

    def _run(self) -> None:
        """ A single pass of complete sessions """
        sessions = self._get_pending_sessions()
        if not sessions:
            return
        LOGGER.info('Found %d sessions that require action', len(sessions))
        inventory_cache = Inventory()
        for data in sessions:
            session = Session(data, inventory_cache, self.bos_client)
            session.setup()

    def _get_pending_sessions(self):
        return self.bos_client.sessions.get_sessions(status='pending')


class Session:

    def __init__(self, data, inventory_cache, bos_client):
        self.session_data = data
        self.inventory = inventory_cache
        self.bos_client = bos_client
        self._template = None

    @property
    def name(self):
        return self.session_data.get('name')

    @property
    def tenant(self):
        return self.session_data.get('tenant')

    @property
    def operation_type(self):
        return self.session_data.get('operation')

    @property
    def template(self):
        if not self._template:
            template_name = self.session_data.get('template_name')
            self._template = self.bos_client.session_templates.get_session_template(template_name,
                                                                                    self.tenant)
        return self._template

    def setup(self):
        try:
            component_ids = self._setup_components()
        except SessionSetupException as err:
            self._mark_failed(str(err))
        else:
            self._mark_running(component_ids)

    def _setup_components(self):
        all_component_ids = []
        data = []
        stage = self.session_data.get("stage", False)
        try:
            for _, boot_set in self.template.get('boot_sets', {}).items():
                components = self._get_boot_set_component_list(boot_set)
                if not components:
                    continue
                if stage:
                    state = self._generate_desired_state(boot_set, staged=True)
                else:
                    state = self._generate_desired_state(boot_set)
                for component_id in components:
                    data.append(self._operate(component_id, copy.deepcopy(state)))
                all_component_ids += components
            if not all_component_ids:
                raise SessionSetupException("No nodes were found to act upon.")
        except Exception as err:
            raise SessionSetupException(err) from err
        # No exception raised by previous block
        self._log(LOGGER.info, 'Found %d components that require updates', len(data))
        self._log(LOGGER.debug, f'Updated components: {data}')
        self.bos_client.components.update_components(data)
        return list(set(all_component_ids))

    def _get_boot_set_component_list(self, boot_set) -> Set[str]:
        nodes = set()
        # Populate from nodelist
        for node_name in boot_set.get('node_list', []):
            nodes.add(node_name)
        if nodes:
            tenant_nodes = self._apply_tenant_limit(nodes)
            if nodes != tenant_nodes:
                invalid_nodes = ",".join(list(nodes.difference(tenant_nodes)))
                raise SessionSetupException(
                    f"The session template includes nodes which do not exist"
                    f" or are not available to this tenant: {invalid_nodes}")
        # Populate from node_groups
        for group_name in boot_set.get('node_groups', []):
            if group_name not in self.inventory.groups:
                self._log(LOGGER.warning, f"No hardware matching label {group_name}")
                continue
            nodes |= self.inventory.groups[group_name]
        # Populate from node_roles_groups
        for role_name in boot_set.get('node_roles_groups', []):
            if role_name not in self.inventory.roles:
                self._log(LOGGER.warning, f"No hardware matching role {role_name}")
                continue
            nodes |= self.inventory.roles[role_name]
        if not nodes:
            self._log(LOGGER.warning,
                      "After populating node list, before any filtering, no nodes to act upon.")
            return nodes
        self._log(LOGGER.debug, "Before any limiting or filtering, %d nodes to act upon.",
                  len(nodes))
        # Filter out any nodes that do not match the boot set architecture desired; boot sets that
        # do not have a specified arch are considered 'X86' nodes.
        arch = boot_set.get('arch', 'X86')
        nodes = self._apply_arch(nodes, arch)
        if not nodes:
            return nodes
        # Filter to nodes defined by limit
        nodes = self._apply_limit(nodes)
        if not nodes:
            return nodes
        # Exclude disabled nodes
        nodes = self._apply_include_disabled(nodes)
        if not nodes:
            return nodes
        # If this session is for a tenant, filter out nodes not belonging to this tenant
        nodes = self._apply_tenant_limit(nodes)
        return nodes

    def _apply_arch(self, nodes, arch):
        """
        Removes any node from <nodes> that does not match arch. Nodes in HSM that do not have the
        arch field, and nodes that have the arch field flagged as undefined are assumed to be of
        type 'X86'. String value of arch directly corresponds to those values in HSM components;
        this string is case-sensitive ('ARM' works, 'arm' does not). Similarly, we cannot query
        HSM using an all-caps approach because of 'Other' and 'Unknown' would then never match.

        Because nodes may not have a known architecture, all nodes that are of unknown
        architecture count as being of type X86.
        args:
          nodes: an iterator of nodes by xnames that correspond to components in HSM.
          arch: A string representing a corresponding ARCH from HSM.
        returns:
          A set representing the subset of nodes that match arch, or the logical arch from HSM.
        """
        if not nodes:
            return nodes
        valid_archs = set([arch])
        if arch == 'X86':
            valid_archs.add('UNKNOWN')
        hsm_filter = HSMState()
        nodes = set(hsm_filter.filter_by_arch(nodes, valid_archs))
        if not nodes:
            self._log(LOGGER.warning,
                      "After filtering for architecture, no nodes remain to act upon.")
        else:
            self._log(LOGGER.debug,
                      "After filtering for architecture, %d nodes remain to act upon.", len(nodes))
        return nodes

    def _apply_include_disabled(self, nodes):
        """
        If include_disabled is False for this session, filter out any nodes which are disabled
        in HSM. Otherwise, return the node list unchanged.
        """
        include_disabled = self.session_data.get("include_disabled", False)
        if include_disabled:
            # Nodes disabled in HSM may be included, so no filtering is required
            return nodes
        hsmfilter = HSMState(enabled=True)
        nodes = set(hsmfilter._filter(list(nodes)))
        if not nodes:
            self._log(LOGGER.warning,
                      "After removing disabled nodes, no nodes remain to act upon.")
        else:
            self._log(LOGGER.debug, "After removing disabled nodes, %d nodes remain to act upon.",
                      len(nodes))
        return nodes

    def _apply_limit(self, nodes):
        session_limit = self.session_data.get('limit')
        if not session_limit:
            # No limit is defined, so all nodes are allowed
            return nodes
        self._log(LOGGER.info, f'Applying limit to session: {session_limit}')
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
            if limit in {'all', '*'}:
                limit_nodes = nodes
            elif limit in self.inventory:
                limit_nodes = self.inventory[limit]
            limit_node_set = op(limit_nodes)
        nodes = nodes.intersection(limit_node_set)
        if not nodes:
            self._log(LOGGER.warning, "After applying limit, no nodes remain to act upon.")
        else:
            self._log(LOGGER.debug, "After applying limit, %d nodes remain to act upon.",
                      len(nodes))
        return nodes

    def _apply_tenant_limit(self, nodes):
        tenant = self.session_data.get("tenant")
        if not tenant:
            return nodes
        try:
            tenant_limit = get_tenant_component_set(tenant)
        except InvalidTenantException as e:
            raise SessionSetupException(str(e)) from e
        nodes = nodes.intersection(tenant_limit)
        if not nodes:
            self._log(LOGGER.warning, "After applying tenant limit, no nodes remain to act upon.")
        else:
            self._log(LOGGER.debug, "After applying tenant limit, %d nodes remain to act upon.",
                      len(nodes))
        return nodes

    def _mark_running(self, component_ids):
        self.bos_client.sessions.update_session(
            self.name, self.tenant,
            {'status': {'status': 'running'}, "components": ",".join(component_ids)})
        self._log(LOGGER.info, 'Session is running')

    def _mark_failed(self, err):
        """
        Input:
          err (string): The error that prevented the session from running
        """
        self.bos_client.sessions.update_session(
            self.name, self.tenant, {'status': {'error': err}})
        sco = SessionCompletionOperator()
        sco._mark_session_complete(self.name, self.tenant)
        self._log(LOGGER.info, f'Session {self.name} has failed.')

    def _log(self, logger, message, *xargs):
        logger('Session {}: {}'.format(self.name, message), *xargs)

    # Operations
    def _operate(self, component_id, state):
        stage = self.session_data.get("stage", False)
        data = {"id": component_id}
        if stage:
            data["staged_state"] = state
            data["staged_state"]["session"] = self.name
        else:
            data["desired_state"] = state
            if self.operation_type == "reboot" :
                data["actual_state"] = EMPTY_ACTUAL_STATE
            data["session"] = self.name
            data["enabled"] = True
            # Set node's last_action
            data["last_action"] = {"action": Action.session_setup}
        data['error'] = ''
        return data

    def _generate_desired_state(self, boot_set, staged=False):
        if self.operation_type == "shutdown":
            return EMPTY_STAGED_STATE if staged else EMPTY_DESIRED_STATE
        state = self._get_state_from_boot_set(boot_set)
        return state

    def _get_state_from_boot_set(self, boot_set):
        """
        Returns:
          state: A dictionary containing two keys 'boot_artifacts' and 'configuration'.
            'boot_artifacts' is itself a dictionary containing key/value pairs where the keys are
            the boot artifacts (kernel, initrd, rootfs, and boot parameters) and the values are
            paths to those artifacts in storage.
            'configuration' is a string.
        """
        state = {}
        boot_artifacts = {}
        image_metadata = BootImageMetaDataFactory(boot_set)()
        artifact_info = image_metadata.artifact_summary
        boot_artifacts['kernel'] = artifact_info['kernel']
        boot_artifacts['initrd'] = image_metadata.initrd.get("link", {}).get("path", "")
        boot_artifacts['kernel_parameters'] = self.assemble_kernel_boot_parameters(boot_set,
                                                                                   artifact_info)
        state['boot_artifacts'] = boot_artifacts
        state['configuration'] = self._get_configuration_from_boot_set(boot_set)
        return state

    def _get_configuration_from_boot_set(self, boot_set: dict):
        """
        An abstraction method for determining the configuration to use
        in the event for any given <boot set> within a session. Boot Sets
        can define their own cfs configuration name as an override to
        a provided session level configuration. Alternatively, disabling
        configuration from within the session level boolean 'enable_cfs'
        will override any value set within a boot set.
        """
        if not self.template.get('enable_cfs', True):
            return ''
        bs_config = boot_set.get('configuration', '')
        if bs_config:
            return bs_config
        # Otherwise, we take the configuration value from the session template itself
        return self.template.get('cfs', {}).get('configuration', '')

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

        Inputs:
            boot_set: A boot set from the session template data
            artifact_info: The artifact summary from the boot_set.
                           This is a dictionary containing keys which are boot artifacts (kernel,
                           initrd, roots, and kernel boot parameters).
                           The values are the paths to those boot artifacts in S3.
                           It also contains the etags for the rootfs and kerenl boot parameters.
        Returns:
            A string containing the needed kernel boot parameters

        Raises:
            ClientError -- An S3 client error
        """

        boot_param_pieces = []

        # Parameters from the image itself if the parameters exist.
        if (artifact_info.get('boot_parameters') is not None and
            artifact_info.get('boot_parameters_etag') is not None):
            self._log(LOGGER.info,
                        "++ _get_s3_download_url %s with etag %s.",
                        artifact_info['boot_parameters'],
                        artifact_info['boot_parameters_etag'])

            try:
                s3_obj = S3Object(artifact_info['boot_parameters'],
                                  artifact_info['boot_parameters_etag'])
                image_kernel_parameters_object = s3_obj.object

                parameters_raw = image_kernel_parameters_object['Body'].read().decode('utf-8')
                image_kernel_parameters = parameters_raw.split()
                if image_kernel_parameters:
                    boot_param_pieces.extend(image_kernel_parameters)
            except (ClientError, UnicodeDecodeError, S3ObjectNotFound) as error:
                self._log(LOGGER.error,
                          "Error reading file %s; no kernel boot parameters obtained from image",
                          artifact_info['boot_parameters'])
                self._log(LOGGER.error, exc_type_msg(error))
                raise

        # Parameters from the BOS Session template if the parameters exist.
        if boot_set.get('kernel_parameters'):
            boot_param_pieces.append(boot_set.get('kernel_parameters'))

        # Append special parameters for the rootfs and Node Memory Dump
        pf = ProviderFactory(boot_set, artifact_info)
        provider = pf()
        rootfs_parameters = str(provider)
        if rootfs_parameters:
            boot_param_pieces.append(rootfs_parameters)
        nmd_parameters = provider.nmd_field
        if nmd_parameters:
            boot_param_pieces.append(nmd_parameters)

        # Add the bos actual state ttl value so nodes know how frequently to report
        boot_param_pieces.append('bos_update_frequency=%s' % (options.component_actual_state_ttl))

        return ' '.join(boot_param_pieces)


if __name__ == '__main__':
    main(SessionSetupOperator)
