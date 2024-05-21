#!/usr/bin/env python
#
# MIT License
#
# (C) Copyright 2021-2022, 2024 Hewlett Packard Enterprise Development LP
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
from typing import Dict, List, Type, Union

from bos.operators.utils.clients.capmc import CapmcNodeError, disable_based_on_error_xname_on_off, power
from bos.operators.base import BaseOperator, main
from bos.operators.filters.base import BaseFilter

LOGGER = logging.getLogger('bos.operators.power_base')


class PowerOperatorBase(BaseOperator):
    """
    An abstract class for all BOS power operators.

    Override these methods and properties.
    NAME - This field determines how the operator/action is logged in the components database.
    FILTERS - A list of all filters that are used to determine which components should be acted on.
        Includes the initial query for BOS components as the query also includes filtering.
    _my_power - This method indicates the power action to be taken by the operator.
    Any other method may also be overridden, but functionality such as error handling may be lost.

    """

    retry_attempt_field = "power_base_operator"

    @property
    def name(self) -> str:
        return 'Invalid Action Type'

    # Filters
    @property
    def filters(self) -> List[Type[BaseFilter]]:
        return []

    def _act(self, components) -> List[dict]:
        """
        Calls the _power_components method.
        Override this method to perform additional actions specific to the
        power operator.
        Be sure to finish with the return statement below.
        """
        return self._power_components(components)

    def _power_components(self, components: List[dict]) -> List[dict]:
        """
        Calls _do_power_components to apply the _my_power operation to a
        list of components.

        The return value of the function is the same list object as what
        it is called with -- the only changes happening are to the components
        in the list, not to the list itself.

        Inputs:
        :param List[dict] components: A list of the components to operate on

        Returns:
          components: A list of dictionaries where the individual elements are Components
        :rtype: List[dict]
        """
        if not components:
            return components
        self._do_power_components({ component['id']: component for component in components })
        return components

    def _do_power_components(self, component_id_map: Dict[str, dict],
                             component_ids: Union[None,List[str]]=None) -> None:
        """
        Apply the _my_power operation to a list of components.
        Handle any errors. This includes setting the error per component and
        disabling the component.

        If we know which nodes experienced errors, then set their errors and
        disable them. If we do not know which nodes experienced errors, then
        attempt to power them on or off individually. Any errors encountered
        will be specific to the individual node.

        Input:
        :param Dict[str,dict] component_id_map: A mapping from component IDs
        to components (used to update the status of the components)
        :param List[str] component_ids: A list of component IDs to operate on.
        If None, operate on all components in the map.

        Returns:
          None
        """
        if component_ids is None:
            component_ids = list(component_id_map)
        num_components = len(component_ids)
        LOGGER.debug("_do_power_components called on %d components", num_components)
        errors = self._my_power(component_ids)
        if errors.error_code == 0:
            return

        if errors.nodes_in_error:
            # Update any nodes with errors they encountered
            for component_id, node_error in errors.nodes_in_error.items():
                if component_id in component_ids:
                    self._update_component_with_node_error(component_id_map[component_id],
                                                           node_error)
                else:
                    LOGGER.warning("CAPMC error for xname that wasn't in request: %s error code=%s"
                                   " message=%s", component_id, node_error.error_code,
                                   node_error.error_message)
            return

        # Errors could not be associated with a specific node.

        if num_components >= 16:
            # Subdivide the nodes into 8 groups and recursively act on those
            chunk_size = len(component_ids) // 8
            while component_ids:
                self._do_power_components(component_id_map, component_ids[:chunk_size])
                component_ids = component_ids[chunk_size:]
            return

        if num_components == 1:
            # Well, okay, I guess the error can be associated with this node
            component_id = component_ids[0]
            LOGGER.debug("Component %s error code=%s message=%s", component_id,
                         errors.error_code, errors.error_message)
            component = component_id_map[component_id]
            component['error'] = errors.error_message
            component['enabled'] = False
            return

        # num_components < 16:
        # Ask CAPMC to act on them one at a time to identify
        # nodes associated with errors.
        for component_id in component_ids:
            LOGGER.debug("Acting on component %s", component_id)
            errors = self._my_power([component_id])
            if errors.error_code == 0:
                continue
            if errors.nodes_in_error:
                if any(node != component_id for node in errors.nodes_in_error):
                    LOGGER.warning("CAPMC errors for xnames that weren't in request: %s",
                                   { node: err for node, err in errors.nodes_in_error.items()
                                               if node != component_id })
                if component_id in errors.nodes_in_error:
                    self._update_component_with_node_error(component_id_map[component_id],
                                                           errors.nodes_in_error[component_id])
                    continue
            LOGGER.debug("Component %s error code=%s message=%s", component_id,
                         errors.error_code, errors.error_message)
            component = component_id_map[component_id]
            component['error'] = errors.error_message
            component['enabled'] = False

    def _update_component_with_node_error(self, component: dict, node_error: CapmcNodeError) -> None:
        LOGGER.debug("Component %s error code=%s message=%s", component['id'],
                     node_error.error_code, node_error.error_message)
        component['error'] = node_error.error_message
        component['enabled'] = disable_based_on_error_xname_on_off(node_error.error_message)

    def _my_power(self, component_ids: List[str]):
        """
        Overide this function with the power call specific to the operator.

        Returns:
          errors (dict): A class containing o on error code, error message, and
          a dictionary containing the nodes (keys) suffering from errors (values)
          :rtype: CapmcXnameOnOffReturnedError
        """
        return power(component_ids)

if __name__ == '__main__':
    main(PowerOperatorBase)
