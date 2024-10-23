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
import re
from typing import cast, Literal, Optional, Required, TypedDict

from requests import HTTPError
from requests import Session as RequestsSession

from bos.common.types import JsonDict
from bos.common.utils import compact_response_text, exc_type_msg, requests_retry_session, PROTOCOL
from bos.operators.utils.clients.s3 import S3Url

SERVICE_NAME = 'cray-ims'
IMS_VERSION = 'v3'
BASE_ENDPOINT = f"{PROTOCOL}://{SERVICE_NAME}/{IMS_VERSION}"
IMAGES_ENDPOINT = f"{BASE_ENDPOINT}/images"

LOGGER = logging.getLogger('bos.operators.utils.clients.ims')
IMS_TAG_OPERATIONS = {'set', 'remove'}
ImsTagOperation = Literal['set', 'remove']

# Making minimal assumptions about the IMS ID itself, this pattern just makes sure that the
# S3 key is some string, then a /, then at least one more character.
IMS_S3_KEY_RE = r'^([^/]+)/.+'
IMS_S3_KEY_RE_PROG = re.compile(IMS_S3_KEY_RE)

ImsImageArch = Literal['aarch64', 'x86_64']

# If an IMS image does not have the arch field, default to x86_64 for purposes of
# backward-compatibility
DEFAULT_IMS_IMAGE_ARCH = cast(ImsImageArch, 'x86_64')


class ImsImagePatchMetadata(TypedDict, total=False):
    operation: Required[ImsTagOperation]
    key: Required[str]
    value: str


class ImsImagePatchData(TypedDict):
    """
    We only include the field that concerns us
    """
    metadata: ImsImagePatchMetadata


class ImsImageData(TypedDict, total=False):
    """
    We do not include all of the fields here, because we just
    use this for type hinting.
    """
    id: Required[str]
    name: Required[str]
    arch: ImsImageArch


class TagFailure(Exception):
    pass


class ImageNotFound(Exception):
    """
    Raised if querying IMS for an image and it is not found
    """
    def __init__(self, image_id: str) -> None:
        super().__init__(f"IMS image id '{image_id}' does not exist in IMS")


def get_image(image_id: str, session: Optional[RequestsSession]=None) -> ImsImageData:
    """
    Queries IMS to retrieve the specified image and return it.
    If the image does not exist, raise ImageNotFound.
    Other errors (like a failure to query IMS) will result in appropriate exceptions being raised.
    """
    if not session:
        session = requests_retry_session()
    url=f"{IMAGES_ENDPOINT}/{image_id}"
    LOGGER.debug("GET %s", url)
    try:
        response = session.get(url)
    except Exception as err:
        LOGGER.error("Exception during GET request to %s: %s", url, exc_type_msg(err))
        raise
    LOGGER.debug("Response status code=%d, reason=%s, body=%s", response.status_code,
                 response.reason, compact_response_text(response.text))
    try:
        response.raise_for_status()
    except HTTPError as err:
        msg = f"Failed asking IMS to get image {image_id}: {exc_type_msg(err)}"
        if response.status_code == 404:
            # If it's not found, we just log it as a warning, because we may be
            # okay with that -- that will be for the caller to decide
            LOGGER.warning(msg)
            raise ImageNotFound(image_id) from err
        LOGGER.error(msg)
        raise
    try:
        return response.json()
    except Exception as err:
        LOGGER.error("Failed decoding JSON response from getting IMS image %s: %s", image_id,
                     exc_type_msg(err))
        raise


def patch_image(image_id: str, data: ImsImagePatchData, session: Optional[RequestsSession]=None) -> None:
    if not data:
        LOGGER.warning("patch_image called without data; returning without action.")
        return
    if not session:
        session = requests_retry_session()
    url=f"{IMAGES_ENDPOINT}/{image_id}"
    LOGGER.debug("PATCH %s with body=%s", url, data)
    response = session.patch(url, json=data)
    LOGGER.debug("Response status code=%d, reason=%s, body=%s", response.status_code,
                 response.reason, compact_response_text(response.text))
    try:
        response.raise_for_status()
    except HTTPError as err:
        LOGGER.error("Failed asking IMS to patch image %s: %s", image_id, exc_type_msg(err))
        if response.status_code == 404:
            raise ImageNotFound(image_id) from err
        raise


def tag_image(image_id: str, operation: ImsTagOperation, key: str, value: Optional[str]=None,
              session: Optional[RequestsSession]=None) -> None:
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

    data = ImsImagePatchData(metadata=ImsImagePatchMetadata(operation=operation, key=key))
    if value is not None:
        data["metadata"]["value"] = value
    patch_image(image_id=image_id, data=data, session=session)


def get_ims_id_from_s3_url(s3_url: S3Url) -> Optional[str]:
    """
    If the s3_url matches the expected format of an IMS image path, then return the IMS image ID.
    Otherwise return None.
    """
    match = IMS_S3_KEY_RE_PROG.match(s3_url.key)
    if match is None:
        return None
    return match.group(1)


def get_arch_from_image_data(image_data: ImsImageData) -> ImsImageArch:
    """
    Returns the value of the 'arch' field in the image data
    If it is not present, logs a warning and returns the default value
    """
    try:
        arch = image_data['arch']
    except KeyError:
        LOGGER.warning("Defaulting to '%s' because 'arch' not set in IMS image data: %s",
                       DEFAULT_IMS_IMAGE_ARCH, image_data)
        return DEFAULT_IMS_IMAGE_ARCH
    except Exception as err:
        LOGGER.error("Unexpected error parsing IMS image data (%s): %s", exc_type_msg(err),
                     image_data)
        raise
    if arch:
        return arch
    LOGGER.warning("Defaulting to '%s' because 'arch' set to null value in IMS image data: %s",
                   DEFAULT_IMS_IMAGE_ARCH, image_data)
    return DEFAULT_IMS_IMAGE_ARCH
