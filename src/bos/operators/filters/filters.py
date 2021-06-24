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

import copy
from datetime import datetime, timedelta
from dateutil import parser
import logging
from typing import List, Type

from bos.operators.filters.base import BaseFilter, DetailsFilter, IDFilter, LocalFilter
from bos.operators.utils.clients.bos.components import get_components
from bos.operators.utils.clients.capmc import status as get_power_state
from bos.operators.utils.clients.hsm import get_components as get_hsm_components


LOGGER = logging.getLogger('bos.operators.filters.filters')


# Usable filters
class OR(DetailsFilter):
    def __init__(self, filters_a, filters_b) -> None:
        super().__init__()
        self.filters_a: List[Type[BaseFilter]] = filters_a
        self.filters_b: List[Type[BaseFilter]] = filters_b

    def _filter(self, components: List[dict]) -> List[dict]:
        results_a = copy.deepcopy(components)
        for f in self.filters_a:
            results_a = f.filter(results_a)
        results_b = copy.deepcopy(components)
        for f in self.filters_b:
            results_b = f.filter(results_b)
        results_a_dict = {component['id']: component for component in results_a}
        results_b_dict = {component['id']: component for component in results_b}
        results = {**results_a_dict, **results_b_dict}
        return list(results.values())


class BOSQuery(DetailsFilter):
    """git Gets all components from BOS that match the kwargs """
    INITIAL: bool = True

    def __init__(self, **kwargs) -> None:
        """
        Init for the BOSQuery filter
        kwargs corresponds to arguments for the BOS get_components method
        """
        super().__init__()
        self.kwargs = kwargs

    def _filter(self, components=None) -> List[dict]:
        return get_components(**self.kwargs)


class HSMEnabled(IDFilter):
    """ Returns all components that are in desired enabled state """
    def __init__(self, enabled: bool = True) -> None:
        super().__init__()
        self.enabled = enabled

    def _filter(self, components: List[str]) -> List[str]:
        components = get_hsm_components(components, enabled=self.enabled)
        return [component['ID'] for component in components['Components']]


class PowerState(IDFilter):
    """ Returns all components that are in desired power state """
    def __init__(self, state: str = 'on') -> None:
        super().__init__()
        self.state = state

    def _filter(self, components: List[str]) -> List[str]:
        response, _, _ = get_power_state(components, filtertype='show_{}'.format(self.state))
        return response[self.state]


class TimeSinceLastAction(LocalFilter):
    """ Returns all components whose last actions was over some time ago """
    def __init__(self, **kwargs) -> None:
        """
        Init for the TimeSinceLastAction filter
        kwargs corresponds to arguments for datetime.timedelta
        """
        super().__init__()
        self.kwargs = kwargs

    def _match(self, component: dict) -> bool:
        last_action_time = component.get('lastAction', {}).get('lastUpdated')
        now = datetime.utcnow()
        if not last_action_time or now > parser.parse(last_action_time) + timedelta(**self.kwargs):
            return True
        return False


class LastActionIs(LocalFilter):
    """ Returns with the specified last action(s) """
    def __init__(self, actions: str) -> None:
        super().__init__()
        self.actions = actions.split(',')

    def _match(self, component: dict) -> bool:
        last_action = component.get('lastAction', {}).get('action', '')
        if last_action in self.actions:
            return True
        return False
