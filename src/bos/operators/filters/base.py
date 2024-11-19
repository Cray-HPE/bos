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
from abc import ABC, abstractmethod
import logging
from typing import Generic, TypeVar

from bos.common.types import Component

LOGGER = logging.getLogger('bos.operators.filters.base')

T = TypeVar('T')

# Abstracts
class BaseFilter(Generic[T], ABC):
    """
    A basic abstract filter that includes error handling
    Do not build off this class, IDFilter and DetailsFilter include more functionality

    _filter should be overridden
    """

    INITIAL: bool = False  # Set for filters that are meant to be the first in the list

    @abstractmethod
    def filter(self, components: list[Component]) -> list[Component]:
        raise NotImplementedError

    def apply_filter(self, components: list[T]) -> list[T]:
        results = []
        try:
            if components or self.INITIAL:
                results = self._filter(components)
        except Exception as e:
            LOGGER.exception(e)
        return results

    @abstractmethod
    def _filter(self, components: list[T]) -> list[T]:
        raise NotImplementedError


class IDFilter(BaseFilter[str], ABC):
    """ A class for filters that take and return lists of component ids """
    def filter(self, components: list[Component]) -> list[Component]:
        component_ids = [component['id'] for component in components]
        results = self.apply_filter(components=component_ids)
        LOGGER.debug('%s filter found the following components: %s', type(self).__name__,
                     ','.join(results))
        return [component for component in components if component['id'] in results]

    @abstractmethod
    def _filter(self, components: list[str]) -> list[str]:
        raise NotImplementedError


class DetailsFilter(BaseFilter[Component], ABC):
    """ A class for filters that take and return lists of detailed component information """
    def filter(self, components: list[Component]) -> list[Component]:
        results = self.apply_filter(components=components)
        LOGGER.debug('%s filter found the following components: %s', type(self).__name__,
                     ','.join([component.get('id', '') for component in results]))
        return results

    @abstractmethod
    def _filter(self, components: list[Component]) -> list[Component]:
        raise NotImplementedError


class LocalFilter(DetailsFilter, ABC):
    """
    A class for filters that loop over component information that is already obtained.
    Only the _match method needs to be overridden to filter on one component at a time.
    """
    def __init__(self, negate: bool = False) -> None:
        super().__init__()
        self._negate = negate

    def _filter(self, components: list[Component]) -> list[Component]:
        matching_components = []
        for component in components:
            if self._is_match(component):
                matching_components.append(component)
        return matching_components

    def _is_match(self, component: Component) -> bool:
        if self._negate:
            return not self._match(component)
        return self._match(component)

    @abstractmethod
    def _match(self, component: Component) -> bool:
        raise NotImplementedError
