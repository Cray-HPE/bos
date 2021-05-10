#!/usr/bin/env python3
# Boot Orchestration Service (BOS) Server API Main
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
