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
import os
import logging

PROTOCOL = 'https'
API_GATEWAY_DNS_NAME = os.environ.get('API_GATEWAY_HOST', 'api-gw-service-nmn.local')
SERVICE = 'bos'
API_VERSION = 'v2'
ENDPOINT = f'{PROTOCOL}://{API_GATEWAY_DNS_NAME}/apis/{SERVICE}/{API_VERSION}'


class BOSException(Exception):
    """
    A Base class that all custom Exceptions from this
    project inherits from.
    """


# Setup project level loggging options
LOGGER = logging.getLogger(__name__)
