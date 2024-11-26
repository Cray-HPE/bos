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
"""
BOS Operator - A Python operator for the Boot Orchestration Service.
"""

from abc import ABC, abstractmethod
import itertools
import logging
import threading
import os
import time
import tracemalloc
from typing import Generator, List, NoReturn, Type

from bos.common.utils import exc_type_msg
from bos.common.values import Status
from bos.operators.filters.base import BaseFilter
from bos.operators.utils.clients.bos.options import options
from bos.operators.utils.clients.bos import BOSClient
from bos.operators.utils.liveness.timestamp import Timestamp

LOGGER = logging.getLogger('bos.operators.base')
MAIN_THREAD = threading.current_thread()


#tracemalloc.start()

class BaseOperatorException(Exception):
    pass


class MissingSessionData(BaseOperatorException):
    """
    Operators are expected to update the session data, if they are updating a component's
    desired state.
    """


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

    retry_attempt_field = ""
    frequency_option = "polling_frequency"

    def __init__(self) -> NoReturn:
        self.bos_client = BOSClient()
        self.__max_batch_size = 0

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
                LOGGER.exception('Unhandled exception detected: %s', e)

            try:
                sleep_time = getattr(options, self.frequency_option) - (time.time() - start_time)
                if sleep_time > 0:
                    time.sleep(sleep_time)
            except Exception as e:
                LOGGER.exception('Unhandled exception getting polling frequency: %s', e)
                time.sleep(5)  # A small sleep for when exceptions getting the polling frequency

    @property
    def max_batch_size(self) -> int:
        max_batch_size = options.max_component_batch_size
        if max_batch_size != self.__max_batch_size:
            LOGGER.info("max_component_batch_size option set to %d", max_batch_size)
            self.__max_batch_size = max_batch_size
        return max_batch_size

    def _chunk_components(self, components: List[dict]) -> Generator[List[dict], None, None]:
        """
        Break up the components into groups of no more than max_batch_size nodes,
        and yield each group in turn.
        If the max size is set to 0, just yield the entire list.
        """
        yield from chunk_components(components, self.max_batch_size)

    def _run(self) -> None:
        """ A single pass of detecting and acting on components  """
        components = self._get_components()
        if not components:
            LOGGER.debug('Found 0 components that require action')
            return
        LOGGER.info('Found %d components that require action', len(components))
        for chunk in self._chunk_components(components):
            self._run_on_chunk(chunk)

    def _run_on_chunk(self, components: List[dict]) -> None:
        """
        Acts on a chunk of components
        """
        LOGGER.debug("Processing %d components", len(components))
        # Only check for failed components if we track retries for this operator
        if self.retry_attempt_field:
            components = self._handle_failed_components(components)
            if not components:
                LOGGER.debug('After removing components that exceeded their retry limit, 0 '
                             'components require action')
                return
        for component in components:  # Unset old errors components
            component['error'] = ''
        try:
            components = self._act(components)
        except Exception as e:
            LOGGER.error("An unhandled exception was caught while trying to act on components: %s",
                         e, exc_info=True)
            for component in components:
                component["error"] = str(e)
        self._update_database(components)

    def _get_components(self) -> List[dict]:
        """ Gets the list of all components that require actions  """
        components = []
        for f in self.filters:
            components = f.filter(components)
        return components

    def _handle_failed_components(self, components: List[dict]) -> List[dict]:
        """ Marks components failed if the retry limits are exceeded """
        if not components:
            # If we have been passed an empty list, there is nothing to do.
            LOGGER.debug("_handle_failed_components: No components to handle")
            return []
        failed_components = []
        good_components = []  # Any component that isn't determined to be in a failed state
        for component in components:
            num_attempts = component.get('event_stats', {}).get(self.retry_attempt_field, 0)
            retries = int(component.get('retry_policy', options.default_retry_policy))
            if retries != -1 and num_attempts >= retries:
                # This component has hit its retry limit
                failed_components.append(component)
            else:
                good_components.append(component)
        self._update_database_for_failure(failed_components)
        return good_components

    @abstractmethod
    def _act(self, components: List[dict]) -> List[dict]:
        """ The action taken by the operator on target components """
        raise NotImplementedError()

    def _update_database(self, components: List[dict], additional_fields: dict=None) -> None:
        """
        Updates the BOS database for all components acted on by the operator
        Includes updating the last action, attempt count and error
        """
        if not components:
            # If we have been passed an empty list, there is nothing to do.
            LOGGER.debug("_update_database: No components require database updates")
            return
        data = []
        for component in components:
            patch = {
                'id': component['id'],
                'error': component['error']  # New error, or clearing out old error
            }
            if self.name:
                last_action_data = {
                    'action': self.name,
                    'failed': False
                }
                patch['last_action'] = last_action_data
            if self.retry_attempt_field:
                event_stats_data = {
                    self.retry_attempt_field: component.get(
                                                'event_stats',
                                                {}
                                              ).get(self.retry_attempt_field, 0) + 1
                }
                patch['event_stats']  = event_stats_data

            if additional_fields:
                patch.update(additional_fields)

            # When updating a component's desired state, operators
            # are expected to provide session data as a hacky way to prove
            # that they are operators. If they do not provide it, then the
            # session is incorrectly blanked.
            if 'desired_state' in patch and 'session' not in patch:
                raise MissingSessionData
            data.append(patch)
        LOGGER.info('Found %d components that require updates', len(data))
        LOGGER.debug('Updated components: %s', data)
        self.bos_client.components.update_components(data)

    def _preset_last_action(self, components: List[dict]) -> None:
        # This is done to eliminate the window between performing an action and marking the
        # nodes as acted
        # e.g. nodes could be powered-on without the correct power-on last action, causing
        # status problems
        if not self.name:
            return
        if not components:
            # If we have been passed an empty list, there is nothing to do.
            LOGGER.debug("_preset_last_action: No components require database updates")
            return
        data = []
        for component in components:
            patch = {
                'id': component['id'],
                'error': component['error']
            }
            if self.name:
                last_action_data = {
                    'action': self.name,
                    'failed': False
                }
                patch['last_action'] = last_action_data
            data.append(patch)
        LOGGER.info('Found %d components that require updates', len(data))
        LOGGER.debug('Updated components: %s', data)
        self.bos_client.components.update_components(data)

    def _update_database_for_failure(self, components: List[dict]) -> None:
        """
        Updates the BOS database for all components the operator believes have failed
        """
        if not components:
            # If we have been passed an empty list, there is nothing to do.
            LOGGER.debug("_update_database_for_failure: No components require database updates")
            return
        data = []
        for component in components:
            patch = {
                'id': component['id'],
                'status': {'status_override': Status.failed}
            }
            if not component['error']:
                patch['error'] = ('The retry limit has been hit for this component, '
                                  'but no services have reported specific errors')
            data.append(patch)
        LOGGER.info('Found %d components that require updates', len(data))
        LOGGER.debug('Updated components: %s', data)
        self.bos_client.components.update_components(data)


