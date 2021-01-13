#!/usr/bin/env python3
# Boot Orchestration Service (BOS) Server API Main
# Copyright 2019-2020 Cray Inc.

import logging

import connexion

from bos import specialized_encoder

LOGGER = logging.getLogger('bos.__main__')


def create_app():
    logging.basicConfig(level=logging.DEBUG)
    LOGGER.info("BOS server starting.")
    app = connexion.App(__name__, specification_dir='./openapi/')
    app.app.json_encoder = specialized_encoder.MetadataEncoder
    app.add_api('openapi.yaml',
                arguments={'title':
                           'Cray Boot Orchestration Service'},
                base_path='/')
    return app


app = create_app()


if __name__ == '__main__':
    app.run()
