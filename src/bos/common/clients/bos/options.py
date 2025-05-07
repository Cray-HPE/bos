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
import logging
import json
from typing import cast

import requests
from requests.exceptions import HTTPError
from requests.exceptions import ConnectionError as RequestsConnectionError
from urllib3.exceptions import MaxRetryError

from bos.common.clients.bos.base import BASE_BOS_ENDPOINT
from bos.common.options import OptionsCache
from bos.common.types.options import OptionsDict
from bos.common.utils import exc_type_msg, retry_session_get

LOGGER = logging.getLogger(__name__)
__name = __name__.lower().rsplit('.', maxsplit=1)[-1]
ENDPOINT = f"{BASE_BOS_ENDPOINT}/{__name}"


class Options(OptionsCache):
    """
    Handler for reading configuration options from the BOS API

    This caches the options so that frequent use of these options do not all
    result in network calls.
    """

    def _get_options(self, session: requests.Session | None = None) -> OptionsDict:
        """Retrieves the current options from the BOS api"""
        LOGGER.debug("GET %s", ENDPOINT)
        try:
            with retry_session_get(ENDPOINT, session=session) as response:
                response.raise_for_status()
                return cast(OptionsDict, json.loads(response.text))
        except (RequestsConnectionError, MaxRetryError) as e:
            LOGGER.error("Unable to connect to BOS: %s", exc_type_msg(e))
        except HTTPError as e:
            LOGGER.error("Unexpected response from BOS: %s", exc_type_msg(e))
        except json.JSONDecodeError as e:
            LOGGER.error("Non-JSON response from BOS: %s", exc_type_msg(e))
        return OptionsDict()


options = Options(update_on_create=False)
