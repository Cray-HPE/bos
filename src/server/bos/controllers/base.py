# Cray-provided base controllers for the Boot Orchestration Service
# Copyright 2019, Cray Inc. All Rights Reserved.


from bos.controllers.v1 import base as v1_base

import logging
LOGGER = logging.getLogger('bos.controllers.base')


def root_get():
    """ Get a list of supported versions """
    LOGGER.info('in get_versions')
    versions = [
        v1_base.calc_version(details=False),
    ]
    return versions, 200
