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

from bos.common.utils import exc_type_msg
from bos.common.clients.s3 import S3Url

from .defs import IMS_S3_KEY_RE_PROG, DEFAULT_IMS_IMAGE_ARCH, LOGGER


def get_ims_id_from_s3_url(s3_url: S3Url) -> str | None:
    """
    If the s3_url matches the expected format of an IMS image path, then return the IMS image ID.
    Otherwise return None.
    """
    match = IMS_S3_KEY_RE_PROG.match(s3_url.key)
    if match is None:
        return None
    try:
        return match.group(1)
    except IndexError:
        return None


def get_arch_from_image_data(image_data: dict) -> str:
    """
    Returns the value of the 'arch' field in the image data
    If it is not present, logs a warning and returns the default value
    """
    try:
        arch = image_data['arch']
    except KeyError:
        LOGGER.warning(
            "Defaulting to '%s' because 'arch' not set in IMS image data: %s",
            DEFAULT_IMS_IMAGE_ARCH, image_data)
        return DEFAULT_IMS_IMAGE_ARCH
    except Exception as err:
        LOGGER.error("Unexpected error parsing IMS image data (%s): %s",
                     exc_type_msg(err), image_data)
        raise
    if arch:
        return arch
    LOGGER.warning(
        "Defaulting to '%s' because 'arch' set to null value in IMS image data: %s",
        DEFAULT_IMS_IMAGE_ARCH, image_data)
    return DEFAULT_IMS_IMAGE_ARCH
