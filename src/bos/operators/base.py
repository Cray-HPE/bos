#!/usr/bin/env python
# Copyright 2021-2022 Hewlett Packard Enterprise Development LP
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
"""
BOS Operator - A Python operator for the Boot Orchestration Service.
"""

from abc import ABC, abstractmethod
import logging
import threading
import os
import time
from typing import List, NoReturn, Type

from bos.operators.filters.base import BaseFilter
from bos.operators.utils.clients.bos.options import options
from bos.operators.utils.clients.bos import BOSClient
from bos.operators.utils.liveness.timestamp import Timestamp


LOGGER = logging.getLogger('bos.operators.base')


class BaseOperator(ABC):
    """
    An abstract class for all BOS operators.

    The following should be overridden:
    NAME - This field determines how the operator/action is logged in the components database.
    FILTERS - A list of all filters that are used to determine which components should be acted on.
        Includes the initial query for BOS components as the query also includes filtering.
    _act - This method is the action taken by the operator against target components. e.g. powering
        a component on or off.

    Any other method may also be overridden, but functionality such as error handling may be lost.
    """
    def __init__(self) -> NoReturn:
        self.bos_client = BOSClient()

    @property
    @abstractmethod
    def name(self) -> str:
        return 'Invalid Action Type'

    @property
    @abstractmethod
    def filters(self) -> List[Type[BaseFilter]]:
        return []

    def run(self) -> NoReturn:
        """
        The core method of the operator that periodically detects and acts on components.
        This includes updating the options and logging level, as well as exception handling and
        sleeping between passes.
        """
        while True:
            start_time = time.time()
            try:
                options.update()
                _update_log_level()
                self._run()
            except Exception as e:
                LOGGER.exception('Unhandled exception detected: {}'.format(e))

            try:
                sleep_time = options.polling_frequency - (time.time() - start_time)
                if sleep_time > 0:
                    time.sleep(sleep_time)
            except Exception as e:
                LOGGER.exception('Unhandled exception getting polling frequency: {}'.format(e))
                time.sleep(5)  # A small sleep for when exceptions getting the polling frequency

    def _run(self) -> None:
        """ A single pass of detecting and acting on components  """
        components = self._get_components()
        for component in components:  # Unset old errors components
            component['error'] = ''
        if not components:
            LOGGER.debug('Found 0 components that require action')
            return
        LOGGER.info('Found {} components that require action'.format(len(components)))
        components = self._act(components)
        self._update_database(components)

    def _get_components(self) -> List[dict]:
        """ Gets the list of all components that require actions  """
        components = []
        for f in self.filters:
            components = f.filter(components)
        return components

    @abstractmethod
    def _act(self, components: List[dict]) -> List[dict]:
        """ The action taken by the operator on target components """
        raise NotImplementedError()

    def _update_database(self, components: List[dict], additional_fields: dict = None) -> None:
        """
        Updates the BOS database for all components acted on by the operator
        Includes updating min_wait/max_wait, the last action, attempt count and error
        """
        data = []
        for component in components:
            patch = {
                'id': component['id'],
                'error': component['error']  # New error, or clearing out old error
            }
            if self.name:
                attempts = 1
                last_action = component.get('lastAction', {})
                if last_action.get('action') == self.name:
                    attempts = last_action.get('numAttempts', 1) + 1
                last_action_data = {
                    'action': self.name,
                    'numAttempts': attempts,
                }
                patch['lastAction'] = last_action_data

            if additional_fields:
                patch.update(additional_fields)
            data.append(patch)
        self.bos_client.components.update_components(data)


def _update_log_level() -> None:
    """ Updates the current logging level base on the value in the options database """
    try:
        if not options.logging_level:
            return
        new_level = logging.getLevelName(options.logging_level.upper())
        current_level = LOGGER.getEffectiveLevel()
        if current_level != new_level:
            LOGGER.log(current_level, 'Changing logging level from {} to {}'.format(
                logging.getLevelName(current_level), logging.getLevelName(new_level)))
            logger = logging.getLogger()
            logger.setLevel(new_level)
            LOGGER.log(new_level, 'Logging level changed from {} to {}'.format(
                logging.getLevelName(current_level), logging.getLevelName(new_level)))
    except Exception as e:
        LOGGER.error('Error updating logging level: {}'.format(e))


def _liveliness_heartbeat() -> NoReturn:
    """
    Periodically add a timestamp to disk; this allows for reporting of basic
    health at a minimum rate. This prevents the pod being marked as dead if
    a period of no events have been monitored from k8s for an extended
    period of time.
    """
    while True:
        Timestamp()
        time.sleep(10)


def _init_logging() -> None:
    """ Sets the format and initial log level for logging """
    log_format = "%(asctime)-15s - %(levelname)-7s - %(name)s - %(message)s"
    requested_log_level = os.environ.get('BOS_OPERATOR_LOG_LEVEL', 'INFO')
    log_level = logging.getLevelName(requested_log_level)

    if type(log_level) != int:
        LOGGER.warning('Log level %r is not valid. Falling back to INFO', requested_log_level)
        log_level = logging.INFO
    logging.basicConfig(level=log_level, format=log_format)


def main(operator: Type[BaseOperator]):
    """
    The main method for any operator type.
    Automatically handles logging and heartbeats as well as starting the operator.
    """
    _init_logging()
    heartbeat = threading.Thread(target=_liveliness_heartbeat, args=())
    heartbeat.start()

    op = operator()
    op.run()


if __name__ == '__main__':
    main(BaseOperator)
