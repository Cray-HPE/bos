#
# MIT License
#
# (C) Copyright 2021-2022, 2024-2025 Hewlett Packard Enterprise Development LP
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
from typing import Literal, cast

from connexion.lifecycle import ConnexionResponse

from bos.common.types.options import OptionsDict
from bos.common.utils import exc_type_msg
from bos.server import redis_db_utils as dbutils
from bos.server.controllers.utils import _400_bad_request
from bos.server.options import DB, get_options, update_server_log_level
from bos.server.utils import get_request_json

LOGGER = logging.getLogger(__name__)

@dbutils.redis_error_handler
def get_v2_options() -> tuple[OptionsDict, Literal[200]]:
    """Used by the GET /options API operation"""
    # For all entry points into the server, first refresh options and update log level if needed
    update_server_log_level()

    LOGGER.debug("GET /v2/options invoked get_v2_options")
    return get_options(), 200


@dbutils.redis_error_handler
def patch_v2_options() -> tuple[OptionsDict, Literal[200]] | ConnexionResponse:
    """Used by the PATCH /options API operation"""
    # For all entry points into the server, first refresh options and update log level if needed
    update_server_log_level()

    LOGGER.debug("PATCH /v2/options invoked patch_v2_options")
    try:
        patch_data = cast(OptionsDict, get_request_json())
    except Exception as err:
        LOGGER.error("Error parsing PATCH request data: %s", exc_type_msg(err))
        return _400_bad_request(f"Error parsing the data provided: {err}")

    options = get_options()
    options.update(patch_data)
    DB.put_options(options)
    if "logging_level" in patch_data:
        update_server_log_level()
    return options, 200
