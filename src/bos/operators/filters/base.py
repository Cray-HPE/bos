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
from abc import ABC, abstractmethod
import logging

from bos.common.types.components import ComponentRecord

LOGGER = logging.getLogger(__name__)


# Abstracts
class BaseFilter[T](ABC):
    """
    A basic abstract filter that includes error handling
    Do not build off this class, IDFilter and DetailsFilter include more functionality

    filter_components should be overridden
    """

    INITIAL: bool = False  # Set for filters that are meant to be the first in the list

    @classmethod
    def component_list_to_id_list(cls, components: list[ComponentRecord]) -> list[str]:
        return [component.get('id', '') for component in components]

    def filter(self, components: list[ComponentRecord]) -> list[ComponentRecord]:
        results = []
        try:
            if components or self.INITIAL:
                results = self.filter_components(components)
        except Exception as e:
            LOGGER.exception(e)
        LOGGER.debug('%s filter found the following components: %s', type(self).__name__,
                     ','.join(self.component_list_to_id_list(results)))
        return results

    @abstractmethod
    def filter_components(self, components: list[ComponentRecord]) -> list[ComponentRecord]: ...


class IDFilter(BaseFilter[str], ABC):
    """ A base class for filters that take and return lists of component ids """

    def filter_components(self, components: list[ComponentRecord]) -> list[ComponentRecord]:
        id_results = self.filter_component_ids(self.component_list_to_id_list(components))
        return [ component for component in components if component['id'] in id_results ]

    @abstractmethod
    def filter_component_ids(self, components: list[str]) -> list[str]: ...


class DetailsFilter(BaseFilter[ComponentRecord], ABC):
    """ A base class for filters that take and return lists of detailed component information """


class LocalFilter(DetailsFilter, ABC):
    """
    A base class for filters that loop over component information that is already obtained.
    Only the component_match method needs to be overridden to filter on one component at a time.
    """

    def __init__(self, negate: bool = False) -> None:
        super().__init__()
        self._negate = negate

    def filter_components(self, components: list[ComponentRecord]) -> list[ComponentRecord]:
        matching_components = []
        for component in components:
            if self.component_is_match(component):
                matching_components.append(component)
        return matching_components

    def component_is_match(self, component: ComponentRecord) -> bool:
        if self._negate:
            return not self.component_match(component)
        return self.component_match(component)

    @abstractmethod
    def component_match(self, component: ComponentRecord) -> bool: ...
