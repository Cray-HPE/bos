#
# MIT License
#
# (C) Copyright 2021-2025 Hewlett Packard Enterprise Development LP
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
from typing import NoReturn

from bos.common.clients.endpoints import ApiResponseError, RequestData, RequestErrorHandler

from .base import BaseImsEndpoint
from .defs import IMS_TAG_OPERATIONS, LOGGER
from .exceptions import ImageNotFound, TagFailure


class ImsImageRequestErrorHandler(RequestErrorHandler):

    @classmethod
    def handle_api_response_error(cls, err: ApiResponseError,
                                  request_data: RequestData) -> NoReturn:
        if err.response_data.status_code == 404:
            # If it's not found, we just log it as a warning, because we may be
            # okay with that -- that will be for the caller to decide
            LOGGER.warning("%s %s: 404 response", request_data.method_name,
                           request_data.url)
            image_id = request_data.url.split('/')[-1]
            raise ImageNotFound(image_id) from err
        super().handle_api_response_error(err, request_data)


class ImagesEndpoint(BaseImsEndpoint):
    ENDPOINT = 'images'

    @property
    def error_handler(self) -> ImsImageRequestErrorHandler:
        return ImsImageRequestErrorHandler

    def get_image(self, image_id: str) -> dict:
        return self.get_item(image_id)

    def patch_image(self, image_id: str, data) -> None:
        self.update_item(image_id, data)

    def tag_image(self,
                  image_id: str,
                  operation: str,
                  key: str,
                  value: str | None = None) -> None:
        if operation not in IMS_TAG_OPERATIONS:
            msg = f"{operation} not valid. Expecting one of {IMS_TAG_OPERATIONS}"
            LOGGER.error(msg)
            raise TagFailure(msg)

        if not key:
            msg = f"key must exist: {key}"
            LOGGER.error(msg)
            raise TagFailure(msg)

        if value:
            LOGGER.debug("Patching image %s %sing key: %s value: %s", image_id,
                         operation, key, value)
        else:
            LOGGER.debug("Patching image %s %sing key: %s", image_id,
                         operation, key)

        data = {
            "metadata": {
                "operation": operation,
                "key": key,
                "value": value
            }
        }
        self.patch_image(image_id=image_id, data=data)