def chunk_components(components: List[dict],
                     max_batch_size: int) -> Generator[List[dict], None, None]:
    """
    Break up the components into groups of no more than max_batch_size nodes,
    and yield each group in turn.
    If the max size is set to 0, just yield the entire list.
    """
    chunk_size = max_batch_size if max_batch_size > 0 else len(components)
    yield from itertools.batched(components, chunk_size)


def _update_log_level() -> None:
    """ Updates the current logging level base on the value in the options database """
    try:
        if not options.logging_level:
            return
        new_level = logging.getLevelName(options.logging_level.upper())
        current_level = LOGGER.getEffectiveLevel()
        if current_level != new_level:
            LOGGER.log(current_level, 'Changing logging level from %s to %s',
                       logging.getLevelName(current_level), new_level)
            logger = logging.getLogger()
            logger.setLevel(new_level)
            LOGGER.log(new_level, 'Logging level changed from %s to %s',
                       logging.getLevelName(current_level), new_level)
    except Exception as e:
        LOGGER.error('Error updating logging level: %s', exc_type_msg(e))


def take_show_snapshot(last_snapshot=None):
    snapshot = tracemalloc.take_snapshot() 
    top_stats = snapshot.statistics('lineno') 
  
    howmany=50
    for ind, stat in enumerate(top_stats[:howmany]):
        LOGGER.info("tracemalloc top %d: %s", ind, stat)

    if last_snapshot is not None:
        top_diff = snapshot.compare_to(last_snapshot, 'lineno')
        for ind, stat in enumerate(top_diff[:howmany]):
            LOGGER.info("tracemalloc top diff %d: %s", ind, stat)
    return snapshot


def _liveliness_heartbeat() -> NoReturn:
    """
    Periodically add a timestamp to disk; this allows for reporting of basic
    health at a minimum rate. This prevents the pod being marked as dead if
    a period of no events have been monitored from k8s for an extended
    period of time.
    """
    last_snapshot = take_show_snapshot()
    while True:
        if not MAIN_THREAD.is_alive():
            # All hope abandon ye who enter here
            return
        Timestamp()
        time.sleep(0.1)
        last_snapshot = take_show_snapshot(last_snapshot)


def _init_logging() -> None:
    """ Sets the format and initial log level for logging """
    log_format = "%(asctime)-15s - %(levelname)-7s - %(name)s - %(message)s"
    requested_log_level = os.environ.get('BOS_OPERATOR_LOG_LEVEL', 'INFO')
    log_level = logging.getLevelName(requested_log_level)

    if not isinstance(log_level, int):
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
