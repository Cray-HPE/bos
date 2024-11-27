#
# MIT License
#
# (C) Copyright 2020-2022, 2024 Hewlett Packard Enterprise Development LP
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
import tracemalloc
import weakref
from requests.packages.urllib3.util.retry import Retry # pylint: disable=import-error

LOGGER = logging.getLogger(__name__)

class RetryWithLogs(Retry):
    """
    A urllib3.utils.Retry adapter that allows us to modify the behavior of
    what happens during retry. By overwriting the superclassed method increment, we
    can provide the user with information about how frequently we are reattempting
    an endpoint.

    Providing this feedback to the user allows us to dramatically increase the number
    of retry operations within the provided call to an attempted upstream API, and
    gives users a chance to intervene on behalf of the slower upstream service. This
    behavior is consistent with existing retry behavior that is expected by all of our
    API interactions, as well, gives us a more immediate sense of feedback for overall
    system instability and network congestion.
    """

    def __init__(self, *args, **kwargs):
        # Save a copy of upstack callback to the side; this is the context we provide
        # for recursively instantiated instances of the Retry model
        self._snapshot = tracemalloc.take_snapshot() if tracemalloc.is_tracing() else None
        _callback = kwargs.pop('callback', None)
        if _callback is None:
            self._callback = None
        elif isinstance(_callback, weakref.CallableProxyType):
            self._callback = _callback
        else:
            self._callback = weakref.proxy(_callback)
        kwargs.pop('callback', None)
        super(RetryWithLogs, self).__init__(*args, **kwargs)

    def new(self, *args, **kwargs):
        # Newly created instances should have a history of callbacks made.
        kwargs['callback'] = self._callback
        return super(RetryWithLogs, self).new(*args, **kwargs)

    def increment(self, method, url, *args, **kwargs):
        pool = kwargs['_pool']
        endpoint = "%s://%s%s" % (pool.scheme, pool.host, url)
        try:
            response = kwargs['response']
            LOGGER.warning("Previous %s attempt on '%s' resulted in %s response.", method, endpoint, response.status)
            LOGGER.info("Reattempting %s request for '%s'", method, endpoint)
        except KeyError:
            LOGGER.info("Reattempting %s request for '%s'", method, endpoint)
        if self._callback:
            try:
                self._callback(url)
            except Exception:
                # This is a general except block
                LOGGER.exception("Callback to '%s' raised an exception, ignoring.", url)
        return super(RetryWithLogs, self).increment(method, url, *args, **kwargs)
