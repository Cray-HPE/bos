#
# MIT License
#
# (C) Copyright 2024 Hewlett Packard Enterprise Development LP
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
from requests.exceptions import HTTPError

from bos.common.utils import compact_response_text, exc_type_msg, requests_retry_session, PROTOCOL

SERVICE_NAME = 'cray-ims'
IMS_VERSION = 'v3'
BASE_ENDPOINT = f"{PROTOCOL}://{SERVICE_NAME}/{IMS_VERSION}"
IMAGES_ENDPOINT = f"{BASE_ENDPOINT}/images"

LOGGER = logging.getLogger('bos.operators.utils.clients.ims')
IMS_TAG_OPERATIONS = ['set', 'remove']

class TagFailure(Exception):
    pass

def patch_image(image_id, data, session=None):
    if not data:
        LOGGER.warning("patch_image called without data; returning without action.")
        return
    if not session:
        session = requests_retry_session()
    LOGGER.debug("PATCH %s with body=%s", IMAGES_ENDPOINT, data)
    response = session.patch(f"{IMAGES_ENDPOINT}/{image_id}", json=data)
    LOGGER.debug("Response status code=%d, reason=%s, body=%s", response.status_code,
                 response.reason, compact_response_text(response.text))
    try:
        response.raise_for_status()
    except HTTPError as err:
        LOGGER.error("Failed asking IMS to tag image: %s", exc_type_msg(err))
        raise

def tag_image(image_id: str, operation: str, key: str, value: str = None, session=None) -> None:
    if operation not in IMS_TAG_OPERATIONS:
        msg = f"{operation} not valid. Expecting one of {IMS_TAG_OPERATIONS}"
        LOGGER.error(msg)
        raise TagFailure(msg)

    if not key:
        msg = f"key must exist: {key}"
        LOGGER.error(msg)
        raise TagFailure(msg)

    if value:
        LOGGER.debug("Patching image %s %sing key: %s value: %s", image_id, operation, key, value)
    else:
        LOGGER.debug("Patching image %s %sing key: %s", image_id, operation, key)

    if not session:
        session = requests_retry_session()

    data = {
        "metadata": {
            "operation": operation,
            "key": key,
            "value": value
            }
    }
    patch_image(image_id=image_id, data=data, session=session)
