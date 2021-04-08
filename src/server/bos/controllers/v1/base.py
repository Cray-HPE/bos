# Cray-provided base controllers for the Boot Orchestration Service
# Copyright 2019-2021, Hewlett Packard Enterprise Development LP

import os.path
import logging
import subprocess
import yaml

from bos.controllers.utils import url_for
from bos.models import Version, Link
from os import path


LOGGER = logging.getLogger('bos.controllers.v1.base')


def calc_version(details):
    links = [
        Link(
            rel='self',
            href=url_for('.bos_controllers_base_root_get'),
        ),
    ]

    if details:
        links.extend([
            Link(
                rel='versions',
                href=url_for('.bos_controllers_v1_base_v1_get'),
            ),
        ])

    # parse open API spec file from docker image or local repository
    openapispec_f = '/app/lib/server/bos/openapi/openapi.yaml'
    if not path.exists(openapispec_f):
        repo_root_dir = subprocess.Popen(
            ['git', 'rev-parse', '--show-toplevel'],
            stdout=subprocess.PIPE).communicate()[0].rstrip().decode('utf-8')
        openapispec_f = repo_root_dir + '/src/server/bos/openapi/openapi.yaml'
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
