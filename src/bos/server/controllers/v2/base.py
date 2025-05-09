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
from typing import Literal

import yaml

from bos.common.utils import exc_type_msg
from bos.server.controllers.utils import url_for
from bos.server.models import Version, Link
from bos.server.options import update_server_log_level

LOGGER = logging.getLogger(__name__)


def calc_version(details: bool) -> Version:
    links = [
        Link(
            rel='self',
            href=url_for('.bos_server_controllers_base_root_get'),
        ),
    ]

    if details:
        links.extend([
            Link(
                rel='versions',
                href=url_for('.bos_server_controllers_v2_base_get_v2'),
            ),
        ])

    # parse open API spec file from docker image or local repository
    openapispec_f = '/app/lib/bos/server/openapi/openapi.yaml'
    try:
        with open(openapispec_f, 'r') as f:
            openapispec_map = yaml.safe_load(f)
        major, minor, patch = openapispec_map['info']['version'].split('.')
        return Version(major=major, minor=minor, patch=patch, links=links)
    except IOError as e:
        LOGGER.exception('error opening "%s" file: %s', openapispec_f,
                         exc_type_msg(e))
        raise


def get_v2() -> tuple[Version, Literal[200]]:
    # For all entry points into the server, first refresh options and update log level if needed
    update_server_log_level()

    LOGGER.debug("GET /v2 invoked get_v2")
    return calc_version(details=True), 200


def get_version_v2() -> tuple[Version, Literal[200]]:
    # For all entry points into the server, first refresh options and update log level if needed
    update_server_log_level()

    LOGGER.debug("GET /v2/version invoked get_version_v2")
    return calc_version(details=True), 200
