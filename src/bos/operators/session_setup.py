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

"""
BOS session setup operator
"""

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable
import copy
import logging
from typing import Any

from botocore.exceptions import ClientError

from bos.common.clients.bos import BOSClient
from bos.common.clients.bos.options import options
from bos.common.clients.hsm import Inventory
from bos.common.clients.s3 import (BootImageArtifactSummary,
                                   BootImageMetadata,
                                   S3Object,
                                   S3ObjectNotFound)
from bos.common.clients.s3.types import ImageArtifactLinkManifest
from bos.common.tenant_utils import get_tenant_component_set, InvalidTenantException
from bos.common.types.components import (ComponentDesiredState,
                                         ComponentLastAction,
                                         ComponentRecord,
                                         ComponentStagedState)
from bos.common.types.components import BootArtifacts as ComponentStateBootArtifacts
from bos.common.types.sessions import Session as SessionRecord
from bos.common.types.templates import BootSet, SessionTemplate, SessionTemplateCfsParameters
from bos.common.utils import cached_property, exc_type_msg
from bos.common.values import Action, EMPTY_ACTUAL_STATE, EMPTY_DESIRED_STATE, EMPTY_STAGED_STATE
from bos.operators.base import BaseActionOperator, main, chunk_components
from bos.operators.filters import HSMState
from bos.operators.filters.base import BaseFilter
from bos.operators.session_completion import mark_session_complete
from bos.operators.utils.rootfs.factory import get_provider

LOGGER = logging.getLogger(__name__)


class SessionSetupException(Exception):
    """ The Session Set-up experienced a fatal error """


class SessionSetupOperator(BaseActionOperator):
    """
    The Session Setup Operator sets the desired state of components based
    on existing sessions.
    """

    action = Action.session_setup

    # This operator overrides _run and does not use "filters" or "_act", but they are defined here
    # because they are abstract methods in the base class and must be implemented.
    @property
    def filters(self) -> list[BaseFilter]:
        return []

    def _act(self, components: list[ComponentRecord]) -> list[ComponentRecord]:
        return components

    def _run(self) -> None:
        """ A single pass of pending sessions """
        sessions = self._get_pending_sessions()
        if not sessions:
            return
        LOGGER.info('Found %d sessions that require action', len(sessions))
        inventory_cache = Inventory(self.client.hsm)
        for data in sessions:
            session = get_session_object(data, inventory_cache, self.client.bos, self.HSMState, self._component_last_action)
            session.setup(self.max_batch_size)

    def _get_pending_sessions(self) -> list[SessionRecord]:
        return self.client.bos.sessions.get_sessions(status='pending')


