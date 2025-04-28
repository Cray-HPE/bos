#
# MIT License
#
# (C) Copyright 2024-2025 Hewlett Packard Enterprise Development LP
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
import re

from bos.common.utils import PROTOCOL

LOGGER = logging.getLogger(__name__)

SERVICE_NAME = 'cray-ims'
IMS_VERSION = 'v3'
BASE_ENDPOINT = f"{PROTOCOL}://{SERVICE_NAME}/{IMS_VERSION}"

# Making minimal assumptions about the IMS ID itself, this pattern just makes sure that the
# S3 key is some string, then a /, then at least one more character.
IMS_S3_KEY_RE = r'^([^/]+)/.+'
IMS_S3_KEY_RE_PROG = re.compile(IMS_S3_KEY_RE)

# If an IMS image does not have the arch field, default to x86_64 for purposes of
# backward-compatibility
DEFAULT_IMS_IMAGE_ARCH = 'x86_64'
