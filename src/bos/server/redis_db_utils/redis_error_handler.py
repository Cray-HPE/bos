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
Redis error handler wrapper for use with endpoint controllers
"""

from collections.abc import Callable
import functools
import logging
from typing import ParamSpec, TypeVar

import connexion
from connexion.lifecycle import ConnexionResponse as CxResponse
import redis

from bos.common.utils import exc_type_msg

LOGGER = logging.getLogger(__name__)

P = ParamSpec('P')
R = TypeVar('R')

def redis_error_handler(func: Callable[P, R]) -> Callable[P, R|CxResponse]:
    """Decorator for returning better errors if Redis is unreachable"""

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R | CxResponse:
        try:
            if 'body' in kwargs:
                # Our get/patch functions don't take body, but the **kwargs
                # in the arguments to this wrapper cause it to get passed.
                del kwargs['body']
            return func(*args, **kwargs)
        except redis.exceptions.ConnectionError as e:
            LOGGER.error('Unable to connect to the Redis database: %s', exc_type_msg(e))
            return connexion.problem(
                status=503,
                title='Unable to connect to the Redis database',
                detail=str(e))

    return wrapper
