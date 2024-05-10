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
from typing import List, Type

from bos.operators.utils.clients.capmc import disable_based_on_error_xname_on_off, power
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
        Apply the _my_power operation to a list of components.
        Handle any errors. This includes setting the error per component and
        disabling the component.

        If we know which nodes experienced errors, then set their errors and
        disable them. If we do not know which nodes experienced errors, then
        attempt to power them on or off individually. Any errors encountered
        will be specific to the individual node.

        Inputs:
        :param List[dict] components: A list of the components to operate on

        :return components: the
        :rtype: A list of dictionaries where the individual elements are Components
        """
        component_ids = [component['id'] for component in components]
        errors = self._my_power(component_ids)
        if errors.error_code == 0:
            return components
            
        if errors.nodes_in_error:
            # Update any nodes with errors they encountered
            for component in errors.nodes_in_error:
                index = self._find_component_in_components(component, components)
                if index is not None:
                    error = errors.nodes_in_error[component].error_message
                    components[index]['error'] = error
                    components[index]['enabled'] = disable_based_on_error_xname_on_off(error)
            return components

        # Errors could not be associated with a specific node.
        # Ask CAPMC to act on them one at a time to identify
        # nodes associated with errors.
        for component in component_ids:
            LOGGER.debug("Acting on component %s", component)
            errors = self._my_power([component])
            if errors.error_code == 0:
                continue
            LOGGER.debug("Component %s error code=%s message=%s", component,
                         errors.error_code, errors.error_message)
            index = self._find_component_in_components(component, components)
            if index is not None:
                components[index]['error'] = errors.error_message
                components[index]['enabled'] = False
        return components

    def _find_component_in_components(self, component_id, components) -> int:
        """
        In a list of components, find the component that matches
        the component ID. Return its index in the list.

        :param str component_id: The component ID
        :param List[dict] components: A list of components

        Returns:
          An index indicating the matched components location in the list
          It returns None if there is no match.
          :rtype: int
        """
        for component in components:
            if component_id == component['id']:
                return components.index(component)
        return None

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