class BaseSession[TargetStateT: (ComponentDesiredState, ComponentStagedState)](ABC):
    """
    The base class for setting up a new BOS session.
    Two concrete classes inerhit from this -- Session and StagedSession
    The child classes handle the slight differences between those two cases, while the
    common setup code is defined in this base class.
    """

    def __init__(self, data: SessionRecord, inventory_cache: Inventory, bos_client: BOSClient,
                 hsm_state: Callable[..., HSMState],
                 component_last_action: ComponentLastAction) -> None:
        self.session_data = data
        self.inventory = inventory_cache
        self.bos_client = bos_client
        self.HSMState = hsm_state
        self._component_last_action = component_last_action

    def _log_debug(self, message: str, *xargs: Any) -> None:
        LOGGER.debug(f'Session {self.name}: {message}', *xargs)

    def _log_error(self, message: str, *xargs: Any) -> None:
        LOGGER.error(f'Session {self.name}: {message}', *xargs)

    def _log_info(self, message: str, *xargs: Any) -> None:
        LOGGER.info(f'Session {self.name}: {message}', *xargs)

    def _log_warning(self, message: str, *xargs: Any) -> None:
        LOGGER.warning(f'Session {self.name}: {message}', *xargs)

    @abstractmethod
    def _set_component_data(self, data: ComponentRecord, state: TargetStateT) -> None:
        """
        Helper for the _operate method
        Set the component data fields for this session
        """

    @classmethod
    @abstractmethod
    def _empty_target_state(cls) -> TargetStateT:
        """
        Helper for the _generate_target_state method
        Return the "empty" state object for the target state type
        """

    @abstractmethod
    def _new_target_state(self, boot_artifacts: ComponentStateBootArtifacts,
                          configuration: str) -> TargetStateT:
        """
        Helper for the _generate_target_state method
        Create and return a new state object for the target state type
        """

    @property
    def name(self) -> str:
        return self.session_data['name']

    @property
    def tenant(self) -> str | None:
        return self.session_data.get('tenant')

    @property
    def operation_type(self) -> str:
        return self.session_data['operation']

    @cached_property
    def template(self) -> SessionTemplate:
        template_name = self.session_data['template_name']
        return self.bos_client.session_templates.get_session_template(template_name, self.tenant)

    def setup(self, max_batch_size: int) -> None:
        try:
            component_ids = self._setup_components(max_batch_size)
        except SessionSetupException as err:
            self._mark_failed(str(err))
        else:
            self._mark_running(component_ids)

    def _setup_components(self, max_batch_size: int) -> set[str]:
        all_component_ids: set[str] = set()
        data: list[ComponentRecord] = []
        try:
            for boot_set in self.template['boot_sets'].values():
                components = self._get_boot_set_component_list(boot_set)
                if not components:
                    continue
                state = self._generate_target_state(boot_set)
                for component_id in components:
                    data.append(self._operate(component_id, copy.deepcopy(state)))
                all_component_ids.update(components)
            if not all_component_ids:
                raise SessionSetupException("No nodes were found to act upon.")
        except Exception as err:
            self._log_debug(exc_type_msg(err))
            if isinstance(err, SessionSetupException):
                raise
            raise SessionSetupException(exc_type_msg(err)) from err
        # No exception raised by previous block
        self._log_info('Found %d components that require updates', len(data))
        for chunk in chunk_components(data, max_batch_size):
            self._log_debug('Updated components: %s', chunk)
            patched_comps = self.bos_client.components.update_components(chunk, skip_bad_ids=True)
            chunk_comp_ids = set(comp["id"] for comp in chunk)
            patched_comp_ids = set(comp["id"] for comp in patched_comps)
            unpatched_comp_ids = chunk_comp_ids - patched_comp_ids
            if not unpatched_comp_ids:
                continue
            self._log_warning('%d components not found in BOS: %s',
                              len(unpatched_comp_ids), unpatched_comp_ids)
            all_component_ids.difference_update(unpatched_comp_ids)
        if all_component_ids:
            return all_component_ids
        raise SessionSetupException("All nodes found to act upon do not exist as BOS components")

    def _get_boot_set_component_list(self, boot_set: BootSet) -> set[str]:
        # Populate from nodelist
        nodes: set[str] = set(boot_set.get('node_list', []))

        self._log_append_diff(set(), nodes, 'node_list')

        if nodes:
            tenant_nodes = self._apply_tenant_limit(nodes)
            if nodes != tenant_nodes:
                invalid_nodes = ",".join(list(nodes.difference(tenant_nodes)))
                raise SessionSetupException(
                    f"The session template includes nodes which do not exist"
                    f" or are not available to this tenant: {invalid_nodes}")

        # Populate from node_groups
        nodes_before = set(nodes)
        for group_name in boot_set.get('node_groups', []):
            if group_name not in self.inventory.groups:
                self._log_warning("No hardware matching label %s", group_name)
                continue
            nodes |= self.inventory.groups[group_name]
        self._log_append_diff(nodes_before, nodes, 'node_groups')

        # Populate from node_roles_groups
        nodes_before = set(nodes)
        for role_name in boot_set.get('node_roles_groups', []):
            if role_name not in self.inventory.roles:
                self._log_warning("No hardware matching role %s", role_name)
                continue
            nodes |= self.inventory.roles[role_name]
        self._log_append_diff(nodes_before, nodes, 'node_roles_groups')
        if not nodes:
            self._log_warning("After populating node list, before filtering, no nodes to act upon")
            return nodes
        self._log_debug("Before any limiting or filtering, %d nodes to act upon", len(nodes))

        # Filter to nodes defined by limit
        nodes = self._apply_limit(nodes)
        if not nodes:
            return nodes

        # Remove any nodes locked in HSM
        nodes = self._apply_hsm_lock_filter(nodes)
        if not nodes:
            return nodes

        # If this session is for a tenant, filter out nodes not belonging to this tenant
        nodes = self._apply_tenant_limit(nodes)
        if not nodes:
            return nodes

        # Filter out any nodes that do not match the boot set architecture desired; boot sets that
        # do not have a specified arch are considered 'X86' nodes.
        arch = boot_set.get('arch', 'X86')
        nodes = self._apply_arch(nodes, arch)
        if not nodes:
            return nodes

        # Exclude disabled nodes
        nodes = self._apply_include_disabled(nodes)
        return nodes

    def _log_filter_diff(self, nodes_before: set[str], nodes_after: set[str], action: str) -> None:
        """
        Logs an appropriate messgae at an appropriate log level, based on the results of
        the filtering
        """
        if nodes_before == nodes_after:
            self._log_debug("No nodes were removed when %s", action)
            return
        if not nodes_after:
            self._log_warning("After %s, no nodes remain to act upon", action)
            return
        self._log_debug("nodes_after %s = %s", action, nodes_after)
        nodes_diff = nodes_before - nodes_after
        nodes_diff_count = len(nodes_diff)
        if nodes_diff_count <= 10:
            self._log_info("%d nodes were removed when %s: %s", nodes_diff_count, action,
                           ','.join(sorted(nodes_diff)))
            return
        nodes_after_count = len(nodes_after)
        if nodes_after_count <= 10:
            self._log_info("%d nodes were removed when %s, leaving only %d nodes: %s",
                           nodes_diff_count, action, nodes_after_count,
                           ','.join(sorted(nodes_after)))
            return
        self._log_info("%d nodes were removed when %s, leaving %d nodes",
                       nodes_diff_count, action, nodes_after_count)

    def _log_append_diff(self, nodes_before: set[str], nodes_after: set[str],
                         bs_field: str) -> None:
        """
        Logs an appropriate messgae at an appropriate log level, based on the results of
        the appending (basically, the same as the previous method, except this one is when we are building up
        the node list, not whittling it down
        """
        text = f"nodes were added from '{bs_field}' boot set field"
        if nodes_before == nodes_after:
            self._log_debug("No %s", text)
            return
        self._log_debug("nodes_after %s = %s", text, nodes_after)
        nodes_diff = nodes_after - nodes_before
        nodes_diff_count = len(nodes_diff)
        if nodes_diff_count <= 10:
            self._log_info("%d %s: %s", nodes_diff_count, text,
                           ','.join(sorted(nodes_diff)))
            return
        self._log_info("%d %s, giving a new total of %d nodes", nodes_diff_count, text,
                       len(nodes_after))

    def _apply_arch(self, nodes: set[str], arch: str) -> set[str]:
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
        hsm_filter = self.HSMState()
        nodes_after = set(hsm_filter.filter_by_arch(nodes, valid_archs))
        self._log_filter_diff(nodes, nodes_after, "filtering for architecture")
        return nodes_after

    def _apply_include_disabled(self, nodes: set[str]) -> set[str]:
        """
        If include_disabled is False for this session, filter out any nodes which are disabled
        in HSM. Otherwise, return the node list unchanged.
        """
        include_disabled = self.session_data.get("include_disabled", False)
        if include_disabled:
            # Nodes disabled in HSM may be included, so no filtering is required
            return nodes
        hsmfilter = self.HSMState(enabled=True)
        nodes_after = set(hsmfilter.filter_component_ids(list(nodes)))
        self._log_filter_diff(nodes, nodes_after, "removing HSM-disabled nodes")
        return nodes_after

    def _apply_hsm_lock_filter(self, nodes: set[str]) -> set[str]:
        """
        Remove any nodes that are locked in HSM
        """
        hsmfilter = self.HSMState()
        nodes_after = hsmfilter.filter_for_unlocked(nodes)
        self._log_filter_diff(nodes, nodes_after, "removing nodes locked in HSM")
        return nodes_after

    def _apply_limit(self, nodes: set[str]) -> set[str]:
        session_limit = self.session_data.get('limit')
        if not session_limit:
            # No limit is defined, so all nodes are allowed
            return nodes
        self._log_info('Applying limit to session: %s', session_limit)
        limit_node_set: set[str] = set()
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
        nodes_after = nodes.intersection(limit_node_set)
        self._log_filter_diff(nodes, nodes_after, "applying BOS session limit")
        return nodes_after

    def _apply_tenant_limit(self, nodes: set[str]) -> set[str]:
        tenant = self.session_data.get("tenant")
        if not tenant:
            return nodes
        try:
            tenant_limit = get_tenant_component_set(tenant)
        except InvalidTenantException as e:
            raise SessionSetupException(str(e)) from e
        nodes_after = nodes.intersection(tenant_limit)
        self._log_filter_diff(nodes, nodes_after, "applying tenant limit")
        return nodes_after

    def _mark_running(self, component_ids: Iterable[str]) -> None:
        self.bos_client.sessions.update_session(
            self.name, self.tenant, {
                'status': {
                    'status': 'running'
                },
                "components": ",".join(component_ids)
            })
        self._log_info('Session is running')

    def _mark_failed(self, err: str) -> None:
        """
        Input:
          err (string): The error that prevented the session from running
        """
        mark_session_complete(self.name, self.tenant, self.bos_client, err=err)
        self._log_info('Session %s has failed.', self.name)

    # Operations
    def _operate(
        self, component_id: str, state: TargetStateT
    ) -> ComponentRecord:
        data: ComponentRecord = {"id": component_id, "error": ""}
        self._set_component_data(data, state)
        return data

    def _generate_target_state(self, boot_set: BootSet) -> TargetStateT:
        if self.operation_type == "shutdown":
            return self._empty_target_state()
        boot_artifacts = self._get_boot_artifacts_from_boot_set(boot_set)
        configuration = self._get_configuration_from_boot_set(boot_set)
        return self._new_target_state(boot_artifacts, configuration)

    def _get_boot_artifacts_from_boot_set(self, boot_set: BootSet) -> ComponentStateBootArtifacts:
        """
        Returns:
            A dictionary containing key/value pairs where the keys are
            the boot artifacts (kernel, initrd, rootfs, and boot parameters) and the values are
            paths to those artifacts in storage.
        """
        image_metadata = BootImageMetadata(boot_set)
        artifact_info = image_metadata.artifact_summary
        kernel = artifact_info['kernel']
        initrd = image_metadata.initrd.get("link", ImageArtifactLinkManifest()).get("path", "")
        kernel_parameters = self.assemble_kernel_boot_parameters(boot_set, artifact_info)
        return ComponentStateBootArtifacts(kernel=kernel, initrd=initrd,
                                           kernel_parameters=kernel_parameters)

    def _get_configuration_from_boot_set(self, boot_set: BootSet) -> str:
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
        bs_config = boot_set.get('cfs', SessionTemplateCfsParameters()).get('configuration', '')
        if bs_config:
            return bs_config
        # Otherwise, we take the configuration value from the session template itself
        return self.template.get('cfs', {}).get('configuration', '')

    def assemble_kernel_boot_parameters(self, boot_set: BootSet,
                                        artifact_info: BootImageArtifactSummary) -> str:
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
        boot_param_pieces = self._base_boot_param_pieces(artifact_info)

        # Parameters from the BOS Session template if the parameters exist.
        if (kernel_parameters := boot_set.get('kernel_parameters')):
            boot_param_pieces.append(kernel_parameters)

        # Append special parameters for the rootfs and Node Memory Dump
        provider = get_provider(boot_set, artifact_info)
        rootfs_parameters = str(provider)
        if rootfs_parameters:
            boot_param_pieces.append(rootfs_parameters)
        nmd_parameters = provider.nmd_field
        if nmd_parameters:
            boot_param_pieces.append(nmd_parameters)

        # Add the bos actual state ttl value so nodes know how frequently to report
        boot_param_pieces.append(
            f'bos_update_frequency={options.component_actual_state_ttl}')

        return ' '.join(boot_param_pieces)

    def _base_boot_param_pieces(self, artifact_info: BootImageArtifactSummary) -> list[str]:
        """
        Helper for assemble_kernel_boot_parameters that generates the initial boot parameter pieces,
        based on the image boot parameters
        """
        boot_param_pieces: list[str] = []

        # Parameters from the image itself if the parameters exist.
        boot_parameters = artifact_info.get('boot_parameters')
        if boot_parameters is None:
            return boot_param_pieces
        boot_parameters_etag = artifact_info.get('boot_parameters_etag')
        if boot_parameters_etag is None:
            return boot_param_pieces
        self._log_info("++ _get_s3_download_url %s with etag %s.",
                       boot_parameters, boot_parameters_etag)

        try:
            s3_obj = S3Object(boot_parameters, boot_parameters_etag)
            image_kernel_parameters_object = s3_obj.object

            parameters_raw = image_kernel_parameters_object['Body'].read().decode('utf-8')
            image_kernel_parameters = parameters_raw.split()
            if image_kernel_parameters:
                boot_param_pieces.extend(image_kernel_parameters)
        except (ClientError, UnicodeDecodeError, S3ObjectNotFound) as error:
            self._log_error("Error reading file %s; no kernel boot parameters obtained from image",
                            artifact_info['boot_parameters'])
            self._log_error(exc_type_msg(error))
            raise
        return boot_param_pieces


