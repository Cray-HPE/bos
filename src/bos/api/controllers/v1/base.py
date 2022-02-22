# Cray-provided base controllers for the Boot Orchestration Service
# Copyright 2019-2021 Hewlett Packard Enterprise Development LP
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

import logging
import subprocess
import yaml

from bos.api.controllers.utils import url_for
from bos.api.models import Version, Link
from os import path

LOGGER = logging.getLogger('bos.controllers.v1.base')


def calc_version(details):
    links = [
        Link(
            rel='self',
            href=url_for('.bos_api_controllers_base_root_get'),
        ),
    ]

    if details:
        links.extend([
            Link(
                rel='versions',
                href=url_for('.bos_api_controllers_v1_base_v1_get'),
            ),
        ])

    # parse open API spec file from docker image or local repository
    openapispec_f = '/app/lib/bos/api/openapi/openapi.yaml'
    if not path.exists(openapispec_f):
        repo_root_dir = subprocess.Popen(
            ['git', 'rev-parse', '--show-toplevel'],
            stdout=subprocess.PIPE).communicate()[0].rstrip().decode('utf-8')
        openapispec_f = repo_root_dir + '/src/bos/api/openapi/openapi.yaml'
    f = None
    try:
        f = open(openapispec_f, 'r')
    except IOError as e:
        LOGGER.debug('error opening openapi.yaml file: %s' % e)

    openapispec_map = yaml.safe_load(f)
    f.close()
    major, minor, patch = openapispec_map['info']['version'].split('.')
    return Version(
        major=major,
        minor=minor,
        patch=patch,
        links=links,
    )


def v1_get():
    LOGGER.info('in v1_get')
    return calc_version(details=True), 200


def v1_get_version():
    LOGGER.info('in v1_get_version')
    return calc_version(details=True), 200
