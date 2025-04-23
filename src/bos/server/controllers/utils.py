#
# MIT License
#
# (C) Copyright 2019, 2021-2022, 2024-2025 Hewlett Packard Enterprise Development LP
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
import os
from urllib.parse import urlparse, urlunparse

import connexion
from connexion.lifecycle import ConnexionResponse
import flask

LOGGER = logging.getLogger(__name__)


class BadRequest(Exception):
    """
    Generic error to use for problems with API requests
    """


class ResourceNotFound(Exception):
    """
    A resource needed for an API request was not found.
    """

    RESOURCE_TYPE: str = "Resource"

    def __init__(self, resource_id: str):
        self._resource_id = resource_id
        super().__init__(f"{self.RESOURCE_TYPE} not found: {resource_id}")

    @property
    def resource_id(self) -> str:
        return self._resource_id


def url_for(endpoint: str, **values) -> str:
    """Calculate the URL for an endpoint

    This wraps flask.url_for. flask.url_for doesn't generate the path that we
    need when BOS is running on a path behind a proxy. For example, if the app
    is proxied on `/apis/bos` and the client made a request like
    `/apis/bos/v1`, flask.url_for('repositories') would return
    `/v1/repositories` which wouldn't be valid because it's missing the path
    prefix.

    This wrapper adds the "PROXY_PATH" environment variable value to the path
    in the returned url if the `X-Forwarded-For` header is present in the
    request.

    Also, it always sets _external=True.

    """
    LOGGER.debug('url_for(endpoint=%s)', endpoint)

    url = flask.url_for(endpoint, _external=True, **values)
    LOGGER.debug('url_for(url=%s)', url)

    proxy_path = os.environ.get('PROXY_PATH')
    if not proxy_path:
        # proxy_path isn't set so never change.
        return url

    if 'X-Forwarded-For' not in connexion.request.headers:
        # Request wasn't proxied so don't prefix proxy path.
        return url

    # Request was proxied, so update the path with the proxy path.
    _parts = urlparse(url)
    parts = (_parts.scheme, _parts.netloc,
             '/'.join([proxy_path.rstrip('/'),
                       _parts.path.lstrip('/')
                       ]), _parts.params, _parts.query, _parts.fragment)
    return urlunparse(parts)

    # TODO(CASMCMS-1869): there might be a better way to do this by overriding
    # url_adapter in the context or request, see
    # https://github.com/pallets/flask/blob/a74864ec229141784374f1998324d2cbac837295/flask/helpers.py#L302


def _400_bad_request(msg: str) -> ConnexionResponse:
    """
    ProblemBadRequest
    """
    return connexion.problem(
        status=400,
        title="Bad Request",
        detail=msg)

def _404_resource_not_found(resource_type: str, resource_id: str) -> ConnexionResponse:
    """
    ProblemResourceNotFound
    """
    return connexion.problem(
        status=404,
        title="The resource was not found",
        detail=f"{resource_type} '{resource_id}' does not exist")

def _404_tenanted_resource_not_found(resource_type: str, resource_id: str, tenant: str | None) -> ConnexionResponse:
    """
    ProblemResourceNotFound
    """
    if tenant:
        resource_type+=f" for tenant '{tenant}'"
    return _404_resource_not_found(resource_type, resource_id)