class Session(BaseSession[ComponentDesiredState]):
    """
    Concrete class for setting up a non-staged BOS session
    """

    @classmethod
    def _empty_target_state(cls) -> ComponentDesiredState:
        """
        Helper for the _generate_target_state method
        Return the "empty" state object for the target state type
        """
        return EMPTY_DESIRED_STATE

    def _new_target_state(self, boot_artifacts: ComponentStateBootArtifacts,
                          configuration: str) -> ComponentDesiredState:
        """
        Helper for the _generate_target_state method
        Create and return a new state object for the target state type
        """
        return ComponentDesiredState(boot_artifacts=boot_artifacts, configuration=configuration)

    def _set_component_data(self, data: ComponentRecord, state: ComponentDesiredState) -> None:
        """
        Helper for the _operate method
        Set the component data fields for this session
        """
        data["desired_state"] = state
        if self.operation_type == "reboot":
            data["actual_state"] = EMPTY_ACTUAL_STATE
        data["session"] = self.name
        data["enabled"] = True
        # Set node's last_action
        data["last_action"] = self._component_last_action


class StagedSession(BaseSession[ComponentStagedState]):
    """
    Concrete class for setting up a staged BOS session
    """

    @classmethod
    def _empty_target_state(cls) -> ComponentStagedState:
        """
        Helper for the _generate_target_state method
        Return the "empty" state object for the target state type
        """
        return EMPTY_STAGED_STATE

    def _new_target_state(self, boot_artifacts: ComponentStateBootArtifacts,
                          configuration: str) -> ComponentStagedState:
        """
        Helper for the _generate_target_state method
        Create and return a new state object for the target state type
        """
        return ComponentStagedState(boot_artifacts=boot_artifacts, configuration=configuration,
                                    session=self.name)

    def _set_component_data(self, data: ComponentRecord, state: ComponentStagedState) -> None:
        """
        Helper for the _operate method
        Set the component data fields for this session
        """
        data["staged_state"] = state


def get_session_object(data: SessionRecord, inventory_cache: Inventory, bos_client: BOSClient,
                       hsm_state: Callable[..., HSMState],
                       component_last_action: ComponentLastAction) -> Session | StagedSession:
    if data.get("stage", False):
        return StagedSession(data, inventory_cache, bos_client, hsm_state, component_last_action)
    return Session(data, inventory_cache, bos_client, hsm_state, component_last_action)


if __name__ == '__main__':
    main(SessionSetupOperator)
