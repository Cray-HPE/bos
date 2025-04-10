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
BOS Operator - A Python operator for the Boot Orchestration Service.
"""

from abc import ABC, abstractmethod
from collections.abc import Generator
from contextlib import ExitStack
import itertools
import logging
import threading
import os
import time
from types import TracebackType
from typing import NoReturn, Self

from bos.common.clients.bos import BOSClient
from bos.common.clients.bos.options import options
from bos.common.clients.bss import BSSClient
from bos.common.clients.cfs import CFSClient
from bos.common.clients.hsm import HSMClient
from bos.common.clients.ims import IMSClient
from bos.common.clients.pcs import PCSClient
from bos.common.utils import exc_type_msg, update_log_level
from bos.common.types.components import ComponentRecord
from bos.common.values import Status
from bos.operators.filters import BOSQuery, DesiredConfigurationSetInCFS, HSMState
from bos.operators.filters.base import BaseFilter
from bos.operators.utils.liveness.timestamp import Timestamp

LOGGER = logging.getLogger(__name__)
MAIN_THREAD = threading.current_thread()


class BaseOperatorException(Exception):
    pass


class MissingSessionData(BaseOperatorException):
    """
    Operators are expected to update the session data, if they are updating a component's
    desired state.
    """


class ApiClients:
    """
    Context manager to provide API clients to BOS operators.
    Essentially, it uses an ExitStack context manager to manage the API clients.
    """

    def __init__(self) -> None:
        self.bos = BOSClient()
        self.bss = BSSClient()
        self.cfs = CFSClient()
        self.hsm = HSMClient()
        self.ims = IMSClient()
        self.pcs = PCSClient()
        self._stack = ExitStack()

    def __enter__(self) -> Self:
        """
        Enter context for all API clients
        """
        self._stack.enter_context(self.bos)
        self._stack.enter_context(self.bss)
        self._stack.enter_context(self.cfs)
        self._stack.enter_context(self.hsm)
        self._stack.enter_context(self.ims)
        self._stack.enter_context(self.pcs)
        return self

    def __exit__(self, exc_type: type[BaseException] | None,
                 exc_val: BaseException | None,
                 exc_tb: TracebackType | None) -> bool | None:
        """
        Exit context on the exit stack, which will take care of exiting
        context for all of the API clients.
        """
        return self._stack.__exit__(exc_type, exc_val, exc_tb)


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

    def __init__(self) -> None:
        self.__max_batch_size = 0
        self._client: ApiClients | None = None

    @property
    def client(self) -> ApiClients:
        """
        Return the ApiClients object for this operator.
        If it is not initialized, raise a ValueError (this should never be the case).
        """
        if self._client is None:
            raise ValueError("Attempted to access uninitialized API client")
        return self._client

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def filters(self) -> list[BaseFilter]: ...

    def BOSQuery(self, bos_client: BOSClient | None = None, **kwargs) -> BOSQuery:
        """
        Shortcut to get a BOSQuery filter with the bos_client for this operator
        """
        return BOSQuery(bos_client=self.client.bos if bos_client is None else bos_client,
                        **kwargs)

    def DesiredConfigurationSetInCFS(self, cfs_client: CFSClient | None = None,
                                     **kwargs) -> DesiredConfigurationSetInCFS:
        """
        Shortcut to get a DesiredConfigurationSetInCFS filter with the cfs_client for this operator
        """
        return DesiredConfigurationSetInCFS(
                cfs_client=self.client.cfs if cfs_client is None else cfs_client, **kwargs)

    def HSMState(self, hsm_client: HSMClient | None = None, **kwargs) -> HSMState:
        """
        Shortcut to get a HSMState filter with the bos_client for this operator
        """
        return HSMState(hsm_client=self.client.hsm if hsm_client is None else hsm_client,
                        **kwargs)

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
                with ApiClients() as _client:
                    self._client = _client
                    self._run()
            except Exception as e:
                LOGGER.exception('Unhandled exception detected: %s', e)
            finally:
                # We have exited the context manager, so make sure to reset the client
                # value for this operator
                self._client = None

            try:
                sleep_time = getattr(options, self.frequency_option) - (
                    time.time() - start_time)
                if sleep_time > 0:
                    time.sleep(sleep_time)
            except Exception as e:
                LOGGER.exception(
                    'Unhandled exception getting polling frequency: %s', e)
                time.sleep(
                    5
                )  # A small sleep for when exceptions getting the polling frequency

    @property
    def max_batch_size(self) -> int:
        max_batch_size = options.max_component_batch_size
        if max_batch_size != self.__max_batch_size:
            LOGGER.info("max_component_batch_size option set to %d",
                        max_batch_size)
            self.__max_batch_size = max_batch_size
        return max_batch_size

    def _chunk_components(self,
                          components: list[ComponentRecord]) -> Generator[list[ComponentRecord],
                                                                          None, None]:
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

    def _run_on_chunk(self, components: list[ComponentRecord]) -> None:
        """
        Acts on a chunk of components
        """
        LOGGER.debug("Processing %d components", len(components))
        # Only check for failed components if we track retries for this operator
        if self.retry_attempt_field:
            components = self._handle_failed_components(components)
            if not components:
                LOGGER.debug(
                    'After removing components that exceeded their retry limit, 0 '
                    'components require action')
                return
        for component in components:  # Unset old errors components
            component['error'] = ''
        try:
            components = self._act(components)
        except Exception as e:
            LOGGER.error(
                "An unhandled exception was caught while trying to act on components: %s",
                e,
                exc_info=True)
            for component in components:
                component["error"] = str(e)
        self._update_database(components)

    def _get_components(self) -> list[ComponentRecord]:
        """ Gets the list of all components that require actions  """
        components = []
        for f in self.filters:
            components = f.filter(components)
        return components

    def _handle_failed_components(self, components: list[ComponentRecord]) -> list[ComponentRecord]:
        """ Marks components failed if the retry limits are exceeded """
        if not components:
            # If we have been passed an empty list, there is nothing to do.
            LOGGER.debug("_handle_failed_components: No components to handle")
            return []
        failed_components = []
        good_components = [
        ]  # Any component that isn't determined to be in a failed state
        for component in components:
            num_attempts = component.get('event_stats',
                                         {}).get(self.retry_attempt_field, 0)
            retries = int(
                component.get('retry_policy', options.default_retry_policy))
            if retries != -1 and num_attempts >= retries:
                # This component has hit its retry limit
                failed_components.append(component)
            else:
                good_components.append(component)
        self._update_database_for_failure(failed_components)
        return good_components

    @abstractmethod
    def _act(self, components: list[ComponentRecord]) -> list[ComponentRecord]:
        """ The action taken by the operator on target components """

    def _update_database(self,
                         components: list[ComponentRecord],
                         additional_fields: dict | None = None) -> None:
        """
        Updates the BOS database for all components acted on by the operator
        Includes updating the last action, attempt count and error
        """
        if not components:
            # If we have been passed an empty list, there is nothing to do.
            LOGGER.debug(
                "_update_database: No components require database updates")
            return
        data = []
        for component in components:
            patch = {
                'id': component['id'],
                'error':
                component['error']  # New error, or clearing out old error
            }
            if self.name:
                last_action_data = {'action': self.name, 'failed': False}
                patch['last_action'] = last_action_data
            if self.retry_attempt_field:
                event_stats_data = {
                    self.retry_attempt_field:
                    component.get('event_stats', {}).get(
                        self.retry_attempt_field, 0) + 1
                }
                patch['event_stats'] = event_stats_data

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
        self.client.bos.components.update_components(data)

    def _preset_last_action(self, components: list[ComponentRecord]) -> None:
        # This is done to eliminate the window between performing an action and marking the
        # nodes as acted
        # e.g. nodes could be powered-on without the correct power-on last action, causing
        # status problems
        if not self.name:
            return
        if not components:
            # If we have been passed an empty list, there is nothing to do.
            LOGGER.debug(
                "_preset_last_action: No components require database updates")
            return
        data = []
        for component in components:
            patch = {'id': component['id'], 'error': component['error']}
            if self.name:
                last_action_data = {'action': self.name, 'failed': False}
                patch['last_action'] = last_action_data
            data.append(patch)
        LOGGER.info('Found %d components that require updates', len(data))
        LOGGER.debug('Updated components: %s', data)
        self.client.bos.components.update_components(data)

    def _update_database_for_failure(self, components: list[ComponentRecord]) -> None:
        """
        Updates the BOS database for all components the operator believes have failed
        """
        if not components:
            # If we have been passed an empty list, there is nothing to do.
            LOGGER.debug(
                "_update_database_for_failure: No components require database updates"
            )
            return
        data = []
        for component in components:
            patch = {
                'id': component['id'],
                'status': {
                    'status_override': Status.failed
                }
            }
            if not component['error']:
                patch['error'] = (
                    'The retry limit has been hit for this component, '
                    'but no services have reported specific errors')
            data.append(patch)
        LOGGER.info('Found %d components that require updates', len(data))
        LOGGER.debug('Updated components: %s', data)
        self.client.bos.components.update_components(data)


def chunk_components(components: list[ComponentRecord],
                     max_batch_size: int) -> Generator[list[ComponentRecord], None, None]:
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
        update_log_level(options.logging_level)
    except Exception as e:
        LOGGER.error('Error updating logging level: %s', exc_type_msg(e))


def _liveliness_heartbeat() -> NoReturn:
    """
    Periodically add a timestamp to disk; this allows for reporting of basic
    health at a minimum rate. This prevents the pod being marked as dead if
    a period of no events have been monitored from k8s for an extended
    period of time.
    """
    while True:
        if not MAIN_THREAD.is_alive():
            # All hope abandon ye who enter here
            return
        Timestamp()
        time.sleep(10)


def _init_logging() -> None:
    """ Sets the format and initial log level for logging """
    log_format = "%(asctime)-15s - %(levelname)-7s - %(name)s - %(message)s"
    requested_log_level = os.environ.get('BOS_OPERATOR_LOG_LEVEL', 'INFO')
    log_level = logging.getLevelName(requested_log_level)

    if not isinstance(log_level, int):
        LOGGER.warning('Log level %r is not valid. Falling back to INFO',
                       requested_log_level)
        log_level = logging.INFO
    logging.basicConfig(level=log_level, format=log_format)


def main(operator: type[BaseOperator]):
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
