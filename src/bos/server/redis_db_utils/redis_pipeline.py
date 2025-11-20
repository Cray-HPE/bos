#
# MIT License
#
# (C) Copyright 2019-2025 Hewlett Packard Enterprise Development LP
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
Database-related decorator definitions
"""

from collections.abc import Callable
import functools
import logging
from typing import Concatenate, Protocol

import redis


LOGGER = logging.getLogger(__name__)


class HasRedisClient(Protocol):
    """
    Protocol for classes that have a Redis client property
    (e.g. DBWrapper)
    """
    @property
    def client(self) -> redis.Redis: ...


def redis_pipeline[**P, C: HasRedisClient, R](
    method: Callable[Concatenate[C, redis.client.Pipeline, P], R]
) -> Callable[Concatenate[C, P], R]:
    """
    Decorator to put around DBWrapper methods that provides a Redis pipeline as the
    first argument to the function (inside of a context manager).
    """

    @functools.wraps(method)
    def wrapper(self: C, /, *args: P.args, **kwargs: P.kwargs) -> R:
        # Because C is bounded by the HasRedisClient protocol, we know that
        # self.client is a redis.Redis object
        with self.client.pipeline() as pipe:
            return method(self, pipe, *args, **kwargs)

    return wrapper
