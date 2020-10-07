# Copyright 2019, Cray Inc. All Rights Reserved.

import os
from urllib.parse import urlparse, urlunparse

import connexion
import flask

import logging
LOGGER = logging.getLogger('bos.utils')


def url_for(endpoint, **values):
    """Calculate the URL for an endpoint

    This wraps flask.url_for. flask.url_for doesn't generate the path that we
    need when PRS is running on a path behind a proxy. For example, if the app
    is proxied on `/apis/bos` and the client made a request like
    `/apis/bos/v1`, flask.url_for('repositories') would return
    `/v1/repositories` which wouldn't be valid because it's missing the path
    prefix.

    This wrapper adds the "PROXY_PATH" environment variable value to the path
    in the returned url if the `X-Forwarded-For` header is present in the
    request.

    Also, it always sets _external=True.

    """
    LOGGER.debug('url_for(endpoint=%s)' % endpoint)

    url = flask.url_for(endpoint, _external=True, **values)
    LOGGER.debug('url_for(url=%s)' % url)

    proxy_path = os.environ.get('PROXY_PATH')
    if not proxy_path:
        # proxy_path isn't set so never change.
        return url

    if 'X-Forwarded-For' not in connexion.request.headers:
        # Request wasn't proxied so don't prefix proxy path.
        return url

    # Request was proxied, so update the path with the proxy path.
    parts = urlparse(url)
    parts = (
        parts.scheme, parts.netloc,
        '/'.join([proxy_path.rstrip('/'), parts.path.lstrip('/')]),
        parts.params, parts.query, parts.fragment)
    return urlunparse(parts)

    # TODO(CASMCMS-1869): there might be a better way to do this by overriding
    # url_adapter in the context or request, see
    # https://github.com/pallets/flask/blob/a74864ec229141784374f1998324d2cbac837295/flask/helpers.py#L302
